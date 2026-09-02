import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

/// Raised for non-2xx responses; [message] is the server-provided text.
class ApiException implements Exception {
  ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

/// Same-origin JSON client for the WBLester WebApi (`/auth`, `/cpanel/jwt/*`).
///
/// Runs as JWT bearer requests with silent refresh-once on 401. Relative
/// leading-slash paths resolve against the serving origin, so the portal works
/// both at the dev root and under the `/admin` base href.
class ApiClient {
  ApiClient({http.Client? httpClient}) : _http = httpClient ?? http.Client();

  final http.Client _http;

  String? accessToken;
  String? refreshToken;

  /// Called after a successful refresh (token swap persisted by the holder).
  Future<void> Function()? onTokensChanged;

  /// Called when refresh fails and the session must be torn down.
  Future<void> Function()? onSessionExpired;

  Future<dynamic> get(String path) => request(path);

  Future<dynamic> post(String path, {Map<String, dynamic>? body}) =>
      request(path, method: 'POST', body: body);

  Future<dynamic> put(String path, {Map<String, dynamic>? body}) =>
      request(path, method: 'PUT', body: body);

  Future<dynamic> delete(String path) => request(path, method: 'DELETE');

  /// Upload a binary file as `file` in a multipart form to [path].
  Future<dynamic> upload(
    String path,
    String filename,
    List<int> bytes,
  ) async {
    final request = http.MultipartRequest('POST', Uri.parse(path));
    request.headers['Accept'] = 'application/json';
    if (accessToken != null) {
      request.headers['Authorization'] = 'Bearer $accessToken';
    }
    request.files.add(
      http.MultipartFile.fromBytes('file', bytes, filename: filename),
    );
    final streamed = await _http.send(request);
    final response = await http.Response.fromStream(streamed);
    return _decode(response, path);
  }

  Future<dynamic> request(
    String path, {
    String method = 'GET',
    Map<String, dynamic>? body,
  }) async {
    for (var attempt = 0; attempt < 2; attempt++) {
      final response = await _send(path, method: method, body: body);
      if (response.statusCode == 401 &&
          attempt == 0 &&
          refreshToken != null &&
          !_isAuthCall(path)) {
        final refreshed = await _tryRefresh();
        if (!refreshed) {
          await onSessionExpired?.call();
        }
        continue;
      }
      return _decode(response, path);
    }
    throw ApiException('Request failed', statusCode: 401);
  }

  Future<http.Response> _send(
    String path, {
    required String method,
    Map<String, dynamic>? body,
  }) async {
    final uri = Uri.parse(path);
    final headers = <String, String>{
      'Accept': 'application/json',
      if (accessToken != null) 'Authorization': 'Bearer $accessToken',
      if (body != null) 'Content-Type': 'application/json',
    };
    final encoded = body == null ? null : jsonEncode(body);
    switch (method) {
      case 'POST':
        return _http.post(uri, headers: headers, body: encoded);
      case 'PUT':
        return _http.put(uri, headers: headers, body: encoded);
      case 'DELETE':
        return _http.delete(uri, headers: headers);
      default:
        return _http.get(uri, headers: headers);
    }
  }

  bool _isAuthCall(String path) =>
      path == '/auth/login' ||
      path == '/auth/jwt_login' ||
      path == '/auth/refresh';

  Future<bool> _tryRefresh() async {
    if (refreshToken == null) return false;
    try {
      final response = await _http.post(
        Uri.parse('/auth/refresh'),
        headers: {
          'Accept': 'application/json',
          'Authorization': 'Bearer $refreshToken',
        },
      );
      if (response.statusCode != 200) return false;
      final data = _decode(response);
      if (data is! Map) return false;
      accessToken = data['access_token']?.toString();
      refreshToken = data['refresh_token']?.toString();
      await onTokensChanged?.call();
      return true;
    } on ApiException {
      return false;
    }
  }

  dynamic _decode(http.Response response, [String? path]) {
    final text = response.body;
    dynamic data;
    if (text.isNotEmpty) {
      try {
        data = jsonDecode(text);
      } on FormatException {
        data = null;
      }
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      var message = 'Request failed (${response.statusCode})';
      if (data is Map && data['message'] is String) {
        message = data['message'] as String;
      } else if (data is Map && data['error'] is String) {
        message = data['error'] as String;
      }
      if (path != null) _reportFailure(path, message);
      throw ApiException(message, statusCode: response.statusCode);
    }
    return data;
  }

  /// Fire-and-forget ingestion of failed API calls into the SIEM log stream
  /// so frontend errors are visible from the consolidated /logs view. Never
  /// recurses (log + auth endpoints are excluded).
  void _reportFailure(String path, String message) {
    final token = accessToken;
    if (token == null ||
        path.contains('/logs/') ||
        path.contains('/auth/')) {
      return;
    }
    unawaited(() async {
      try {
        await _http.post(
          Uri.parse('/cpanel/jwt/logs/frontend'),
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer $token',
          },
          body: jsonEncode({
            'level': 'ERROR',
            'page': path,
            'message': 'API: $message',
          }),
        );
      } catch (_) {
        // Reporting failures are deliberately silent.
      }
    }());
  }

  /// Fire-and-forget report of an uncaught Dart error (`FlutterError.onError`).
  void reportRuntimeError(String message) {
    final token = accessToken;
    if (token == null) return;
    unawaited(() async {
      try {
        await _http.post(
          Uri.parse('/cpanel/jwt/logs/frontend'),
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer $token',
          },
          body: jsonEncode({
            'level': 'ERROR',
            'page': 'app',
            'message': 'RUNTIME: ${message.substring(0, message.length > 900 ? 900 : message.length)}',
          }),
        );
      } catch (_) {
        // Reporting failures are deliberately silent.
      }
    }());
  }
}
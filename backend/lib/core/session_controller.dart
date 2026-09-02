import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api_client.dart';
import 'helpers.dart';

enum AuthStatus { unknown, unauthenticated, authenticated }

/// Holds auth state + the shared [ApiClient]; persists tokens client-side so a
/// refresh of the browser keeps the session alive until they expire.
class SessionController extends ChangeNotifier {
  SessionController({ApiClient? api}) : api = api ?? ApiClient() {
    this.api.onTokensChanged = () async {
      await _persistTokens();
      notifyListeners();
    };
    this.api.onSessionExpired = _expire;
  }

  final ApiClient api;

  AuthStatus status = AuthStatus.unknown;
  String username = '';
  int? userId;
  String? roleName;
  List<String> permissions = const [];
  bool mustChangePassword = false;

  bool get authenticated => status == AuthStatus.authenticated;

  bool get isSuperuser => roleName == 'superuser';

  bool can(String permission) => isSuperuser || permissions.contains(permission);

  static const _kAccess = 'wb_access';
  static const _kRefresh = 'wb_refresh';
  static const _kUsername = 'wb_username';
  static const _kRole = 'wb_role';
  static const _kPerms = 'wb_permissions';
  static const _kMustChange = 'wb_must_change';

  Future<void> restore() async {
    final prefs = await SharedPreferences.getInstance();
    final access = prefs.getString(_kAccess);
    final refresh = prefs.getString(_kRefresh);
    username = prefs.getString(_kUsername) ?? '';
    roleName = prefs.getString(_kRole);
    permissions = prefs.getStringList(_kPerms) ?? const [];
    mustChangePassword = prefs.getBool(_kMustChange) ?? false;

    api.accessToken = access;
    api.refreshToken = refresh;
    status = access == null ? AuthStatus.unauthenticated : AuthStatus.authenticated;
    notifyListeners();
  }

  /// Returns null on success or a user-facing error message.
  Future<String?> login(String user, String pass) async {
    try {
      final data = await api.post('/auth/login', body: {
        'username': user,
        'password': pass,
      });
      final map = data is Map ? data : <String, dynamic>{};
      api.accessToken = map['access_token']?.toString();
      api.refreshToken = map['refresh_token']?.toString();

      final userData = map['user'];
final userMap =
        userData is Map ? userData : const <String, dynamic>{};
      username = userMap['username']?.toString() ?? user;
      userId = asInt(userMap['user_id']);
      roleName = userMap['role_name']?.toString();
      mustChangePassword = userMap['must_change_password'] == true;
      final rawPerms = userMap['permissions'];
      if (rawPerms is List) {
        permissions = rawPerms.whereType<String>().toList();
      }

      await _persistTokens();
      await _persistUser();
      status = AuthStatus.authenticated;
      notifyListeners();
      return null;
    } on ApiException catch (error) {
      return error.message;
    }
  }

  Future<void> logout() async {
    api.accessToken = null;
    api.refreshToken = null;
    status = AuthStatus.unauthenticated;
    mustChangePassword = false;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kAccess);
    await prefs.remove(_kRefresh);
    await prefs.remove(_kUsername);
    await prefs.remove(_kRole);
    await prefs.remove(_kPerms);
    await prefs.remove(_kMustChange);
    notifyListeners();
  }

  /// Changes the current user's password. Clears [mustChangePassword] on
  /// success. Returns null on success or a user-facing error message.
  Future<String?> changePassword(String current, String next) async {
    final id = userId;
    if (id == null) return 'Session lost, please sign in again.';
    try {
      await api.put('/cpanel/jwt/users/$id/password', body: {
        'current_password': current,
        'new_password': next,
      });
      mustChangePassword = false;
      await _persistUser();
      notifyListeners();
      return null;
    } on ApiException catch (error) {
      return error.message;
    }
  }

  Future<void> _persistTokens() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kAccess, api.accessToken ?? '');
    await prefs.setString(_kRefresh, api.refreshToken ?? '');
  }

  Future<void> _persistUser() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kUsername, username);
    await prefs.setString(_kRole, roleName ?? '');
    await prefs.setStringList(_kPerms, permissions);
    await prefs.setBool(_kMustChange, mustChangePassword);
  }

  Future<void> _expire() async {
    api.accessToken = null;
    api.refreshToken = null;
    status = AuthStatus.unauthenticated;
    mustChangePassword = false;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kAccess);
    await prefs.remove(_kRefresh);
    await prefs.remove(_kMustChange);
    notifyListeners();
  }
}
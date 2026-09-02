import 'dart:convert';

import 'package:intl/intl.dart';

/// Numeric value that may arrive as int, num or a numeric string.
int? asInt(Object? value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  if (value == null) return null;
  return int.tryParse(value.toString());
}

String asStr(Object? value) => value?.toString() ?? '';

bool asBool(Object? value) => value == true;

DateTime? asDate(Object? value) {
  if (value is DateTime) return value;
  if (value == null) return null;
  return DateTime.tryParse(value.toString());
}

/// snake_case -> "Title Case".
String humanize(String key) => key
    .split('_')
    .where((part) => part.isNotEmpty)
    .map((part) => part[0].toUpperCase() + part.substring(1))
    .join(' ');

String fmtDate(DateTime? value) {
  if (value == null) return '—';
  return DateFormat('yyyy-MM-dd').format(value.toLocal());
}

String fmtDateTime(DateTime? value) {
  if (value == null) return '—';
  return DateFormat('yyyy-MM-dd HH:mm').format(value.toLocal());
}

String timeAgo(DateTime? value) {
  if (value == null) return '—';
  final diff = DateTime.now().difference(value.toLocal());
  if (diff.inSeconds < 45) return 'just now';
  if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
  if (diff.inHours < 24) return '${diff.inHours}h ago';
  if (diff.inDays < 30) return '${diff.inDays}d ago';
  return fmtDate(value);
}

Object? jsonDecodeSafe(String source) {
  final trimmed = source.trim();
  if (trimmed.isEmpty) return null;
  try {
    return jsonDecode(trimmed);
  } on FormatException {
    return null;
  }
}

String jsonPretty(Object? value) {
  if (value == null) return 'null';
  try {
    return const JsonEncoder.withIndent('  ').convert(value);
  } on JsonUnsupportedObjectError {
    return value.toString();
  }
}
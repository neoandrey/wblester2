import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'app.dart';
import 'core/session_controller.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  final session = SessionController();
  _hookErrorReporting(session);
  unawaited(session.restore());
  runApp(
    ChangeNotifierProvider.value(
      value: session,
      child: const WbLesterApp(),
    ),
  );
}

/// Surface uncaught Dart errors in the consolidated SIEM log view without
/// swallowing them from the console.
void _hookErrorReporting(SessionController session) {
  if (!kIsWeb) return;
  final previous = FlutterError.onError;
  FlutterError.onError = (details) {
    session.api.reportRuntimeError(details.exceptionAsString());
    previous?.call(details);
  };
}
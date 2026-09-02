import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:web/web.dart' as web;

import '../core/session_controller.dart';
import '../screens/login/forced_password_screen.dart';
import '../screens/login/login_screen.dart';
import '../screens/shell/admin_shell.dart';

/// Order defines sidebar layout + routing. Superuser-gated sections are also
/// enforced by the WebApi (403 for non-superusers).
const List<String> kSectionOrder = [
  'dashboard',
  'pages',
  'categories',
  'messages',
  'mail-templates',
  'settings',
  'users',
  'roles',
  'images',
  'files',
  'events',
  'jobs',
  'logs',
  'system',
  'audit',
];

const Set<String> kSuperuserOnly = {'events', 'jobs', 'logs', 'system'};

/// Path prefix the app is served under. Prefers the injected `<base href>`
/// (set by `--base-href /admin/`), falling back to `Uri.base.path` for a
/// plain `flutter run` at the dev root.
String appPrefix() {
  final base = web.document.querySelector('base')?.getAttribute('href');
  if (base != null && base.isNotEmpty) {
    var path = base.trim();
    while (path.length > 1 && path.endsWith('/')) {
      path = path.substring(0, path.length - 1);
    }
    return path == '/' ? '' : path;
  }
  var path = Uri.base.path;
  while (path.length > 1 && path.endsWith('/')) {
    path = path.substring(0, path.length - 1);
  }
  if (path == '/') return '';
  return path;
}

class AppRouter {
  AppRouter(this.session);

  final SessionController session;

  String get _prefix => appPrefix();

  String _root(String path) => '$_prefix$path';

  String? _goHome(BuildContext context, GoRouterState state) {
    if (!session.authenticated) return _root('/login');
    return session.mustChangePassword
        ? _root('/force-password')
        : _root('/app/dashboard');
  }

  String? _redirect(BuildContext context, GoRouterState state) {
    if (session.status == AuthStatus.unknown) return null;

    var path = state.uri.path;
    if (path == _prefix) path = '/';
    if (_prefix.isNotEmpty && path.startsWith('$_prefix/')) {
      path = path.substring(_prefix.length);
    }

    final authed = session.authenticated;
    final atLogin = path == '/login';
    if (!authed) return atLogin ? null : _root('/login');
    if (atLogin) {
      return _root(session.mustChangePassword
          ? '/force-password'
          : '/app/dashboard');
    }
    // Users waiting on a forced password change cannot enter the portal.
    if (path == '/force-password') {
      return session.mustChangePassword ? null : _root('/app/dashboard');
    }
    if (session.mustChangePassword) return _root('/force-password');
    if (path == '/' || path.isEmpty) return _root('/app/dashboard');

    final parts = path.split('/').where((part) => part.isNotEmpty).toList();
    if (parts.isEmpty || parts[0] != 'app') return _root('/app/dashboard');
    final section = parts.length > 1 ? parts[1] : 'dashboard';
    if (!kSectionOrder.contains(section)) return _root('/app/dashboard');
    if (kSuperuserOnly.contains(section) && !session.isSuperuser) {
      return _root('/app/dashboard');
    }
    return null;
  }

  GoRouter get router => GoRouter(
        initialLocation: _root('/login'),
        refreshListenable: session,
        redirect: _redirect,
        routes: [
          GoRoute(
            path: _prefix.isEmpty ? '/' : _prefix,
            redirect: _goHome,
          ),
          GoRoute(
            path: _root('/login'),
            builder: (context, state) => const LoginScreen(),
          ),
          GoRoute(
            path: _root('/force-password'),
            builder: (context, state) => const ForcedPasswordScreen(),
          ),
          GoRoute(
            path: _root('/app'),
            redirect: _goHome,
          ),
          GoRoute(
            path: _root('/app/:section'),
            builder: (context, state) => AdminShell(
              section: state.pathParameters['section'] ?? 'dashboard',
            ),
          ),
        ],
      );
}
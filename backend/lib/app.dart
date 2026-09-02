import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:provider/provider.dart';

import 'core/session_controller.dart';
import 'core/theme.dart';
import 'routing/app_router.dart';

class WbLesterApp extends StatelessWidget {
  const WbLesterApp({super.key});

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionController>();
    return MaterialApp.router(
      title: 'WBLester Admin',
      debugShowCheckedModeBanner: false,
      theme: buildAdminTheme(),
      routerConfig: AppRouter(session).router,
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: const [Locale('en')],
      builder: (context, child) {
        if (session.status == AuthStatus.unknown) {
          return const _SplashScreen();
        }
        return child!;
      },
    );
  }
}

class _SplashScreen extends StatelessWidget {
  const _SplashScreen();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      backgroundColor: kSidebar,
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            SvgPicture.asset(
              'assets/logo.svg',
              width: 76,
              height: 76,
              semanticsLabel: 'WBLester and O',
            ),
            const SizedBox(height: 24),
            Text(
              'WBLester & O.',
              style: theme.textTheme.headlineSmall
                  ?.copyWith(color: Colors.white, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 6),
            Text(
              'Content Management System',
              style: theme.textTheme.bodyMedium
                  ?.copyWith(color: const Color(0xFF9FB8AE)),
            ),
            const SizedBox(height: 32),
            const SizedBox(
              width: 24,
              height: 24,
              child: CircularProgressIndicator(
                color: kBrand,
                strokeWidth: 2.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
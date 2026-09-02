import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:provider/provider.dart';

import '../../core/session_controller.dart';
import '../../core/theme.dart';
import '../../core/ui.dart';

/// Blocking screen shown until a new user (or a user whose password an admin
/// reset) picks a fresh password. The router refuses access to any other
/// section while `mustChangePassword` is armed.
class ForcedPasswordScreen extends StatefulWidget {
  const ForcedPasswordScreen({super.key});

  @override
  State<ForcedPasswordScreen> createState() => _ForcedPasswordScreenState();
}

class _ForcedPasswordScreenState extends State<ForcedPasswordScreen> {
  final _current = TextEditingController();
  final _next = TextEditingController();
  final _confirm = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _current.dispose();
    _next.dispose();
    _confirm.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_current.text.isEmpty || _next.text.isEmpty || _confirm.text.isEmpty) {
      snack(context, 'All three fields are required.', error: true);
      return;
    }
    if (_next.text != _confirm.text) {
      snack(context, 'New password and confirmation do not match.',
          error: true);
      return;
    }
    if (_next.text.length < 6) {
      snack(context, 'New password must be at least 6 characters.',
          error: true);
      return;
    }
    if (_next.text == _current.text) {
      snack(context, 'New password must differ from the current one.',
          error: true);
      return;
    }
    setState(() => _busy = true);
    final session = context.read<SessionController>();
    final error = await session
        .changePassword(_current.text, _next.text);
    if (!mounted) return;
    setState(() => _busy = false);
    if (error != null) {
      snack(context, error, error: true);
      return;
    }
    snack(context, 'Password updated. Welcome!');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kSidebar,
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 430),
            child: Material(
              color: Colors.white,
              elevation: 8,
              borderRadius: BorderRadius.circular(16),
              child: Padding(
                padding: const EdgeInsets.fromLTRB(28, 28, 28, 20),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      children: [
                        SvgPicture.asset(
                          'assets/logo.svg',
                          width: 44,
                          height: 44,
                          semanticsLabel: 'WBLester and O',
                        ),
                        const SizedBox(width: 14),
                        const Expanded(
                          child: Text(
                            'Set a new password',
                            style: TextStyle(
                              fontSize: 19,
                              fontWeight: FontWeight.w800,
                              color: Color(0xFF17242B),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Your account was created by an administrator or an '
                      'admin reset your password. Choose a new one before '
                      'you continue into the portal.',
                      style: TextStyle(color: Color(0xFF607A82), height: 1.4),
                    ),
                    const SizedBox(height: 18),
                    KTextField(
                      label: 'Current password',
                      controller: _current,
                      password: true,
                    ),
                    const SizedBox(height: 12),
                    KTextField(
                      label: 'New password',
                      controller: _next,
                      password: true,
                    ),
                    const SizedBox(height: 12),
                    KTextField(
                      label: 'Confirm new password',
                      controller: _confirm,
                      password: true,
                    ),
                    const SizedBox(height: 20),
                    FilledButton.icon(
                      onPressed: _busy ? null : _submit,
                      icon: _busy
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child:
                                  CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.lock_reset, size: 18),
                      label: Text(_busy ? 'Updating…' : 'Update password'),
                    ),
                    TextButton(
                      onPressed: _busy
                          ? null
                          : () => context
                              .read<SessionController>()
                              .logout(),
                      child: const Text('Sign out instead'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
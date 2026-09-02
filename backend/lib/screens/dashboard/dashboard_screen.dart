import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/helpers.dart';
import '../../core/session_controller.dart';
import '../../core/ui.dart';
import '../../routing/app_router.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardModel {
  const _DashboardModel({
    required this.webapi,
    required this.backend,
    required this.frontend,
    required this.storageBytes,
  });

  final Map<String, dynamic> webapi;
  final Map<String, dynamic> backend;
  final Map<String, dynamic> frontend;
  final int storageBytes;
}

class _DashboardScreenState extends State<DashboardScreen> {
  late Future<_DashboardModel> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_DashboardModel> _load() async {
    final api = context.read<SessionController>().api;
    final data = await api.get('/cpanel/jwt/stats') as Map;
    final webapi = (data['webapi'] as Map?)?.cast<String, dynamic>() ?? {};
    final backend = (data['backend'] as Map?)?.cast<String, dynamic>() ?? {};
    final frontend = (data['frontend'] as Map?)?.cast<String, dynamic>() ?? {};
    return _DashboardModel(
      webapi: webapi,
      backend: backend,
      frontend: frontend,
      storageBytes: asInt(frontend['storage_bytes']) ?? 0,
    );
  }

  void _reload() => setState(() => _future = _load());

  int _n(Map<String, dynamic> map, String key) => asInt(map[key]) ?? 0;

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionController>();
    return FutureBuilder<_DashboardModel>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const LoadingPane();
        }
        if (snapshot.hasError) {
          return ErrorPane(
            message: snapshot.error.toString(),
            onRetry: _reload,
          );
        }
        final model = snapshot.data!;
        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'Welcome back, ${session.username}',
              style: const TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  color: Color(0xFF17242B)),
            ),
            const SizedBox(height: 4),
            Text(
              session.isSuperuser
                  ? 'You are signed in with superuser access.'
                  : 'Role: ${session.roleName ?? 'user'} · '
                      '${session.permissions.length} permission(s).',
              style: const TextStyle(color: Color(0xFF607A82)),
            ),
            const SizedBox(height: 20),
            _cardGrid([
              StatCard(
                icon: Icons.description_outlined,
                label: 'Pages',
                value: '${_n(model.backend, 'pages')}',
                accent: const Color(0xFF1976D2),
                onTap: () => context.go('${appPrefix()}/app/pages'),
              ),
              StatCard(
                icon: Icons.category_outlined,
                label: 'Categories',
                value: '${_n(model.backend, 'categories')}',
                accent: const Color(0xFF8E6E2E),
                onTap: () => context.go('${appPrefix()}/app/categories'),
              ),
              StatCard(
                icon: Icons.mail_outlined,
                label: 'New messages',
                value: '${_n(model.backend, 'messages_new')}',
                accent: const Color(0xFFC62828),
                onTap: () => context.go('${appPrefix()}/app/messages'),
              ),
              StatCard(
                icon: Icons.group_outlined,
                label: 'Users',
                value: '${_n(model.webapi, 'users')}',
                accent: const Color(0xFF7B1FA2),
                onTap: () => context.go('${appPrefix()}/app/users'),
              ),
            ]),
            const SizedBox(height: 26),
            Text(
              'Platform',
              style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF17242B)),
            ),
            const SizedBox(height: 12),
            _cardGrid([
              StatCard(
                icon: Icons.photo_library_outlined,
                label: 'Images',
                value: '${_n(model.frontend, 'images')}',
                accent: const Color(0xFF00838F),
                onTap: () => context.go('${appPrefix()}/app/images'),
              ),
              StatCard(
                icon: Icons.folder_outlined,
                label: 'Documents',
                value: '${_n(model.frontend, 'files')}',
                accent: const Color(0xFF5D4037),
                onTap: () => context.go('${appPrefix()}/app/files'),
              ),
              StatCard(
                icon: Icons.storage_outlined,
                label: 'Media storage',
                value: _humanBytes(model.storageBytes),
                accent: const Color(0xFF37474F),
              ),
              StatCard(
                icon: Icons.person_pin_circle_outlined,
                label: 'Active users',
                value: '${_n(model.webapi, 'active_users')}',
                accent: const Color(0xFF00695C),
              ),
              StatCard(
                icon: Icons.fact_check_outlined,
                label: 'Jobs running',
                value: '${_n(model.backend, 'jobs_running')}',
                accent: const Color(0xFFE65100),
                onTap: () => context.go('${appPrefix()}/app/jobs'),
              ),
              StatCard(
                icon: Icons.receipt_long_outlined,
                label: 'Audit entries',
                value: '${_n(model.webapi, 'audit_trail')}',
                accent: const Color(0xFF3E2723),
                onTap: () => context.go('${appPrefix()}/app/audit'),
              ),
              if (session.isSuperuser) ...[
                StatCard(
                  icon: Icons.manage_search_outlined,
                  label: 'Frontend errors',
                  value: '${_n(model.frontend, 'frontend_errors')}',
                  accent: const Color(0xFFC62828),
                  onTap: () => context.go('${appPrefix()}/app/logs'),
                ),
                StatCard(
                  icon: Icons.password_outlined,
                  label: 'Must change password',
                  value: '${_n(model.webapi, 'must_change_password')}',
                  accent: const Color(0xFFB26A00),
                  onTap: () => context.go('${appPrefix()}/app/users'),
                ),
              ],
            ]),
            const SizedBox(height: 12),
          ],
        );
      },
    );
  }

  Widget _cardGrid(List<StatCard> cards) {
    return GridView(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
        maxCrossAxisExtent: 300,
        mainAxisSpacing: 14,
        crossAxisSpacing: 14,
        childAspectRatio: 3.15,
      ),
      children: cards,
    );
  }
}

String _humanBytes(int bytes) {
  if (bytes < 1024) return '$bytes B';
  if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
  if (bytes < 1024 * 1024 * 1024) {
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }
  return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB';
}
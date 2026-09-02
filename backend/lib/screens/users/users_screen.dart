import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/helpers.dart';
import '../../core/session_controller.dart';
import '../../core/status.dart';
import '../../core/ui.dart';

class UsersScreen extends StatefulWidget {
  const UsersScreen({super.key});

  @override
  State<UsersScreen> createState() => _UsersScreenState();
}

class _UsersModel {
  const _UsersModel({required this.users, required this.roles});

  final List<Map<String, dynamic>> users;
  final Map<int, String> roles;
}

class _UsersScreenState extends State<UsersScreen> {
  late Future<_UsersModel> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_UsersModel> _load() async {
    final api = context.read<SessionController>().api;
    final usersData = await api.get('/cpanel/jwt/data/Users') as Map;
    final rolesData = await api.get('/cpanel/jwt/data/Roles') as Map;
    final users = (usersData['Users'] as List).cast<Map<String, dynamic>>();
    final roles = <int, String>{
      for (final role in (rolesData['Roles'] as List).cast<Map<String, dynamic>>())
        asInt(role['role_id']) ?? 0: asStr(role['role_name']),
    };
    users.sort((a, b) =>
        (asInt(a['user_id']) ?? 0).compareTo(asInt(b['user_id']) ?? 0));
    return _UsersModel(users: users, roles: roles);
  }

  void _reload() => setState(() => _future = _load());

  String _roleName(_UsersModel model, Map<String, dynamic> user) {
    final roleId = asInt(user['role_id']);
    return roleId == null ? '—' : (model.roles[roleId] ?? 'role #$roleId');
  }

  Future<void> _create() async {
    final model = await _future;
    if (!mounted) return;
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => _UserDialog(roles: model.roles),
    );
    if (result == null || !mounted) return;
    final api = context.read<SessionController>().api;
    try {
      await api.post('/cpanel/jwt/users', body: result);
      if (!mounted) return;
      snack(context, 'User created.');
      _reload();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    }
  }

  Future<void> _edit(_UsersModel model, Map<String, dynamic> user) async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => _UserDialog(
        existing: user,
        roles: model.roles,
        roleHint: _roleName(model, user),
      ),
    );
    if (result == null || !mounted) return;
    final api = context.read<SessionController>().api;
    final id = asInt(user['user_id']);
    try {
      if (result.containsKey('action_password')) {
        await api.put(
          '/cpanel/jwt/users/$id/password',
          body: {
            'new_password': result['action_password'] as String,
          },
        );
      }
      await api.put('/cpanel/jwt/users/$id', body: {
        'roleId': result['roleId'],
        'active': result['active'],
      });
      if (result['unlock'] == true) {
        await api.post('/cpanel/jwt/users/$id/unlock');
      }
      if (!mounted) return;
      snack(context, 'User updated.');
      _reload();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    }
  }

  Future<void> _delete(Map<String, dynamic> user) async {
    final ok = await confirmAction(
      context,
      title: 'Delete user',
      message: 'Delete user "${user['username']}"?',
    );
    if (!ok || !mounted) return;
    final api = context.read<SessionController>().api;
    try {
      await api.delete('/cpanel/jwt/data/Users/${asInt(user['user_id'])}');
      if (!mounted) return;
      snack(context, 'User deleted.');
      _reload();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<_UsersModel>(
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
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 12),
              child: ToolbarRow(
                children: [
                  Text(
                    '${model.users.length} user(s)',
                    style: const TextStyle(color: Color(0xFF607A82)),
                  ),
                  const Spacer(),
                  FilledButton.icon(
                    onPressed: _create,
                    icon: const Icon(Icons.add, size: 18),
                    label: const Text('New user'),
                  ),
                ],
              ),
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                child: Card(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: DataTable(
                      headingRowHeight: 42,
                      columns: const [
                        DataColumn(label: Text('ID')),
                        DataColumn(label: Text('Username')),
                        DataColumn(label: Text('Email')),
                        DataColumn(label: Text('Role')),
                        DataColumn(label: Text('State')),
                        DataColumn(label: Text('Logins')),
                        DataColumn(label: Text('')),
                      ],
                      rows: [
                        for (final user in model.users)
                          DataRow(cells: [
                            tableCell(asInt(user['user_id']), strong: true),
                            tableCell(user['username'], strong: true),
                            tableCell(user['email']),
                            tableCell(_roleName(model, user)),
                            tableCellWidget(_StateChip(user: user)),
                            tableCell(asInt(user['login_count']) ?? 0),
                            tableCellWidget(Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                smallIcon(Icons.edit_outlined, 'Edit',
                                    () => _edit(model, user)),
                                smallIcon(
                                    Icons.delete_outline,
                                    'Delete',
                                    () => _delete(user),
                                    danger: true),
                              ],
                            )),
                          ]),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}

class _StateChip extends StatelessWidget {
  const _StateChip({required this.user});

  final Map<String, dynamic> user;

  @override
  Widget build(BuildContext context) {
    if (user['locked'] == true) {
      return const ChipStatus(
          spec: StatusSpec('LOCKED', Color(0xFFC62828)));
    }
    if (user['active'] == true) {
      return const ChipStatus(
          spec: StatusSpec('ACTIVE', Color(0xFF2E7D32)));
    }
    return const ChipStatus(
        spec: StatusSpec('INACTIVE', Color(0xFF607D8B)));
  }
}

class _UserDialog extends StatefulWidget {
  const _UserDialog({
    this.existing,
    required this.roles,
    this.roleHint,
  });

  final Map<String, dynamic>? existing;
  final Map<int, String> roles;
  final String? roleHint;

  @override
  State<_UserDialog> createState() => _UserDialogState();
}

class _UserDialogState extends State<_UserDialog> {
  late final _username =
      TextEditingController(text: asStr(widget.existing?['username']));
  late final _email =
      TextEditingController(text: asStr(widget.existing?['email']));
  late final _password = TextEditingController();
  late final _confirm = TextEditingController();
  late int? _roleId = asInt(widget.existing?['role_id']);
  late bool _active = widget.existing?['active'] == true;
  bool _unlock = false;

  @override
  void dispose() {
    _username.dispose();
    _email.dispose();
    _password.dispose();
    _confirm.dispose();
    super.dispose();
  }

  void _save() {
    final isNew = widget.existing == null;
    if (_username.text.trim().isEmpty || _email.text.trim().isEmpty) {
      snack(context, 'Username and email are required.', error: true);
      return;
    }
    if (isNew) {
      if (_password.text.isEmpty) {
        snack(context, 'A password is required for new users.', error: true);
        return;
      }
      if (_password.text != _confirm.text) {
        snack(context, 'Password and confirmation do not match.', error: true);
        return;
      }
      Navigator.of(context).pop(<String, dynamic>{
        'username': _username.text.trim(),
        'email': _email.text.trim(),
        'password': _password.text,
        'roleId': _roleId ?? 0,
        'active': _active,
      });
      return;
    }
    Navigator.of(context).pop(<String, dynamic>{
      'roleId': _roleId ?? 0,
      'active': _active,
      'unlock': _unlock,
      if (_password.text.trim().isNotEmpty)
        'action_password': _password.text.trim(),
    });
  }

  @override
  Widget build(BuildContext context) {
    final isNew = widget.existing == null;
    final roleItems = <int, String>{
      for (final entry in widget.roles.entries) entry.key: entry.value,
    };
    return AlertDialog(
      title: Text(isNew ? 'New user' : 'Edit user'),
      content: SizedBox(
        width: 440,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              KTextField(label: 'Username', controller: _username),
              const SizedBox(height: 12),
              KTextField(label: 'Email', controller: _email),
              const SizedBox(height: 12),
              KDropdown<int?>(
                label: 'Role',
                value: _roleId,
                items: roleItems,
                onChanged: (value) => setState(() => _roleId = value),
              ),
              const SizedBox(height: 12),
              KTextField(
                label: isNew ? 'Password' : 'New password (optional)',
                controller: _password,
                password: true,
              ),
              if (isNew) ...[
                const SizedBox(height: 12),
                KTextField(
                  label: 'Confirm password',
                  controller: _confirm,
                  password: true,
                ),
                const SizedBox(height: 8),
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    'The user will be asked to change this password on '
                    'their first login.',
                    style: const TextStyle(
                        fontSize: 12, color: Color(0xFF607A82)),
                  ),
                ),
              ],
              if (!isNew) ...[
                const SizedBox(height: 12),
                CheckboxListTile(
                  value: _active,
                  onChanged: (value) => setState(() => _active = value ?? true),
                  title: const Text('Active'),
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                ),
                if (widget.existing?['locked'] == true)
                  CheckboxListTile(
                    value: _unlock,
                    onChanged: (value) => setState(() => _unlock = value ?? false),
                    title: const Text('Unlock this account'),
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                  ),
                if (_password.text.trim().isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Align(
                      alignment: Alignment.centerLeft,
                      child: Text(
                        'Password will be changed.',
                        style: TextStyle(
                            fontSize: 12,
                            color: Theme.of(context).colorScheme.primary),
                      ),
                    ),
                  ),
              ],
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(onPressed: _save, child: const Text('Save user')),
      ],
    );
  }
}
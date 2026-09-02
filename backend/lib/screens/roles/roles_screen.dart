import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/helpers.dart';
import '../../core/session_controller.dart';
import '../../core/status.dart';
import '../../core/ui.dart';

class RolesScreen extends StatefulWidget {
  const RolesScreen({super.key});

  @override
  State<RolesScreen> createState() => _RolesScreenState();
}

class _Matrix {
  const _Matrix({
    required this.roles,
    required this.permissions,
    required this.cells,
  });

  final List<Map<String, dynamic>> roles;
  final List<Map<String, dynamic>> permissions;

  /// role_id -> permission_id -> access level (-1..2).
  final Map<int, Map<int, int>> cells;
}

class _RolesScreenState extends State<RolesScreen> {
  late Future<_Matrix> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_Matrix> _load() async {
    final api = context.read<SessionController>().api;
    final data = await api.get('/cpanel/jwt/roles/matrix') as Map;
    final roles = (data['roles'] as List).cast<Map<String, dynamic>>();
    final permissions =
        (data['permissions'] as List).cast<Map<String, dynamic>>();
    final cells = <int, Map<int, int>>{};
    for (final row in (data['matrix'] as List).cast<Map<String, dynamic>>()) {
      cells[asInt(row['role_id']) ?? 0] = {
        for (final cell in (row['cells'] as List)
            .cast<Map<String, dynamic>>())
          asInt(cell['permission_id']) ?? 0:
              asInt(cell['access_level']) ?? -1,
      };
    }
    return _Matrix(roles: roles, permissions: permissions, cells: cells);
  }

  void _reload() => setState(() => _future = _load());

  Future<void> _createRole() async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => _RoleDialog(),
    );
    if (result == null || !mounted) return;
    final api = context.read<SessionController>().api;
    try {
      await api.post('/cpanel/jwt/roles', body: result);
      if (!mounted) return;
      snack(context, 'Role created.');
      _reload();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    }
  }

  Future<void> _deleteRole(Map<String, dynamic> role) async {
    final ok = await confirmAction(
      context,
      title: 'Delete role',
      message: 'Delete role "${role['role_name']}"? Users keep their records.',
    );
    if (!ok || !mounted) return;
    final api = context.read<SessionController>().api;
    try {
      await api
          .delete('/cpanel/jwt/data/Roles/${asInt(role['role_id'])}');
      if (!mounted) return;
      snack(context, 'Role deleted.');
      _reload();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    }
  }

  Future<void> _saveMatrix(_Matrix matrix, int roleId,
      Map<int, int> levels) async {
    final api = context.read<SessionController>().api;
    try {
      await api.put('/cpanel/jwt/roles/matrix/$roleId', body: {
        'cells': [
          for (final permission in matrix.permissions)
            {
              'permission_id': asInt(permission['permission_id']) ?? 0,
              'access_level': levels[asInt(permission['permission_id']) ?? 0],
            },
        ],
      });
      if (!mounted) return;
      snack(context, 'Matrix saved.');
      setState(() {
        matrix.cells[roleId] = levels;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<_Matrix>(
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
        final matrix = snapshot.data!;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 12),
              child: ToolbarRow(
                children: [
                  const Text(
                    'Access is per role × permission: deny / read / modify / full.',
                    style: TextStyle(color: Color(0xFF607A82)),
                  ),
                  const Spacer(),
                  FilledButton.icon(
                    onPressed: _createRole,
                    icon: const Icon(Icons.add, size: 18),
                    label: const Text('New role'),
                  ),
                ],
              ),
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Roles & permissions matrix',
                            style: TextStyle(
                                fontSize: 16, fontWeight: FontWeight.w700)),
                        const SizedBox(height: 8),
                        const Text(
                          'Read = view, Modify = edit, Full = create & delete. Levels are indexed '
                          'by the CMS permission model.',
                          style: TextStyle(color: Color(0xFF607A82), fontSize: 12.5),
                        ),
                        const SizedBox(height: 12),
                        for (final role in matrix.roles)
                          _RoleMatrixCard(
                            role: role,
                            matrix: matrix,
                            onSave: (levels) => _saveMatrix(
                                matrix,
                                asInt(role['role_id']) ?? 0,
                                levels),
                            onDelete: () => _deleteRole(role),
                          ),
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

class _RoleMatrixCard extends StatefulWidget {
  const _RoleMatrixCard({
    required this.role,
    required this.matrix,
    required this.onSave,
    required this.onDelete,
  });

  final Map<String, dynamic> role;
  final _Matrix matrix;
  final ValueChanged<Map<int, int>> onSave;
  final VoidCallback onDelete;

  @override
  State<_RoleMatrixCard> createState() => _RoleMatrixCardState();
}

class _RoleMatrixCardState extends State<_RoleMatrixCard> {
late final Map<int, int> _levels = Map.of(
    widget.matrix.cells[asInt(widget.role['role_id']) ?? 0] ?? const {});
  bool _dirty = false;

  void _setLevel(int permissionId, int? level) {
    if (level == null) return;
    setState(() {
      _levels[permissionId] = level;
      _dirty = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    final roleId = asInt(widget.role['role_id']) ?? 0;
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 10, 14, 14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(asStr(widget.role['role_name']),
                    style: const TextStyle(
                        fontWeight: FontWeight.w700, fontSize: 15)),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    asStr(widget.role['description']),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: Color(0xFF607A82), fontSize: 12.5),
                  ),
                ),
                if (roleId != 1)
                  smallIcon(Icons.delete_outline, 'Delete role', widget.onDelete,
                      danger: true),
                FilledButton(
                  onPressed:
                      _dirty ? () => widget.onSave(_levels) : null,
                  child: const Text('Save'),
                ),
              ],
            ),
            const SizedBox(height: 8),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  for (final permission in widget.matrix.permissions)
                    Padding(
                      padding: const EdgeInsets.only(right: 10),
                      child: _LevelCell(
                        permissionId: asInt(permission['permission_id']) ?? 0,
                        label: asStr(permission['permission_name']),
                        level: _levels[asInt(permission['permission_id']) ?? 0] ??
                            -1,
                        onChanged: (value) => _setLevel(
                            asInt(permission['permission_id']) ?? 0, value),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _LevelCell extends StatelessWidget {
  const _LevelCell({
    required this.permissionId,
    required this.label,
    required this.level,
    required this.onChanged,
  });

  final int permissionId;
  final String label;
  final int level;
  final ValueChanged<int?> onChanged;

  @override
  Widget build(BuildContext context) {
    final spec = specFor(level);
    return SizedBox(
      width: 150,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF31404A)),
              maxLines: 2,
              overflow: TextOverflow.ellipsis),
          const SizedBox(height: 4),
          Container(
            decoration: BoxDecoration(
              color: spec.color.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: spec.color.withValues(alpha: 0.35)),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 8),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<int>(
                value: level,
                isExpanded: true,
                isDense: true,
                items: [
                  for (final entry in kAccessLevel.entries)
                    DropdownMenuItem(
                      value: entry.key,
                      child: Text(
                        entry.value.label,
                        style: TextStyle(
                            color: entry.value.color,
                            fontWeight: FontWeight.w600),
                      ),
                    ),
                ],
                onChanged: onChanged,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _RoleDialog extends StatefulWidget {
  const _RoleDialog();

  @override
  State<_RoleDialog> createState() => _RoleDialogState();
}

class _RoleDialogState extends State<_RoleDialog> {
  final _name = TextEditingController();
  final _description = TextEditingController();

  @override
  void dispose() {
    _name.dispose();
    _description.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('New role'),
      content: SizedBox(
        width: 420,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            KTextField(label: 'Role name', controller: _name),
            const SizedBox(height: 12),
            KTextField(
                label: 'Description', controller: _description, lines: 2),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () {
            if (_name.text.trim().isEmpty) {
              snack(context, 'Role name is required.', error: true);
              return;
            }
            Navigator.of(context).pop(<String, dynamic>{
              'roleName': _name.text.trim(),
              'description': _description.text.trim(),
            });
          },
          child: const Text('Create'),
        ),
      ],
    );
  }
}
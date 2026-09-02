import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/helpers.dart';
import '../../core/session_controller.dart';
import '../../core/ui.dart';

class CategoriesScreen extends StatefulWidget {
  const CategoriesScreen({super.key});

  @override
  State<CategoriesScreen> createState() => _CategoriesScreenState();
}

class _CategoriesScreenState extends State<CategoriesScreen> {
  late Future<List<Map<String, dynamic>>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<Map<String, dynamic>>> _load() async {
    final api = context.read<SessionController>().api;
    final data = await api.get('/cpanel/jwt/data/Categories') as Map;
    final list = (data['Categories'] as List).cast<Map<String, dynamic>>();
    list.sort((a, b) => (asInt(a['sort_order']) ?? 0)
        .compareTo(asInt(b['sort_order']) ?? 0));
    return list;
  }

  void _reload() => setState(() => _future = _load());

  Future<void> _edit([Map<String, dynamic>? existing]) async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => _CategoryDialog(existing: existing),
    );
    if (result == null || !mounted) return;
    final api = context.read<SessionController>().api;
    try {
      if (existing == null) {
        await api.post('/cpanel/jwt/data/Categories', body: result);
      } else {
        await api.put(
          '/cpanel/jwt/data/Categories/${asInt(existing['category_id'])}',
          body: result,
        );
      }
      if (!mounted) return;
      snack(context, existing == null ? 'Category created.' : 'Category updated.');
      _reload();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    }
  }

  Future<void> _delete(Map<String, dynamic> category) async {
    final ok = await confirmAction(
      context,
      title: 'Delete category',
      message:
          'Delete "${category['category_name']}"? Pages in it are not removed.',
    );
    if (!ok || !mounted) return;
    final api = context.read<SessionController>().api;
    try {
      await api.delete(
          '/cpanel/jwt/data/Categories/${asInt(category['category_id'])}');
      if (!mounted) return;
      snack(context, 'Category deleted.');
      _reload();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Map<String, dynamic>>>(
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
        final categories = snapshot.data!;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 12),
              child: ToolbarRow(
                children: [
                  const Text(
                    'Category navigator',
                    style: TextStyle(color: Color(0xFF607A82)),
                  ),
                  const Spacer(),
                  FilledButton.icon(
                    onPressed: () => _edit(),
                    icon: const Icon(Icons.add, size: 18),
                    label: const Text('New category'),
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
                        DataColumn(label: Text('Name')),
                        DataColumn(label: Text('Slug')),
                        DataColumn(label: Text('Parent')),
                        DataColumn(label: Text('Order')),
                        DataColumn(label: Text('Visible')),
                        DataColumn(label: Text('')),
                      ],
                      rows: [
                        if (categories.isEmpty)
                          const DataRow(cells: [
                            DataCell(Text('')),
                            DataCell(Text('No categories yet.')),
                            DataCell(Text('')),
                            DataCell(Text('')),
                            DataCell(Text('')),
                            DataCell(Text('')),
                            DataCell(Text('')),
                          ])
                        else
                          for (final category in categories)
                            DataRow(cells: [
                              tableCell(asInt(category['category_id']),
                                  strong: true),
                              tableCell(category['category_name'],
                                  strong: true),
                              tableCell(category['slug']),
                              tableCell(_parentName(categories, category)),
                              tableCell(asInt(category['sort_order']) ?? 0),
                              tableCellWidget(Switch(
                                value: category['visible'] != false,
                                onChanged: (_) => _edit(category),
                                materialTapTargetSize:
                                    MaterialTapTargetSize.shrinkWrap,
                              )),
                              tableCellWidget(Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  smallIcon(Icons.edit_outlined, 'Edit',
                                      () => _edit(category)),
                                  smallIcon(
                                      Icons.delete_outline,
                                      'Delete',
                                      () => _delete(category),
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

  String _parentName(List<Map<String, dynamic>> categories,
      Map<String, dynamic> category) {
    final parentId = asInt(category['parent_id']);
    if (parentId == null) return '—';
    for (final other in categories) {
      if (asInt(other['category_id']) == parentId) {
        return asStr(other['category_name']);
      }
    }
    return '—';
  }
}

class _CategoryDialog extends StatefulWidget {
  const _CategoryDialog({this.existing});

  final Map<String, dynamic>? existing;

  @override
  State<_CategoryDialog> createState() => _CategoryDialogState();
}

class _CategoryDialogState extends State<_CategoryDialog> {
  late final _name =
      TextEditingController(text: asStr(widget.existing?['category_name']));
  late final _slug = TextEditingController(text: asStr(widget.existing?['slug']));
  late final _sortOrder = TextEditingController(
      text: (asInt(widget.existing?['sort_order']) ?? 0).toString());
  late bool _visible = widget.existing?['visible'] != false;

  @override
  void dispose() {
    _name.dispose();
    _slug.dispose();
    _sortOrder.dispose();
    super.dispose();
  }

  void _save() {
    if (_name.text.trim().isEmpty || _slug.text.trim().isEmpty) {
      snack(context, 'Name and slug are required.', error: true);
      return;
    }
    final existingId = asInt(widget.existing?['category_id']);
    Navigator.of(context).pop({
      'categoryId': ?existingId,
      'categoryName': _name.text.trim(),
      'slug': _slug.text.trim(),
      'sortOrder': int.tryParse(_sortOrder.text.trim()) ?? 0,
      'visible': _visible,
    });
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.existing == null ? 'New category' : 'Edit category'),
      content: SizedBox(
        width: 420,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            KTextField(label: 'Name', controller: _name),
            const SizedBox(height: 12),
            KTextField(label: 'Slug', controller: _slug, hint: 'services'),
            const SizedBox(height: 12),
            KTextField(
              label: 'Sort order',
              controller: _sortOrder,
              number: true,
            ),
            const SizedBox(height: 12),
            CheckboxListTile(
              value: _visible,
              onChanged: (value) => setState(() => _visible = value ?? true),
              title: const Text('Visible on the website'),
              dense: true,
              contentPadding: EdgeInsets.zero,
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(onPressed: _save, child: const Text('Save category')),
      ],
    );
  }
}
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/browser.dart';
import '../../core/helpers.dart';
import '../../core/session_controller.dart';
import '../../core/status.dart';
import '../../core/ui.dart';
import 'block_editor.dart';

class PagesScreen extends StatefulWidget {
  const PagesScreen({super.key});

  @override
  State<PagesScreen> createState() => _PagesScreenState();
}

class _PagesModel {
  const _PagesModel({required this.pages, required this.categories});

  final List<Map<String, dynamic>> pages;
  final List<Map<String, dynamic>> categories;
}

class _PagesScreenState extends State<PagesScreen> {
  late Future<_PagesModel> _future;
  String _filter = '';

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_PagesModel> _load() async {
    final api = context.read<SessionController>().api;
    final tree = await api.get('/cpanel/jwt/pages/tree') as Map;
    final pages = (tree['pages'] as List).cast<Map<String, dynamic>>();
    final categories =
        (tree['categories'] as List).cast<Map<String, dynamic>>();
    pages.sort((a, b) {
      final na = asInt(a['sort_order']) ?? 0;
      final nb = asInt(b['sort_order']) ?? 0;
      if (na != nb) return na.compareTo(nb);
      return (asInt(a['page_id']) ?? 0).compareTo(asInt(b['page_id']) ?? 0);
    });
    return _PagesModel(pages: pages, categories: categories);
  }

  void _reload() => setState(() => _future = _load());

  Map<String, dynamic>? _byId(List<Map<String, dynamic>> items, String key, int? id) {
    if (id == null) return null;
    for (final item in items) {
      if (asInt(item[key]) == id) return item;
    }
    return null;
  }

  Future<void> _savePage({Map<String, dynamic>? existing}) async {
    final categories =
        await context.read<SessionController>().api.get('/cpanel/jwt/data/Categories');
    if (!mounted) return;
    final catList = ((categories as Map)['Categories'] as List)
        .cast<Map<String, dynamic>>();
    final edited = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => PageDialog(
        existing: existing,
        categories: catList,
      ),
    );
    if (edited == null || !mounted) return;

    final api = context.read<SessionController>().api;
    try {
      if (existing == null) {
        await api.post('/cpanel/jwt/data/Pages', body: edited);
      } else {
        await api.put(
            '/cpanel/jwt/data/Pages/${asInt(existing['page_id'])}',
            body: edited);
      }
      if (!mounted) return;
      snack(context, existing == null ? 'Page created.' : 'Page updated.');
      _reload();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    }
  }

  Future<void> _toggleVisible(Map<String, dynamic> page) async {
    final api = context.read<SessionController>().api;
    try {
      await api.put(
        '/cpanel/jwt/pages/${asInt(page['page_id'])}/visibility',
        body: {'visible': page['visible'] != true},
      );
      _reload();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    }
  }

  Future<void> _setHome(Map<String, dynamic> page) async {
    final api = context.read<SessionController>().api;
    try {
      await api.post('/cpanel/jwt/pages/set_home_page/${asInt(page['page_id'])}');
      if (!mounted) return;
      snack(context, 'Home page set to "${page['title']}".');
      _reload();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    }
  }

  Future<void> _delete(Map<String, dynamic> page) async {
    final ok = await confirmAction(
      context,
      title: 'Delete page',
      message: 'Delete "${page['title']}"? This cannot be undone.',
    );
    if (!ok || !mounted) return;
    final api = context.read<SessionController>().api;
    try {
      await api.delete('/cpanel/jwt/data/Pages/${asInt(page['page_id'])}');
      if (!mounted) return;
      snack(context, 'Page deleted.');
      _reload();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<_PagesModel>(
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
        final haystack = _filter.trim().toLowerCase();
        final visible = model.pages.where((page) {
          if (haystack.isEmpty) return true;
          final title = asStr(page['title']).toLowerCase();
          final slug = asStr(page['slug']).toLowerCase();
          return title.contains(haystack) || slug.contains(haystack);
        }).toList();

        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 12),
              child: ToolbarRow(
                children: [
                  SizedBox(
                    width: 280,
                    child: TextField(
                      decoration: const InputDecoration(
                        hintText: 'Filter by title or slug…',
                        prefixIcon: Icon(Icons.search),
                      ),
                      onChanged: (value) => setState(() => _filter = value),
                    ),
                  ),
                  const Spacer(),
                  FilledButton.icon(
                    onPressed: () => _savePage(),
                    icon: const Icon(Icons.add, size: 18),
                    label: const Text('New page'),
                  ),
                ],
              ),
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: DataTable(
                        headingRowHeight: 42,
                        columns: const [
                          DataColumn(label: Text('ID')),
                          DataColumn(label: Text('Title')),
                          DataColumn(label: Text('Slug')),
                          DataColumn(label: Text('Category')),
                          DataColumn(label: Text('Order')),
                          DataColumn(label: Text('Home')),
                          DataColumn(label: Text('Visible')),
                          DataColumn(label: Text('')),
                        ],
                        rows: [
                          if (visible.isEmpty)
                            const DataRow(cells: [
                              DataCell(Text('')),
                              DataCell(Text('No pages yet.')),
                              DataCell(Text('')),
                              DataCell(Text('')),
                              DataCell(Text('')),
                              DataCell(Text('')),
                              DataCell(Text('')),
                              DataCell(Text('')),
                            ])
                          else
                            for (final page in visible)
                              DataRow(
                                cells: [
                                  tableCell(asInt(page['page_id']), strong: true),
                                  tableCell(page['title'], strong: true),
                                  DataCell(Text(
                                    asStr(page['slug']),
                                    style: const TextStyle(
                                      fontFamily: 'monospace',
                                      fontSize: 12.5,
                                    ),
                                  )),
                                  tableCell(_categoryName(model, page)),
                                  tableCell(asInt(page['sort_order']) ?? 0),
                                  tableCellWidget(ChipStatus(
                                    spec: page['is_home'] == true
                                        ? const StatusSpec('HOME',
                                            Color(0xFF8E6E2E))
                                        : const StatusSpec('—',
                                            Color(0xFFB0BEC5)),
                                  )),
                                  tableCellWidget(_SmallSwitch(
                                    value: page['visible'] == true,
                                    onChanged: () => _toggleVisible(page),
                                  )),
                                  tableCellWidget(_RowActions(
                                    page: page,
                                    onEdit: () => _savePage(existing: page),
                                    onSetHome: () => _setHome(page),
                                    onDelete: () => _delete(page),
                                  )),
                                ],
                              ),
                        ],
                      ),
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

  String _categoryName(_PagesModel model, Map<String, dynamic> page) {
    final category = _byId(model.categories, 'category_id',
        asInt(page['category_id']));
    return category == null ? '—' : asStr(category['category_name']);
  }
}

class _SmallSwitch extends StatelessWidget {
  const _SmallSwitch({required this.value, required this.onChanged});

  final bool value;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) {
    return Switch(
      value: value,
      onChanged: (_) => onChanged(),
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
    );
  }
}

class _RowActions extends StatelessWidget {
  const _RowActions({
    required this.page,
    required this.onEdit,
    required this.onSetHome,
    required this.onDelete,
  });

  final Map<String, dynamic> page;
  final VoidCallback onEdit;
  final VoidCallback onSetHome;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        smallIcon(Icons.edit_outlined, 'Edit', onEdit),
        smallIcon(Icons.home_outlined, 'Set as home page', onSetHome),
        smallIcon(Icons.open_in_new, 'View', () {
          openUrl('/page/${asStr(page['slug'])}');
        }),
        smallIcon(Icons.delete_outline, 'Delete', onDelete, danger: true),
      ],
    );
  }
}

class PageDialog extends StatefulWidget {
  const PageDialog({super.key, required this.existing, required this.categories});

  final Map<String, dynamic>? existing;
  final List<Map<String, dynamic>> categories;

  @override
  State<PageDialog> createState() => _PageDialogState();
}

class _PageDialogState extends State<PageDialog> {
  late final _title = TextEditingController(text: asStr(widget.existing?['title']));
  late final _slug = TextEditingController(text: asStr(widget.existing?['slug']));
  late final _seoTitle =
      TextEditingController(text: asStr(widget.existing?['seo_title']));
  late final _seoDescription =
      TextEditingController(text: asStr(widget.existing?['seo_description']));
  late final _sortOrder = TextEditingController(
      text: (asInt(widget.existing?['sort_order']) ?? 10).toString());
  late int? _categoryId = asInt(widget.existing?['category_id']);
  late bool _visible = widget.existing?['visible'] != false;
  late List<Map<String, dynamic>> _blocks = _parseBlocks(
      widget.existing?['content_json']);

  static List<Map<String, dynamic>> _parseBlocks(Object? raw) {
    if (raw is Map && raw['blocks'] is List) {
      return (raw['blocks'] as List)
          .whereType<Map<String, dynamic>>()
          .toList();
    }
    return const [];
  }

  @override
  void dispose() {
    _title.dispose();
    _slug.dispose();
    _seoTitle.dispose();
    _seoDescription.dispose();
    _sortOrder.dispose();
    super.dispose();
  }

  Future<void> _editBlocks() async {
    final result = await showDialog<List<Map<String, dynamic>>>(
      context: context,
      builder: (context) => BlocksDialog(blocks: _blocks),
    );
    if (result != null) setState(() => _blocks = result);
  }

  void _save() {
    if (_title.text.trim().isEmpty) {
      snack(context, 'Title is required.', error: true);
      return;
    }
    final slug = _slug.text.trim();
    if (slug.isEmpty) {
      snack(context, 'Slug is required.', error: true);
      return;
    }
    final pageId = asInt(widget.existing?['page_id']);
    Navigator.of(context).pop({
      'pageId': ?pageId,
      'title': _title.text.trim(),
      'slug': slug,
      'categoryId': ?_categoryId,
      'sortOrder': int.tryParse(_sortOrder.text.trim()) ?? 0,
      'visible': _visible,
      'seoTitle': _seoTitle.text.trim(),
      'seoDescription': _seoDescription.text.trim(),
      'contentJson': {'blocks': _blocks},
    });
  }

  @override
  Widget build(BuildContext context) {
    final categoryItems = <int?, String>{
      for (final category in widget.categories)
        asInt(category['category_id']): asStr(category['category_name']),
    };
    return AlertDialog(
      title: Text(widget.existing == null ? 'New page' : 'Edit page'),
      content: SizedBox(
        width: 560,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              KTextField(label: 'Title', controller: _title),
              const SizedBox(height: 12),
              KTextField(label: 'Slug', controller: _slug, hint: 'about-us'),
              const SizedBox(height: 12),
              KDropdown<int?>(
                label: 'Category',
                value: _categoryId,
                allowNull: true,
                items: categoryItems,
                onChanged: (value) => setState(() => _categoryId = value),
              ),
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
              const SizedBox(height: 12),
              KTextField(
                label: 'SEO title',
                controller: _seoTitle,
              ),
              const SizedBox(height: 12),
              KTextField(
                label: 'SEO description',
                controller: _seoDescription,
                lines: 2,
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  const Expanded(
                    child: Text(
                      'Content blocks',
                      style: TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ),
                  TextButton.icon(
                    onPressed: _editBlocks,
                    icon: const Icon(Icons.view_agenda_outlined, size: 18),
                    label: Text('${_blocks.length} block(s)…'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(onPressed: _save, child: const Text('Save page')),
      ],
    );
  }
}
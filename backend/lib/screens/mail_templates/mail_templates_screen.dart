import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/helpers.dart';
import '../../core/session_controller.dart';
import '../../core/ui.dart';

class MailTemplatesScreen extends StatefulWidget {
  const MailTemplatesScreen({super.key});

  @override
  State<MailTemplatesScreen> createState() => _MailTemplatesScreenState();
}

class _MailTemplatesScreenState extends State<MailTemplatesScreen> {
  late Future<List<Map<String, dynamic>>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<Map<String, dynamic>>> _load() async {
    final api = context.read<SessionController>().api;
    final data = await api.get('/cpanel/jwt/data/MailTemplates') as Map;
    final templates =
        ((data['MailTemplates'] as List?) ?? const [])
            .cast<Map<String, dynamic>>();
    templates.sort((a, b) => asStr(a['template_name'])
        .compareTo(asStr(b['template_name'])));
    return templates;
  }

  void _reload() => setState(() => _future = _load());

  Future<void> _edit([Map<String, dynamic>? existing]) async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => _TemplateDialog(existing: existing),
    );
    if (result == null || !mounted) return;
    final api = context.read<SessionController>().api;
    try {
      if (existing == null) {
        await api.post('/cpanel/jwt/data/MailTemplates', body: result);
        if (!mounted) return;
        snack(context, 'Template created.');
      } else {
        final id = asInt(existing['template_id']);
        await api.put('/cpanel/jwt/data/MailTemplates/$id', body: result);
        if (!mounted) return;
        snack(context, 'Template updated.');
      }
      _reload();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    }
  }

  Future<void> _delete(Map<String, dynamic> template) async {
    final ok = await confirmAction(
      context,
      title: 'Delete template',
      message:
          'Delete template "${asStr(template['template_name'])}" permanently?',
    );
    if (!ok || !mounted) return;
    final api = context.read<SessionController>().api;
    try {
      await api.delete(
          '/cpanel/jwt/data/MailTemplates/${asInt(template['template_id'])}');
      if (!mounted) return;
      snack(context, 'Template deleted.');
      _reload();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final canWrite = context.read<SessionController>().can('messages');
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
        final templates = snapshot.data!;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 4),
              child: ToolbarRow(
                children: [
                  Text('${templates.length} template(s)',
                      style: const TextStyle(color: Color(0xFF607A82))),
                  const Spacer(),
                  if (canWrite)
                    FilledButton.icon(
                      onPressed: () => _edit(),
                      icon: const Icon(Icons.add, size: 18),
                      label: const Text('New template'),
                    ),
                  const SizedBox(width: 6),
                  IconButton(
                    tooltip: 'Refresh',
                    icon: const Icon(Icons.refresh),
                    onPressed: _reload,
                  ),
                ],
              ),
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
                child: Card(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: templates.isEmpty
                        ? const Padding(
                            padding: EdgeInsets.all(24),
                            child: Text('No mail templates yet.'),
                          )
                        : DataTable(
                            headingRowHeight: 42,
                            columns: const [
                              DataColumn(label: Text('Template')),
                              DataColumn(label: Text('Description')),
                              DataColumn(label: Text('')),
                            ],
                            rows: [
                              for (final template in templates)
                                DataRow(cells: [
                                  DataCell(Text(
                                    asStr(template['template_name']),
                                    style: const TextStyle(
                                        fontWeight: FontWeight.w600),
                                  )),
                                  DataCell(Text(
                                    asStr(template['description']),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  )),
                                  DataCell(Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      IconButton(
                                        tooltip: 'Preview',
                                        iconSize: 18,
                                        icon: const Icon(Icons.visibility_outlined),
                                        onPressed: () => _preview(template),
                                      ),
                                      if (canWrite) ...[
                                        IconButton(
                                          tooltip: 'Edit',
                                          iconSize: 18,
                                          icon: const Icon(Icons.edit_outlined),
                                          onPressed: () => _edit(template),
                                        ),
                                        IconButton(
                                          tooltip: 'Delete',
                                          iconSize: 18,
                                          icon: const Icon(
                                              Icons.delete_outline),
                                          onPressed: () => _delete(template),
                                        ),
                                      ],
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

  Future<void> _preview(Map<String, dynamic> template) async {
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(asStr(template['template_name'])),
        content: SizedBox(
          width: 640,
          child: SelectableText(
            asStr(template['contents']),
            style: const TextStyle(fontFamily: 'monospace', fontSize: 12.5),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }
}

class _TemplateDialog extends StatefulWidget {
  const _TemplateDialog({this.existing});

  final Map<String, dynamic>? existing;

  @override
  State<_TemplateDialog> createState() => _TemplateDialogState();
}

class _TemplateDialogState extends State<_TemplateDialog> {
  late final _name = TextEditingController(
      text: asStr(widget.existing?['template_name']));
  late final _description = TextEditingController(
      text: asStr(widget.existing?['description']));
  late final _contents = TextEditingController(
      text: asStr(widget.existing?['contents']));

  @override
  void dispose() {
    _name.dispose();
    _description.dispose();
    _contents.dispose();
    super.dispose();
  }

  void _save() {
    final name = _name.text.trim();
    if (name.isEmpty) {
      snack(context, 'A template name is required.', error: true);
      return;
    }
    Navigator.of(context).pop({
      'template_name': name,
      if (_description.text.trim().isNotEmpty)
        'description': _description.text.trim(),
      'contents': _contents.text.trim(),
    });
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.existing == null ? 'New mail template' : 'Edit template'),
      content: SizedBox(
        width: 620,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              KTextField(
                label: 'Template name',
                controller: _name,
                hint: 'welcome, new_message, …',
              ),
              const SizedBox(height: 12),
              KTextField(
                label: 'Description',
                controller: _description,
              ),
              const SizedBox(height: 12),
              KTextField(
                label: 'Contents ({{placeholders}} in double braces)',
                controller: _contents,
                lines: 10,
              ),
              const SizedBox(height: 8),
              const Text(
                'Placeholders are filled from the message context, e.g. '
                '{{name}}, {{body}}, {{message}}.',
                style: TextStyle(fontSize: 11.5, color: Color(0xFF607A82)),
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
        FilledButton(onPressed: _save, child: const Text('Save template')),
      ],
    );
  }
}
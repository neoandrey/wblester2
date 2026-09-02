import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/helpers.dart';
import '../../core/session_controller.dart';
import '../../core/ui.dart';

class ComposeDialog extends StatefulWidget {
  const ComposeDialog({super.key});

  @override
  State<ComposeDialog> createState() => _ComposeDialogState();
}

class _ComposeDialogState extends State<ComposeDialog> {
  final _to = TextEditingController();
  final _subject = TextEditingController();
  final _name = TextEditingController();
  final _body = TextEditingController();
  List<String> _addressList = const [];
  List<Map<String, dynamic>> _templates = const [];
  Map<String, dynamic>? _template;
  bool _mailingListTo = false;
  bool _loading = true;
  bool _sending = false;
  String? _error;
  final List<Map<String, dynamic>> _attachments = [];

  @override
  void initState() {
    super.initState();
    _loadOptions();
  }

  @override
  void dispose() {
    _to.dispose();
    _subject.dispose();
    _name.dispose();
    _body.dispose();
    super.dispose();
  }

  Future<void> _loadOptions() async {
    final api = context.read<SessionController>().api;
    try {
      final settings = await api.get('/cpanel/jwt/data/SiteSettings') as Map;
      final list = (settings['SiteSettings'] as List?) ?? const [];
      final first = list.isEmpty ? null : list.first as Map;
      _addressList = (first?['mailing_list'] as List? ?? const [])
          .whereType<String>()
          .where((email) => email.trim().isNotEmpty)
          .toList();
      final templates =
          await api.get('/cpanel/jwt/data/MailTemplates') as Map;
      _templates = ((templates['MailTemplates'] as List?) ?? const [])
          .cast<Map<String, dynamic>>();
      _templates.sort((a, b) =>
          asStr(a['template_name']).compareTo(asStr(b['template_name'])));
    } on ApiException catch (error) {
      _error = error.message;
    }
    if (mounted) setState(() => _loading = false);
  }

  List<String> get _recipients {
    final parts = _to.text.replaceAll(';', ',').split(',');
    final manual = [
      for (final part in parts)
        if (part.trim().isNotEmpty) part.trim(),
    ];
    return _mailingListTo ? [..._addressList, ...manual] : manual;
  }

  String get _placeholderHint {
    final contents = asStr(_template?['contents']);
    final matches = RegExp(r'\{\{\s*([a-zA-Z0-9_]+)\s*\}\}')
        .allMatches(contents)
        .map((m) => m.group(1)!)
        .toSet();
    return matches.isEmpty
        ? 'Template has no placeholders.'
        : 'Placeholders: ${matches.map((m) => '{{$m}}').join('  ')}';
  }

  Future<void> _send() async {
    final recipients = _recipients;
    final subject = _subject.text.trim();
    final body = _body.text.trim();
    if (recipients.isEmpty) {
      snack(context, 'Add at least one recipient.', error: true);
      return;
    }
    if (subject.isEmpty) {
      snack(context, 'Add a subject.', error: true);
      return;
    }
    if (body.isEmpty && _template == null) {
      snack(context, 'Write a message or choose a template.', error: true);
      return;
    }
    setState(() {
      _sending = true;
      _error = null;
    });
    final api = context.read<SessionController>().api;
    try {
      await api.post('/cpanel/jwt/messages/compose', body: {
        'to': recipients,
        'subject': subject,
        'body': body,
        if (_template != null)
          'template_name': asStr(_template!['template_name']),
        'context': {'name': _name.text.trim()},
        'attachments': [
          for (final a in _attachments) {'type': a['type'], 'id': a['id']},
        ],
        'reply_to_id': null,
      });
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _sending = false;
        _error = error.message;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Compose mail'),
      content: SizedBox(
        width: 620,
        child: _loading
            ? const SizedBox(
                height: 120,
                child: Center(child: CircularProgressIndicator()),
              )
            : SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (_error != null)
                      Container(
                        margin: const EdgeInsets.only(bottom: 12),
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color:
                              const Color(0xFFC62828).withValues(alpha: 0.08),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(_error!,
                            style: const TextStyle(
                                color: Color(0xFFC62828), fontSize: 13)),
                      ),
                    if (_addressList.isNotEmpty)
                      CheckboxListTile(
                        contentPadding: EdgeInsets.zero,
                        controlAffinity: ListTileControlAffinity.leading,
                        dense: true,
                        value: _mailingListTo,
                        title: Text(
                          'Mailing list (${_addressList.length})',
                          style: const TextStyle(fontSize: 14),
                        ),
                        onChanged: (v) => setState(() => _mailingListTo = v ?? false),
                      ),
                    TextField(
                      controller: _to,
                      maxLines: 2,
                      decoration: const InputDecoration(
                        labelText: 'To (comma / newline separated)',
                        hintText: 'client@example.com',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _subject,
                      decoration: const InputDecoration(
                        labelText: 'Subject',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<Map<String, dynamic>>(
                      initialValue: _template,
                      isExpanded: true,
                      decoration: const InputDecoration(
                        labelText: 'Template (optional)',
                        border: OutlineInputBorder(),
                      ),
                      hint: const Text('No template'),
                      items: [
                        for (final template in _templates)
                          DropdownMenuItem(
                            value: template,
                            child: Text(
                              asStr(template['template_name']),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                      ],
                      onChanged: (value) => setState(() => _template = value),
                    ),
                    if (_template != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 6),
                        child: Text(
                          _placeholderHint,
                          style: const TextStyle(
                              fontSize: 11.5, color: Color(0xFF607A82)),
                        ),
                      ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _name,
                      decoration: const InputDecoration(
                        labelText: 'Name placeholder',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _body,
                      maxLines: 6,
                      decoration: const InputDecoration(
                        labelText: 'Message',
                        hintText: 'Your message…',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        OutlinedButton.icon(
                          onPressed: _attach,
                          icon: const Icon(Icons.attach_file, size: 18),
                          label: const Text('Attach media'),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Wrap(
                            spacing: 6,
                            runSpacing: 4,
                            children: [
                              for (final a in _attachments)
                                InputChip(
                                  avatar: Icon(
                                    a['type'] == 'image'
                                        ? Icons.image_outlined
                                        : Icons.insert_drive_file_outlined,
                                    size: 16,
                                  ),
                                  label:
                                      Text(asStr(a['label']), style: const TextStyle(fontSize: 12)),
                                  onDeleted: () => setState(() =>
                                      _attachments.remove(a)),
                                  deleteIconColor:
                                      Theme.of(context).colorScheme.error,
                                ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
      ),
      actions: [
        TextButton(
          onPressed: _sending ? null : () => Navigator.of(context).pop(false),
          child: const Text('Cancel'),
        ),
        FilledButton.icon(
          onPressed: _sending ? null : _send,
          icon: _sending
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.send, size: 18),
          label: const Text('Send'),
        ),
      ],
    );
  }

Future<void> _attach() async {
    final api = context.read<SessionController>().api;
    List<Map<String, dynamic>> images;
    List<Map<String, dynamic>> files;
    try {
      final data = await api.get('/cpanel/jwt/uploads') as Map;
      images = ((data['Images'] as List?) ?? const [])
          .cast<Map<String, dynamic>>();
      files = ((data['Files'] as List?) ?? const []).cast<Map<String, dynamic>>();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
      return;
    }
    if (!mounted) return;
    final picked = await showDialog<List<Map<String, dynamic>>>(
      context: context,
      builder: (context) => _AttachmentPickerDialog(images: images, files: files),
    );
    if (picked == null || !mounted) return;
    final already = _attachments
        .map((a) => '${a['type']}${a['id']}')
        .toSet();
    setState(() {
      for (final item in picked) {
        if (already.add('${item['type']}${item['id']}')) {
          _attachments.add({
            'type': item['type'],
            'id': item['id'],
            'label': item['label'],
          });
        }
      }
    });
  }
}

class _AttachmentPickerDialog extends StatefulWidget {
  const _AttachmentPickerDialog({required this.images, required this.files});

  final List<Map<String, dynamic>> images;
  final List<Map<String, dynamic>> files;

  @override
  State<_AttachmentPickerDialog> createState() => _AttachmentPickerDialogState();
}

class _AttachmentPickerDialogState extends State<_AttachmentPickerDialog> {
  final Set<String> _selected = {};

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Attach media'),
      content: SizedBox(
        width: 560,
        height: 420,
        child: ListView(
          children: [
            const Padding(
              padding: EdgeInsets.only(bottom: 4),
              child: Text('Images',
                  style: TextStyle(fontWeight: FontWeight.w600)),
            ),
            if (widget.images.isEmpty)
              const Padding(
                padding: EdgeInsets.only(bottom: 12),
                child: Text('No images yet.',
                    style: TextStyle(color: Color(0xFF607A82))),
              )
            else
              for (final image in widget.images)
                CheckboxListTile(
                  contentPadding: EdgeInsets.zero,
                  dense: true,
                  value: _selected.contains('image${asInt(image['image_id'])}'),
                  title: Text(asStr(image['image_name']),
                      maxLines: 1, overflow: TextOverflow.ellipsis),
                  subtitle: const Text('Inserted inline in the email body'),
                  onChanged: (v) => setState(() {
                    final key = 'image${asInt(image['image_id'])}';
                    if (v == true) {
                      _selected.add(key);
                    } else {
                      _selected.remove(key);
                    }
                  }),
                ),
            const Divider(height: 24),
            const Padding(
              padding: EdgeInsets.only(bottom: 4),
              child: Text('Files / documents',
                  style: TextStyle(fontWeight: FontWeight.w600)),
            ),
            if (widget.files.isEmpty)
              const Padding(
                padding: EdgeInsets.only(bottom: 12),
                child: Text('No documents yet.',
                    style: TextStyle(color: Color(0xFF607A82))),
              )
            else
              for (final file in widget.files)
                CheckboxListTile(
                  contentPadding: EdgeInsets.zero,
                  dense: true,
                  value: _selected.contains('file${asInt(file['file_id'])}'),
                  title: Text(asStr(file['file_name']),
                      maxLines: 1, overflow: TextOverflow.ellipsis),
                  subtitle: Text(
                      '${asStr(file['file_format']).toUpperCase()} attachment',
                      style: const TextStyle(fontSize: 11)),
                  onChanged: (v) => setState(() {
                    final key = 'file${asInt(file['file_id'])}';
                    if (v == true) {
                      _selected.add(key);
                    } else {
                      _selected.remove(key);
                    }
                  }),
                ),
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
            final result = <Map<String, dynamic>>[];
            for (final key in _selected) {
              if (key.startsWith('image')) {
                for (final image in widget.images) {
                  if (asInt(image['image_id']) == int.tryParse(key.substring(5))) {
                    result.add({
                      'type': 'image',
                      'id': image['image_id'],
                      'label': asStr(image['image_name']),
                    });
                  }
                }
              } else {
                for (final file in widget.files) {
                  if (asInt(file['file_id']) == int.tryParse(key.substring(4))) {
                    result.add({
                      'type': 'file',
                      'id': file['file_id'],
                      'label': asStr(file['file_name']),
                    });
                  }
                }
              }
            }
            Navigator.of(context).pop(result);
          },
          child: Text('Attach (${_selected.length})'),
        ),
      ],
    );
  }
}


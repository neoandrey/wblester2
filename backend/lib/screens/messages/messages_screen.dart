import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/helpers.dart';
import '../../core/session_controller.dart';
import '../../core/status.dart';
import '../../core/ui.dart';
import 'messages_compose.dart';

class MessagesScreen extends StatefulWidget {
  const MessagesScreen({super.key});

  @override
  State<MessagesScreen> createState() => _MessagesScreenState();
}

class _MessagesScreenState extends State<MessagesScreen> {
  late Future<List<Map<String, dynamic>>> _future;
  int? _statusFilter;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<Map<String, dynamic>>> _load() async {
    final api = context.read<SessionController>().api;
    final data = await api.get('/cpanel/jwt/data/Messages') as Map;
    final list = (data['Messages'] as List).cast<Map<String, dynamic>>();
    list.sort((a, b) =>
        (asInt(b['message_id']) ?? 0).compareTo(asInt(a['message_id']) ?? 0));
    return list;
  }

  void _reload() => setState(() => _future = _load());

  Future<void> _compose() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => const ComposeDialog(),
    );
    if (ok != true || !mounted) return;
    snack(context, 'Mail sent.');
    _reload();
  }

  Future<void> _setStatus(
      Map<String, dynamic> message, int status, String label) async {
    final api = context.read<SessionController>().api;
    try {
      await api.put(
        '/cpanel/jwt/messages/${asInt(message['message_id'])}/status',
        body: {'status': status},
      );
      if (!mounted) return;
      snack(context, 'Message $label.');
      _reload();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    }
  }

  Future<void> _reply(Map<String, dynamic> message) async {
    final result = await showDialog<String>(
      context: context,
      builder: (context) => _ReplyDialog(message: message),
    );
    if (result == null || !mounted) return;
    final api = context.read<SessionController>().api;
    try {
      await api.post(
        '/cpanel/jwt/messages/${asInt(message['message_id'])}/reply',
        body: {'body': result},
      );
      if (!mounted) return;
      snack(context, 'Reply sent.');
      _reload();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    }
  }

  Future<void> _delete(Map<String, dynamic> message) async {
    final ok = await confirmAction(
      context,
      title: 'Delete message',
      message: 'Delete this message permanently?',
    );
    if (!ok || !mounted) return;
    final api = context.read<SessionController>().api;
    try {
      await api.delete(
          '/cpanel/jwt/data/Messages/${asInt(message['message_id'])}');
      if (!mounted) return;
      snack(context, 'Message deleted.');
      _reload();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    }
  }

  Future<void> _open(Map<String, dynamic> message) async {
    if (asInt(message['status']) == 0) {
      await _setStatus(message, 1, 'marked read');
    }
    if (!mounted) return;
    await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => _MessageDialog(
        message: message,
        onReply: () async {
          Navigator.of(context).pop();
          await _reply(message);
        },
        onStatus: (status) async {
          Navigator.of(context).pop();
          await _setStatus(message, status, kMessageStatus[status]!.label);
        },
      ),
    );
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
        final all = snapshot.data!;
        final filtered = _statusFilter == null
            ? all
            : all
                .where((m) => asInt(m['status']) == _statusFilter)
                .toList();
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 4),
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    _FilterChip(
                      label: 'All',
                      selected: _statusFilter == null,
                      onTap: () => setState(() => _statusFilter = null),
                    ),
                    for (final entry in kMessageStatus.entries)
                      _FilterChip(
                        label: entry.value.label,
                        selected: _statusFilter == entry.key,
                        onTap: () =>
                            setState(() => _statusFilter = entry.key),
                      ),
                    const Spacer(),
                    FilledButton.icon(
                      onPressed: _compose,
                      icon: const Icon(Icons.edit_outlined, size: 18),
                      label: const Text('Compose'),
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
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
                child: Card(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: DataTable(
                      headingRowHeight: 42,
                      columns: const [
                        DataColumn(label: Text('Status')),
                        DataColumn(label: Text('From')),
                        DataColumn(label: Text('Subject')),
                        DataColumn(label: Text('Date')),
                        DataColumn(label: Text('')),
                      ],
                      rows: [
                        if (filtered.isEmpty)
                          const DataRow(cells: [
                            DataCell(Text('')),
                            DataCell(Text('No messages.')),
                            DataCell(Text('')),
                            DataCell(Text('')),
                            DataCell(Text('')),
                          ])
                        else
                          for (final message in filtered)
                            DataRow(
                              onSelectChanged: (_) => _open(message),
                              cells: [
                                tableCellWidget(ChipStatus(
                                  spec: kMessageStatus[
                                          asInt(message['status']) ?? 0] ??
                                      const StatusSpec('?', Color(0xFFB0BEC5)),
                                )),
                                DataCell(Column(
                                  crossAxisAlignment:
                                      CrossAxisAlignment.start,
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Text(asStr(message['from_name']),
                                        style: const TextStyle(
                                            fontWeight: FontWeight.w600)),
                                    Text(
                                      asStr(message['from_email']),
                                      style: const TextStyle(
                                          fontSize: 11.5,
                                          color: Color(0xFF607A82)),
                                    ),
                                  ],
                                )),
                                tableCell(message['subject'], strong: true),
                                tableCell(fmtDateTime(
                                    asDate(message['sent_at']))),
                                tableCellWidget(Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    smallIcon(Icons.reply, 'Reply',
                                        () => _reply(message)),
                                    smallIcon(
                                        Icons.delete_outline,
                                        'Delete',
                                        () => _delete(message),
                                        danger: true),
                                  ],
                                )),
                              ],
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

class _FilterChip extends StatelessWidget {
  const _FilterChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: FilterChip(
        label: Text(label),
        selected: selected,
        onSelected: (_) => onTap(),
      ),
    );
  }
}

class _MessageDialog extends StatelessWidget {
  const _MessageDialog({
    required this.message,
    required this.onReply,
    required this.onStatus,
  });

  final Map<String, dynamic> message;
  final VoidCallback onReply;
  final ValueChanged<int> onStatus;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(asStr(message['subject'])),
      content: SizedBox(
        width: 560,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${asStr(message['from_name'])} <${asStr(message['from_email'])}>',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            Text(
              'Received ${fmtDateTime(asDate(message['sent_at']))}',
              style: const TextStyle(color: Color(0xFF607A82), fontSize: 12),
            ),
            const Divider(),
            ConstrainedBox(
              constraints: const BoxConstraints(maxHeight: 320),
              child: SingleChildScrollView(
                child: Text(asStr(message['body'])),
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Close'),
        ),
        TextButton(
          onPressed: () => onStatus(3),
          child: const Text('Archive'),
        ),
        TextButton(
          onPressed: () => onStatus(4),
          child: const Text('Trash'),
        ),
        FilledButton.icon(
          onPressed: onReply,
          icon: const Icon(Icons.reply, size: 18),
          label: const Text('Reply'),
        ),
      ],
    );
  }
}

class _ReplyDialog extends StatefulWidget {
  const _ReplyDialog({required this.message});

  final Map<String, dynamic> message;

  @override
  State<_ReplyDialog> createState() => _ReplyDialogState();
}

class _ReplyDialogState extends State<_ReplyDialog> {
  late final _body = TextEditingController();

  @override
  void dispose() {
    _body.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    if (_body.text.trim().isEmpty) {
      snack(context, 'Type a reply first.', error: true);
      return;
    }
    Navigator.of(context).pop(_body.text.trim());
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('Reply to ${widget.message['from_name']}'),
      content: SizedBox(
        width: 520,
        child: TextField(
          controller: _body,
          maxLines: 8,
          autofocus: true,
          decoration: const InputDecoration(
            hintText: 'Your reply…',
            border: OutlineInputBorder(),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(onPressed: _send, child: const Text('Send reply')),
      ],
    );
  }
}
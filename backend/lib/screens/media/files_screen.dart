import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:web/web.dart' as web;

import '../../core/api_client.dart';
import '../../core/browser.dart';
import '../../core/device_files.dart';
import '../../core/helpers.dart';
import '../../core/session_controller.dart';
import '../../core/ui.dart';

class FilesScreen extends StatefulWidget {
  const FilesScreen({super.key});

  @override
  State<FilesScreen> createState() => _FilesScreenState();
}

class _FilesScreenState extends State<FilesScreen> {
  late Future<List<Map<String, dynamic>>> _future;
  bool _uploading = false;

  @override
  void initState() {
    super.initState();
    DropZone.ensureInstalled();
    DropZone.activate(_onDroppedFiles);
    _future = _load();
  }

  @override
  void dispose() {
    DropZone.deactivate(_onDroppedFiles);
    super.dispose();
  }

  Future<List<Map<String, dynamic>>> _load() async {
    final api = context.read<SessionController>().api;
    final data = await api.get('/cpanel/jwt/uploads') as Map;
    return ((data['Files'] as List?) ?? const []).cast<Map<String, dynamic>>();
  }

  void _reload() => setState(() => _future = _load());

  Future<void> _onDroppedFiles(List<DeviceFile> files) =>
      _uploadMany(files);

  Future<void> _upload() async {
    final files = await pickDeviceFiles(
      accept: kDocumentExtensions,
      allowMultiple: true,
    );
    if (files.isEmpty || !mounted) return;
    await _uploadMany(files);
  }

  Future<void> _uploadMany(List<DeviceFile> files) async {
    if (files.isEmpty) return;
    setState(() => _uploading = true);
    final api = context.read<SessionController>().api;
    var uploaded = 0;
    try {
      for (final file in files) {
        await api.upload('/cpanel/jwt/uploads/files', file.name, file.bytes);
        uploaded++;
      }
      if (!mounted) return;
      snack(context, uploaded == 1
          ? 'Document uploaded.'
          : '$uploaded document(s) uploaded.');
      _reload();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  Future<void> _delete(Map<String, dynamic> file) async {
    final id = asInt(file['file_id']);
    final usedBy = ((file['used_by'] as List?) ?? const [])
        .cast<Map<String, dynamic>>();
    if (usedBy.isNotEmpty) {
      final titles = usedBy.map((p) => asStr(p['title'])).join(', ');
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('In use'),
          content: Text(
            'This document is referenced by ${usedBy.length} page(s): $titles. '
            'Remove the download links first, then delete the file.',
          ),
          actions: [
            FilledButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('OK'),
            ),
          ],
        ),
      );
      return;
    }
    final ok = await confirmAction(
      context,
      title: 'Delete document',
      message: 'Delete this document permanently?',
    );
    if (!ok || !mounted) return;
    final api = context.read<SessionController>().api;
    try {
      await api.delete('/cpanel/jwt/uploads/files/$id');
      if (!mounted) return;
      snack(context, 'Document deleted.');
      _reload();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    }
  }

  void _copyUrl(Map<String, dynamic> file) {
    final url = asStr(file['file_url']);
    if (url.isNotEmpty) {
      web.window.navigator.clipboard.writeText(url);
    }
    snack(context, 'URL copied: $url');
  }

  @override
  Widget build(BuildContext context) {
    final canManage = context.read<SessionController>().can('files');
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
        final files = snapshot.data!;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 4),
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    Text('${files.length} document(s)'),
                    const Spacer(),
                    FilledButton.icon(
                      onPressed: _uploading ? null : _upload,
                      icon: _uploading
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.upload_file, size: 18),
                      label: const Text('Upload'),
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
                    child: files.isEmpty
                        ? const Padding(
                            padding: EdgeInsets.all(24),
                            child: Text('No documents uploaded yet.'),
                          )
                        : DataTable(
                            headingRowHeight: 42,
                            columns: const [
                              DataColumn(label: Text('Name')),
                              DataColumn(label: Text('Format')),
                              DataColumn(label: Text('Size')),
                              DataColumn(label: Text('Usage')),
                              DataColumn(label: Text('')),
                            ],
                            rows: [
                              for (final file in files)
                                DataRow(cells: [
                                  DataCell(Text(asStr(file['file_name']),
                                      style: const TextStyle(
                                          fontWeight: FontWeight.w600))),
                                  DataCell(Text(
                                      asStr(file['file_format']).toUpperCase())),
                                  DataCell(Text(_humanSize(
                                      asStr(file['file_size'])))),
                                  DataCell(_usageCell(file)),
                                  DataCell(Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      smallIcon(Icons.link, 'Copy URL',
                                          () => _copyUrl(file)),
                                      smallIcon(Icons.open_in_new, 'Open',
                                          () => openUrl(
                                              asStr(file['file_url']))),
                                      if (canManage)
                                        smallIcon(
                                          Icons.delete_outline,
                                          'Delete',
                                          () => _delete(file),
                                          danger: true,
                                        ),
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

  Widget _usageCell(Map<String, dynamic> file) {
    final usedBy = ((file['used_by'] as List?) ?? const [])
        .cast<Map<String, dynamic>>();
    if (usedBy.isEmpty) {
      return const Text('—', style: TextStyle(color: Color(0xFF90A4AE)));
    }
    return SizedBox(
      width: 260,
      child: Text(
        usedBy.map((p) => asStr(p['title'])).join(', '),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(color: Color(0xFFB26A00)),
      ),
    );
  }
}

String _humanSize(String raw) {
  final bytes = asInt(raw);
  if (bytes == null || bytes <= 0) return raw;
  if (bytes < 1024) return '$bytes B';
  if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
  return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
}
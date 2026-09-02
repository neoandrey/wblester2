import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:web/web.dart' as web;

import '../../core/api_client.dart';
import '../../core/browser.dart';
import '../../core/device_files.dart';
import '../../core/helpers.dart';
import '../../core/session_controller.dart';
import '../../core/ui.dart';

class ImagesScreen extends StatefulWidget {
  const ImagesScreen({super.key});

  @override
  State<ImagesScreen> createState() => _ImagesScreenState();
}

class _ImagesScreenState extends State<ImagesScreen> {
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
    return ((data['Images'] as List?) ?? const [])
        .cast<Map<String, dynamic>>();
  }

  void _reload() => setState(() => _future = _load());

  Future<void> _onDroppedFiles(List<DeviceFile> files) =>
      _uploadMany(files);

  Future<void> _upload() async {
    final files = await pickDeviceFiles(
      accept: kImageExtensions,
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
        await api.upload('/cpanel/jwt/uploads/images', file.name, file.bytes);
        uploaded++;
      }
      if (!mounted) return;
      snack(context,
          uploaded == 1 ? 'Image uploaded.' : '$uploaded image(s) uploaded.');
      _reload();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  Future<void> _delete(Map<String, dynamic> image) async {
    final id = asInt(image['image_id']);
    final usedBy = ((image['used_by'] as List?) ?? const [])
        .cast<Map<String, dynamic>>();
    if (usedBy.isNotEmpty) {
      final titles = usedBy.map((p) => asStr(p['title'])).join(', ');
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('In use'),
          content: Text(
            'This image is referenced by ${usedBy.length} page(s): $titles. '
            'Remove the references first, then delete the image.',
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
      title: 'Delete image',
      message: 'Delete this image and its resized variants permanently?',
    );
    if (!ok || !mounted) return;
    final api = context.read<SessionController>().api;
    try {
      await api.delete('/cpanel/jwt/uploads/images/$id');
      if (!mounted) return;
      snack(context, 'Image deleted.');
      _reload();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    }
  }

  void _copyUrl(Map<String, dynamic> image) {
    final url = asStr(image['image_url']);
    browserCopy(url);
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
        final images = snapshot.data!;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 4),
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    Text('${images.length} image(s)'),
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
                child: images.isEmpty
                    ? const Card(
                        child: Padding(
                          padding: EdgeInsets.all(24),
                          child: Text('No images uploaded yet.'),
                        ),
                      )
                    : Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: [
                          for (final image in images)
                            _imageCard(image, canManage),
                        ],
                      ),
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _imageCard(Map<String, dynamic> image, bool canManage) {
    final url = asStr(image['image_url']);
    final usedBy = ((image['used_by'] as List?) ?? const [])
        .cast<Map<String, dynamic>>();
    final size = asStr(image['file_size']);
    return SizedBox(
      width: 220,
      child: Card(
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            InkWell(
              onTap: () => openUrl(url),
              child: SizedBox(
                height: 140,
                width: double.infinity,
                child: Image.network(
                  '$url?size=thumb',
                  fit: BoxFit.cover,
                  errorBuilder: (context, error, stack) => Container(
                    color: const Color(0xFFF1F5F7),
                    child: const Icon(Icons.broken_image_outlined,
                        size: 40, color: Color(0xFF90A4AE)),
                  ),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    asStr(image['image_name']),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '${asStr(image['image_dimensions'])} · '
                    '${_humanSize(size)}',
                    style: const TextStyle(
                      fontSize: 11.5,
                      color: Color(0xFF607A82),
                    ),
                  ),
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 4,
                    runSpacing: 4,
                    children: [
                      if (usedBy.isNotEmpty)
                        Chip(
                          visualDensity: VisualDensity.compact,
                          label: Text('${usedBy.length} page(s)'),
                          backgroundColor: const Color(0xFFFFF3E0),
                        )
                      else
                        const Chip(
                          visualDensity: VisualDensity.compact,
                          label: Text('Unused'),
                          backgroundColor: Color(0xFFE8F5E9),
                        ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      IconButton(
                        tooltip: 'Copy URL',
                        iconSize: 18,
                        icon: const Icon(Icons.link),
                        onPressed: () => _copyUrl(image),
                      ),
                      IconButton(
                        tooltip: 'Open in new tab',
                        iconSize: 18,
                        icon: const Icon(Icons.open_in_new),
                        onPressed: () => openUrl(url),
                      ),
                      const Spacer(),
                      if (canManage)
                        IconButton(
                          tooltip: 'Delete',
                          iconSize: 18,
                          icon: const Icon(Icons.delete_outline),
                          onPressed: () => _delete(image),
                        ),
                    ],
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

String _humanSize(String raw) {
  final bytes = asInt(raw);
  if (bytes == null || bytes <= 0) return raw;
  if (bytes < 1024) return '$bytes B';
  if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
  return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
}

void browserCopy(String text) {
  if (text.isEmpty) return;
  web.window.navigator.clipboard.writeText(text);
}
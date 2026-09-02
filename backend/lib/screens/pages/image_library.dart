import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/device_files.dart';
import '../../core/helpers.dart';
import '../../core/session_controller.dart';
import '../../core/ui.dart';

/// True for fields that hold an image URL (used to attach a media picker).
bool isImageField(String key) {
  final lower = key.toLowerCase();
  return lower.contains('image');
}

/// Button that opens the media library (images + files) and returns a picked
/// URL via [onPicked]. Also allows uploading new images/documents inline so
/// users can add assets while editing a page.
class ImageLibraryButton extends StatelessWidget {
  const ImageLibraryButton({super.key, required this.onPicked});

  final ValueChanged<String> onPicked;

  Future<void> _pick(BuildContext context) async {
    final api = context.read<SessionController>().api;
    List<Map<String, dynamic>> images;
    List<Map<String, dynamic>> files;
    try {
      final data = await api.get('/cpanel/jwt/uploads') as Map;
      images = ((data['Images'] as List?) ?? const [])
          .cast<Map<String, dynamic>>();
      files = ((data['Files'] as List?) ?? const []).cast<Map<String, dynamic>>();
    } on ApiException catch (error) {
      if (!context.mounted) return;
      snack(context, error.message, error: true);
      return;
    }
    if (!context.mounted) return;
    final url = await showDialog<String>(
      context: context,
      builder: (context) => _LibraryDialog(images: images, files: files),
    );
    if (url != null && url.isNotEmpty) onPicked(url);
  }

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Padding(
        padding: const EdgeInsets.only(top: 6),
        child: OutlinedButton.icon(
          style: OutlinedButton.styleFrom(
            visualDensity: VisualDensity.compact,
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            textStyle: const TextStyle(fontSize: 12),
          ),
          onPressed: () => _pick(context),
          icon: const Icon(Icons.photo_library_outlined, size: 16),
          label: const Text('Media library…'),
        ),
      ),
    );
  }
}

class _LibraryDialog extends StatefulWidget {
  const _LibraryDialog({required this.images, required this.files});

  final List<Map<String, dynamic>> images;
  final List<Map<String, dynamic>> files;

  @override
  State<_LibraryDialog> createState() => _LibraryDialogState();
}

class _LibraryDialogState extends State<_LibraryDialog> {
  late List<Map<String, dynamic>> _images = List.of(widget.images);
  late List<Map<String, dynamic>> _files = List.of(widget.files);
  int _tab = 0;
  bool _uploading = false;

  @override
  void initState() {
    super.initState();
    DropZone.ensureInstalled();
    DropZone.activate(_onDroppedFiles);
  }

  @override
  void dispose() {
    DropZone.deactivate(_onDroppedFiles);
    super.dispose();
  }

  Future<void> _onDroppedFiles(List<DeviceFile> files) =>
      _uploadMany(files, isImage: _tab == 0);

  Future<void> _reload() async {
    final api = context.read<SessionController>().api;
    try {
      final data = await api.get('/cpanel/jwt/uploads') as Map;
      if (!mounted) return;
      setState(() {
        _images = ((data['Images'] as List?) ?? const [])
            .cast<Map<String, dynamic>>();
        _files = ((data['Files'] as List?) ?? const [])
            .cast<Map<String, dynamic>>();
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    }
  }

  Future<void> _upload() async {
    final isImage = _tab == 0;
    final files = await pickDeviceFiles(
      accept: isImage ? kImageExtensions : kDocumentExtensions,
      allowMultiple: true,
    );
    if (files.isEmpty || !mounted) return;
    await _uploadMany(files, isImage: isImage);
  }

  Future<void> _uploadMany(List<DeviceFile> files,
      {required bool isImage}) async {
    if (files.isEmpty) return;
    setState(() => _uploading = true);
    final api = context.read<SessionController>().api;
    final path = isImage
        ? '/cpanel/jwt/uploads/images'
        : '/cpanel/jwt/uploads/files';
    var uploaded = 0;
    try {
      for (final file in files) {
        await api.upload(path, file.name, file.bytes);
        uploaded++;
      }
      if (!mounted) return;
      snack(context, uploaded == 1
          ? (isImage ? 'Image uploaded.' : 'Document uploaded.')
          : '$uploaded file(s) uploaded.');
      await _reload();
      if (mounted) setState(() => _tab = isImage ? 0 : 1);
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Choose media'),
      content: SizedBox(
        width: 680,
        height: 480,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SegmentedButton<int>(
              segments: const [
                ButtonSegment(value: 0, label: Text('Images')),
                ButtonSegment(value: 1, label: Text('Files / documents')),
              ],
              selected: {_tab},
              onSelectionChanged: (s) => setState(() => _tab = s.first),
            ),
            const SizedBox(height: 6),
            Align(
              alignment: Alignment.centerLeft,
              child: Text(
                'Pick one to insert its URL, or drag files onto the window '
                'to upload them to the active tab.',
                style: const TextStyle(fontSize: 11.5, color: Color(0xFF607A82)),
              ),
            ),
            const SizedBox(height: 6),
            Expanded(
              child: _tab == 0 ? _imagesPanel() : _filesPanel(),
            ),
          ],
        ),
      ),
      actions: [
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton.icon(
            onPressed: _uploading ? null : _upload,
            icon: _uploading
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.upload_file, size: 18),
            label: Text(_uploading ? 'Uploading…' : 'Upload new'),
          ),
        ),
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Close'),
        ),
      ],
    );
  }

  Widget _imagesPanel() {
    if (_images.isEmpty) {
      return const Center(child: Text('No images uploaded yet.'));
    }
    return GridView.builder(
      gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
        maxCrossAxisExtent: 150,
        mainAxisSpacing: 8,
        crossAxisSpacing: 8,
      ),
      itemCount: _images.length,
      itemBuilder: (context, index) {
        final image = _images[index];
        final url = asStr(image['image_url']);
        return InkWell(
          borderRadius: BorderRadius.circular(8),
          onTap: () => Navigator.of(context).pop(url),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: Column(
              children: [
                Expanded(
                  child: SizedBox(
                    width: double.infinity,
                    child: Image.network(
                      '$url?size=thumb',
                      fit: BoxFit.cover,
                      errorBuilder: (context, error, stack) => Container(
                        color: const Color(0xFFECEFF1),
                        child: const Icon(Icons.broken_image_outlined),
                      ),
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.all(4),
                  child: Text(
                    asStr(image['image_name']),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 11),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _filesPanel() {
    if (_files.isEmpty) {
      return const Center(child: Text('No documents uploaded yet.'));
    }
    return ListView.builder(
      itemCount: _files.length,
      itemBuilder: (context, index) {
        final file = _files[index];
        final url = asStr(file['file_url']);
        final format = asStr(file['file_format']).toUpperCase();
        return ListTile(
          dense: true,
          leading: Icon(_fileIcon(format),
              color: Theme.of(context).colorScheme.primary),
          title: Text(asStr(file['file_name']),
              maxLines: 1, overflow: TextOverflow.ellipsis),
          subtitle: Text(
              '$format · ${_humanSize(asStr(file['file_size']))}',
              style: const TextStyle(fontSize: 11)),
          trailing: const Icon(Icons.insert_link, size: 18),
          onTap: () => Navigator.of(context).pop(url),
        );
      },
    );
  }

  IconData _fileIcon(String format) {
    if (format.contains('PDF')) return Icons.picture_as_pdf_outlined;
    if (format.isEmpty) return Icons.description_outlined;
    return Icons.insert_drive_file_outlined;
  }
}

String _humanSize(String raw) {
  final bytes = asInt(raw);
  if (bytes == null || bytes <= 0) return raw;
  if (bytes < 1024) return '$bytes B';
  if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
  return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
}
import 'dart:async';
import 'dart:js_interop';

import 'package:flutter/foundation.dart';
import 'package:web/web.dart' as web;

/// Maximum number of files accepted from one picker/drop batch, so a busy
/// user can never drag 200 files and flood the API.
const int kMaxUploadBatch = 10;

const List<String> kImageExtensions = ['png', 'jpg', 'jpeg', 'gif', 'webp'];
const List<String> kDocumentExtensions = [
  'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'csv', 'rtf',
];

/// A binary file held in browser memory after the user picks or drops it.
///
/// Homegrown replacement for `file_picker`, whose web plugin threw an
/// uncaught error before opening the native dialog in this app.
class DeviceFile {
  const DeviceFile({
    required this.name,
    required this.mime,
    required this.bytes,
  });

  final String name;
  final String mime;
  final Uint8List bytes;

  int get sizeInBytes => bytes.length;
}

/// Opens the browser file selector (web only) and resolves with the chosen
/// files. A cancelled dialog resolves with an empty list.
Future<List<DeviceFile>> pickDeviceFiles({
  List<String>? accept,
  bool allowMultiple = true,
}) async {
  if (!kIsWeb) return const [];

  final input = web.HTMLInputElement()
    ..type = 'file'
    ..multiple = allowMultiple;
  if (accept != null && accept.isNotEmpty) {
    input.accept = accept.map((e) => '.$e').join(',');
  }
  web.document.body?.appendChild(input);

  final completer = Completer<List<DeviceFile>>();
  var finished = false;

  late final web.EventListener cancelListener;
  late final web.EventListener changeListener;

  void finish(List<DeviceFile> files) {
    if (finished) return;
    finished = true;
    web.window.removeEventListener('focus', cancelListener);
    input.removeEventListener('change', changeListener);
    input.remove();
    completer.complete(files);
  }

  // A focus event reaching the window means the dialog was dismissed without
  // a selection (the classic "did native cancel fire?" trick).
  cancelListener = ((web.Event _) {
    if (!finished) finish(const []);
  }).toJS;

  changeListener = ((web.Event _) {
    if (finished) return;
    final fileList = input.files;
    if (fileList == null || fileList.length == 0) {
      finish(const []);
      return;
    }
    unawaited(_readFileList(fileList).then(finish));
  }).toJS;

  web.window.addEventListener('focus', cancelListener);
  input.addEventListener('change', changeListener);
  input.click();

  return completer.future;
}

Future<List<DeviceFile>> _readFileList(web.FileList fileList) async {
  final out = <DeviceFile>[];
  final count = fileList.length;
  for (var i = 0; i < count && out.length < kMaxUploadBatch; i++) {
    final file = fileList.item(i);
    if (file == null) continue;
    try {
      out.add(await _toDeviceFile(file));
    } catch (_) {
      // Skip unreadable files rather than failing the whole batch.
    }
  }
  return out;
}

Future<DeviceFile> _toDeviceFile(web.File file) async {
  final jsBuffer = await file.arrayBuffer().toDart;
  return DeviceFile(
    name: file.name,
    mime: file.type,
    bytes: jsBuffer.toDart.asUint8List(),
  );
}

/// Global web drag-and-drop destination.
///
/// Exactly one screen (or open dialog) is the active handler at a time. A
/// LIFO list keeps the top-most *open* surface in charge, so a media dialog
/// layered over a screen receives drops while it is open and the screen takes
/// over again once it closes.
class DropZone {
  DropZone._();

  /// Non-localized "a file is currently being dragged over the window".
  static final ValueNotifier<bool> dragging = ValueNotifier(false);

  static final List<void Function(List<DeviceFile>)> _handlers = [];

  static bool _installed = false;
  static Timer? _leaveTimer;

  /// Installs the global window/document listeners once (called from the
  /// shells that mount a drop surface, not from tests/VM).
  static void ensureInstalled() {
    if (_installed || !kIsWeb) return;
    _installed = true;
    web.document.addEventListener('dragenter', onDragOver.toJS);
    web.document.addEventListener('dragover', onDragOver.toJS);
    web.document.addEventListener('dragleave', onDragLeave.toJS);
    web.document.addEventListener('drop', onDrop.toJS);
  }

  static void activate(void Function(List<DeviceFile>) handler) {
    _handlers.removeWhere((h) => identical(h, handler));
    _handlers.add(handler);
  }

  static void deactivate(void Function(List<DeviceFile>) handler) {
    _handlers.removeWhere((h) => identical(h, handler));
  }

  static web.DataTransfer? _transferOf(web.Event event) {
    try {
      return (event as web.DragEvent).dataTransfer;
    } catch (_) { // ignore: avoid_catches_without_on_clauses
      return null;
    }
  }

  static bool _containsFiles(web.Event event) {
    final transfer = _transferOf(event);
    if (transfer == null) return false;
    final types = transfer.types;
    for (var i = 0; i < types.length; i++) {
      if (types[i].toDart == 'Files') return true;
    }
    return false;
  }

  static void onDragOver(web.Event event) {
    if (!_containsFiles(event)) return;
    event.preventDefault();
    _leaveTimer?.cancel();
    dragging.value = true;
  }

  static void onDragLeave(web.Event _) {
    // Debounce: child-element leave events flicker the banner otherwise.
    _leaveTimer ??= Timer(const Duration(milliseconds: 120), () {
      dragging.value = false;
      _leaveTimer = null;
    });
  }

  static void onDrop(web.Event event) {
    _leaveTimer?.cancel();
    if (!_containsFiles(event)) return;
    event.preventDefault();
    dragging.value = false;
    final transfer = _transferOf(event);
    if (_handlers.isEmpty || transfer == null || transfer.files.length == 0) {
      return;
    }
    final handler = _handlers.last;
    unawaited(_readFileList(transfer.files).then(handler));
  }
}
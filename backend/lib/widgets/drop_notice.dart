import 'package:flutter/material.dart';

import '../core/device_files.dart';
import '../core/theme.dart';

/// Full-width banner that slides in from the top while the user drags files
/// over the window. Must be a direct child of a [Stack].
class DropNotice extends StatelessWidget {
  const DropNotice({super.key, this.message = 'Drop files to upload'});

  final String message;

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<bool>(
      valueListenable: DropZone.dragging,
      builder: (context, active, _) => Positioned(
        top: 0,
        left: 0,
        right: 0,
        child: IgnorePointer(
          child: ClipRect(
            child: AnimatedSlide(
              offset: active ? Offset.zero : const Offset(0, -1.2),
              duration: const Duration(milliseconds: 160),
              curve: Curves.easeOut,
              child: Material(
                color: kBrand,
                elevation: 6,
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(
                      horizontal: 20, vertical: 12),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.cloud_upload_outlined,
                          color: Colors.white, size: 20),
                      const SizedBox(width: 10),
                      Text(
                        message,
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/helpers.dart';
import '../core/status.dart';
import '../core/theme.dart';

void snack(BuildContext context, String message, {bool error = false}) {
  final messenger = ScaffoldMessenger.of(context);
  messenger.hideCurrentSnackBar();
  messenger.showSnackBar(
    SnackBar(
      content: Text(message),
      backgroundColor: error ? Theme.of(context).colorScheme.error : null,
    ),
  );
}

Future<bool> confirmAction(
  BuildContext context, {
  required String title,
  required String message,
  String okLabel = 'Delete',
}) async {
  final ok = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(title),
      content: Text(message),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: const Text('Cancel'),
        ),
        FilledButton(
          style: FilledButton.styleFrom(
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
          onPressed: () => Navigator.of(context).pop(true),
          child: Text(okLabel),
        ),
      ],
    ),
  );
  return ok ?? false;
}

class LoadingPane extends StatelessWidget {
  const LoadingPane({super.key});

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Padding(
        padding: EdgeInsets.all(48),
        child: CircularProgressIndicator(),
      ),
    );
  }
}

class ErrorPane extends StatelessWidget {
  const ErrorPane({super.key, required this.message, this.onRetry});

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, size: 40, color: Color(0xFFC62828)),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            if (onRetry != null) ...[
              const SizedBox(height: 16),
              OutlinedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh),
                label: const Text('Try again'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class EmptyState extends StatelessWidget {
  const EmptyState({super.key, required this.text, this.icon = Icons.inbox});

  final String text;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 40, color: const Color(0xFF9AAFB5)),
            const SizedBox(height: 10),
            Text(text, style: const TextStyle(color: Color(0xFF607A82))),
          ],
        ),
      ),
    );
  }
}

class StatCard extends StatelessWidget {
  const StatCard({
    super.key,
    required this.icon,
    required this.label,
    required this.value,
    this.onTap,
    this.accent = kBrand,
  });

  final IconData icon;
  final String label;
  final String value;
  final VoidCallback? onTap;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final widget = Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: kCardBorder),
          ),
          child: Row(
            children: [
              Container(
                width: 46,
                height: 46,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(icon, color: accent),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      value,
                      style: const TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF17242B),
                      ),
                    ),
                    Text(
                      label,
                      style: const TextStyle(
                        color: Color(0xFF607A82),
                        fontSize: 12.5,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
    return widget;
  }
}

class ChipStatus extends StatelessWidget {
  const ChipStatus({super.key, required this.spec});

  final StatusSpec spec;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
      decoration: BoxDecoration(
        color: spec.color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: spec.color.withValues(alpha: 0.45)),
      ),
      child: Text(
        spec.label,
        style: TextStyle(
          color: spec.color,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class KTextField extends StatelessWidget {
  const KTextField({
    super.key,
    required this.label,
    required this.controller,
    this.hint,
    this.number = false,
    this.password = false,
    this.lines = 1,
  });

  final String label;
  final TextEditingController controller;
  final String? hint;
  final bool number;
  final bool password;
  final int lines;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      obscureText: password,
      keyboardType: number ? TextInputType.number : null,
      inputFormatters:
          number ? [FilteringTextInputFormatter.allow(RegExp(r'[0-9-]'))] : null,
      maxLines: lines,
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        alignLabelWithHint: lines > 1,
      ),
    );
  }
}

class KDropdown<T> extends StatelessWidget {
  const KDropdown({
    super.key,
    required this.label,
    required this.value,
    required this.items,
    required this.onChanged,
    this.allowNull = false,
    this.nullLabel = '— none —',
  });

  final String label;
  final T? value;
  final Map<T, String> items;
  final ValueChanged<T?> onChanged;
  final bool allowNull;
  final String nullLabel;

  @override
  Widget build(BuildContext context) {
    final decorated = <String, T?>{
      for (final entry in items.entries) entry.value: entry.key,
      if (allowNull) nullLabel: null,
    };
    final current =
        value != null && items.containsKey(value) ? items[value] : null;
    return DropdownButtonFormField<String>(
      initialValue: current,
      decoration: InputDecoration(labelText: label),
      items: [
        for (final entry in decorated.entries)
          DropdownMenuItem(value: entry.key, child: Text(entry.key)),
      ],
      onChanged: (text) {
        onChanged(text == null ? null : decorated[text]);
      },
    );
  }
}

class ToolbarRow extends StatelessWidget {
  const ToolbarRow({super.key, required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(children: children),
    );
  }
}

Widget smallIcon(IconData icon, String tooltip, VoidCallback onTap,
    {bool danger = false}) {
  return IconButton(
    onPressed: onTap,
    tooltip: tooltip,
    visualDensity: VisualDensity.compact,
    iconSize: 18,
    color: danger ? const Color(0xFFC62828) : const Color(0xFF455A64),
    icon: Icon(icon),
  );
}

DataCell tableCell(Object? value, {bool strong = false}) {
  return DataCell(
    Text(
      asStr(value),
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
      style: strong ? const TextStyle(fontWeight: FontWeight.w600) : null,
    ),
  );
}

DataCell tableCellWidget(Widget child) => DataCell(child);
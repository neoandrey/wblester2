import 'package:flutter/material.dart';

import '../../core/helpers.dart';
import '../../core/ui.dart';
import 'image_library.dart';

class FieldSpec {
  const FieldSpec(this.key, this.label, {this.multiline = false});

  final String key;
  final String label;
  final bool multiline;
}

class BlockSpec {
  const BlockSpec(
    this.label,
    this.fields, {
    this.itemsField,
    this.itemLabel,
    this.itemFields = const [],
    this.stringItems = false,
  });

  final String label;
  final List<FieldSpec> fields;

  /// Key holding a list of items (maps, or strings when [stringItems]).
  final String? itemsField;
  final String? itemLabel;
  final List<FieldSpec> itemFields;
  final bool stringItems;
}

/// Mirrors frontend/js BLOCK_SPECS — the block set the site renderer knows.
const Map<String, BlockSpec> kBlockSpecs = {
  'jumbotron': BlockSpec('Banner carousel', [], itemsField: 'slides', itemLabel: 'Slide', itemFields: [
    FieldSpec('imageUrl', 'Image URL'),
    FieldSpec('kicker', 'Kicker line'),
    FieldSpec('title', 'Title'),
    FieldSpec('subtitle', 'Subtitle'),
  ]),
  'hero': BlockSpec('Page header image', [FieldSpec('imageUrl', 'Background image URL')]),
  'richText': BlockSpec('Rich text', [FieldSpec('html', 'HTML content', multiline: true)]),
  'cards': BlockSpec('Services grid', [
    FieldSpec('title', 'Section title'),
    FieldSpec('intro', 'Intro paragraph', multiline: true),
  ], itemsField: 'items', itemLabel: 'Card', itemFields: [
    FieldSpec('imageUrl', 'Image URL'),
    FieldSpec('title', 'Title'),
    FieldSpec('text', 'Text', multiline: true),
    FieldSpec('slug', 'Links to slug'),
  ]),
  'features': BlockSpec('Feature boxes', [
    FieldSpec('title', 'Section title'),
    FieldSpec('intro', 'Intro paragraph', multiline: true),
  ], itemsField: 'items', itemLabel: 'Feature', itemFields: [
    FieldSpec('title', 'Title'),
    FieldSpec('text', 'Text', multiline: true),
  ]),
  'steps': BlockSpec('Process steps', [
    FieldSpec('title', 'Section title'),
    FieldSpec('intro', 'Intro paragraph', multiline: true),
  ], itemsField: 'items', itemLabel: 'Step', itemFields: [
    FieldSpec('title', 'Title'),
    FieldSpec('text', 'Text', multiline: true),
  ]),
  'stats': BlockSpec('Counters band', [FieldSpec('backgroundImage', 'Background image URL')],
      itemsField: 'items', itemLabel: 'Counter', itemFields: [
    FieldSpec('value', 'Value (e.g. 30+)'),
    FieldSpec('label', 'Label'),
  ]),
  'gallery': BlockSpec('Gallery', [
    FieldSpec('title', 'Section title'),
    FieldSpec('intro', 'Intro paragraph', multiline: true),
  ], itemsField: 'items', itemLabel: 'Photo', itemFields: [
    FieldSpec('imageUrl', 'Image URL'),
    FieldSpec('caption', 'Caption'),
    FieldSpec('category', 'Filter tag'),
  ]),
  'about': BlockSpec('About split', [
    FieldSpec('title', 'Title'),
    FieldSpec('lead', 'Green lead line'),
    FieldSpec('body', 'Body HTML', multiline: true),
  ], itemsField: 'images', itemLabel: 'Photo URL', stringItems: true),
  'testimonials': BlockSpec('Testimonials', [], itemsField: 'items', itemLabel: 'Quote', itemFields: [
    FieldSpec('title', 'Headline'),
    FieldSpec('quote', 'Quote', multiline: true),
    FieldSpec('name', 'Author'),
    FieldSpec('role', 'Location / role'),
  ]),
  'partners': BlockSpec('Partners strip', [], itemsField: 'items', itemLabel: 'Chip', itemFields: [
    FieldSpec('label', 'Label'),
  ]),
  'cta': BlockSpec('CTA band', [
    FieldSpec('title', 'Title'),
    FieldSpec('text', 'Text', multiline: true),
    FieldSpec('buttonLabel', 'Button label'),
  ]),
  'contactForm': BlockSpec('Quote form', [
    FieldSpec('title', 'Title'),
    FieldSpec('intro', 'Intro', multiline: true),
  ]),
};

const List<String> kBlockTypes = [
  'jumbotron',
  'hero',
  'richText',
  'cards',
  'features',
  'steps',
  'stats',
  'gallery',
  'about',
  'testimonials',
  'partners',
  'cta',
  'contactForm',
];

/// Modal page-block editor. Returns the edited block list via Navigator.pop.
class BlocksDialog extends StatefulWidget {
  const BlocksDialog({super.key, required this.blocks});

  final List<Map<String, dynamic>> blocks;

  @override
  State<BlocksDialog> createState() => _BlocksDialogState();
}

class _BlocksDialogState extends State<BlocksDialog> {
  late final List<Map<String, dynamic>> _blocks =
      List.of(widget.blocks.map((b) => Map.of(b)));

  void _move(int index, int delta) {
    final target = index + delta;
    if (target < 0 || target >= _blocks.length) return;
    setState(() {
      final item = _blocks.removeAt(index);
      _blocks.insert(target, item);
    });
  }

  void _remove(int index) {
    setState(() => _blocks.removeAt(index));
  }

  Future<void> _edit(int index) async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) =>
          BlockDialog(type: _blocks[index]['type'] as String, existing: _blocks[index]),
    );
    if (result != null) setState(() => _blocks[index] = result);
  }

  Future<void> _add(String type) async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => BlockDialog(type: type),
    );
    if (result != null) setState(() => _blocks.add(result));
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      insetPadding: const EdgeInsets.all(24),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 720, maxHeight: 640),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 12, 8),
              child: Row(
                children: [
                  const Expanded(
                    child: Text('Content blocks',
                        style:
                            TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
                  ),
                  DropdownButton<String>(
                    hint: const Text('+ Add block…'),
                    underline: const SizedBox.shrink(),
                    items: [
                      for (final type in kBlockTypes)
                        DropdownMenuItem(value: type, child: Text(kBlockSpecs[type]!.label)),
                    ],
                    onChanged: (type) {
                      if (type != null) _add(type);
                    },
                  ),
                ],
              ),
            ),
            const Divider(height: 1),
            Expanded(
              child: _blocks.isEmpty
                  ? const EmptyState(
                      text: 'No blocks yet — add one above.',
                      icon: Icons.view_agenda_outlined,
                    )
                  : ListView(
                      padding: const EdgeInsets.all(16),
                      children: [
                        for (var i = 0; i < _blocks.length; i++)
                          _BlockCard(
                            index: i,
                            block: _blocks[i],
                            onUp: i > 0 ? () => _move(i, -1) : null,
                            onDown: i < _blocks.length - 1
                                ? () => _move(i, 1)
                                : null,
                            onEdit: () => _edit(i),
                            onDelete: () => _remove(i),
                          ),
                      ],
                    ),
            ),
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Cancel'),
                  ),
                  const SizedBox(width: 8),
                  FilledButton(
                    onPressed: () => Navigator.of(context).pop(_blocks),
                    child: const Text('Save blocks'),
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

class _BlockCard extends StatelessWidget {
  const _BlockCard({
    required this.index,
    required this.block,
    required this.onUp,
    required this.onDown,
    required this.onEdit,
    required this.onDelete,
  });

  final int index;
  final Map<String, dynamic> block;
  final VoidCallback? onUp;
  final VoidCallback? onDown;
  final VoidCallback onEdit;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final type = block['type'] as String;
    final spec = kBlockSpecs[type];
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 8, 6, 8),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: const Color(0xFF0E9F6E).withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(
                spec?.label ?? type,
                style: const TextStyle(
                  color: Color(0xFF0B7A54),
                  fontSize: 12.5,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            Expanded(
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  '#${index + 1} · ${_summary(block, spec)}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 13, color: Color(0xFF607A82)),
                ),
              ),
            ),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (onUp != null)
                  smallIcon(Icons.keyboard_arrow_up, 'Move up', onUp!),
                if (onDown != null)
                  smallIcon(Icons.keyboard_arrow_down, 'Move down', onDown!),
                smallIcon(Icons.edit_outlined, 'Edit block', onEdit),
                smallIcon(Icons.delete_outline, 'Remove block', onDelete,
                    danger: true),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _summary(Map<String, dynamic> block, BlockSpec? spec) {
    if (spec == null || spec.fields.isEmpty) return 'Add content';
    final first = spec.fields.first;
    return asStr(block[first.key]);
  }
}

/// Dialog to edit one block (its scalar fields + item lists).
class BlockDialog extends StatefulWidget {
  const BlockDialog({super.key, required this.type, this.existing});

  final String type;
  final Map<String, dynamic>? existing;

  @override
  State<BlockDialog> createState() => _BlockDialogState();
}

class _BlockDialogState extends State<BlockDialog> {
  late final BlockSpec _spec = kBlockSpecs[widget.type]!;
  late final Map<String, TextEditingController> _fields = {
    for (final field in _spec.fields)
      field.key: TextEditingController(
        text: widget.existing?[field.key]?.toString(),
      ),
  };
  late final List<dynamic> _items = List.of(
    (widget.existing?[_spec.itemsField] as List?) ?? const [],
  );

  @override
  void dispose() {
    for (final controller in _fields.values) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<String?> _promptText(String title, String initial) async {
    final controller = TextEditingController(text: initial);
    final result = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(labelText: 'Value'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(controller.text),
            child: const Text('Save'),
          ),
        ],
      ),
    );
    return result;
  }

  Future<void> _editStringItem(int index) async {
    final result = await _promptText(_spec.itemLabel ?? '', _items[index] as String);
    if (result != null && mounted) {
      setState(() => _items[index] = result);
    }
  }

  Future<void> _addStringItem() async {
    final result = await _promptText('Add ${_spec.itemLabel ?? ''}', '');
    if (result != null && mounted) setState(() => _items.add(result));
  }

  Future<void> _editMapItem(int index) async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => ItemDialog(
        spec: _spec,
        existing: _items[index] as Map<String, dynamic>?,
      ),
    );
    if (result != null && mounted) {
      setState(() => _items[index] = result);
    }
  }

  @override
  Widget build(BuildContext context) {
    final hasItems = _spec.itemsField != null;
    return Dialog(
      insetPadding: const EdgeInsets.all(24),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 560, maxHeight: 640),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text(_spec.label,
                    style: const TextStyle(
                        fontSize: 17, fontWeight: FontWeight.w700)),
              ),
            ),
            const Divider(height: 1),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  for (final field in _spec.fields)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          KTextField(
                            label: field.label,
                            controller: _fields[field.key]!,
                            lines: field.multiline ? 4 : 1,
                          ),
                          if (isImageField(field.key))
                            ImageLibraryButton(
                              onPicked: (url) =>
                                  setState(() => _fields[field.key]!.text = url),
                            ),
                        ],
                      ),
                    ),
                  if (hasItems) ...[
                    _spec.fields.isNotEmpty ? const SizedBox(height: 8) : const SizedBox(),
                    Row(
                      children: [
                        Text(
                          '${_spec.itemLabel ?? ''}s',
                          style: const TextStyle(
                              fontWeight: FontWeight.w600, fontSize: 14),
                        ),
                        const Spacer(),
                        TextButton.icon(
                          onPressed: _spec.stringItems
                              ? _addStringItem
                              : () => _addMapItem(),
                          icon: const Icon(Icons.add, size: 18),
                          label: Text('Add ${_spec.itemLabel ?? ''}'),
                        ),
                      ],
                    ),
                    if (_items.isEmpty)
                      const Padding(
                        padding: EdgeInsets.symmetric(vertical: 12),
                        child: Text('No items.',
                            style: TextStyle(color: Color(0xFF607A82))),
                      )
                    else
                      for (var i = 0; i < _items.length; i++)
                        if (_spec.stringItems)
                          _StringItemRow(
                            index: i,
                            value: _items[i] as String,
                            onEdit: () => _editStringItem(i),
                            onDelete: () => setState(() => _items.removeAt(i)),
                          )
                        else
                          _MapItemRow(
                            index: i,
                            value: _items[i] as Map<String, dynamic>,
                            spec: _spec,
                            onEdit: () => _editMapItem(i),
                            onDelete: () => setState(() => _items.removeAt(i)),
                          ),
                  ],
                ],
              ),
            ),
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Cancel'),
                  ),
                  const SizedBox(width: 8),
                  FilledButton(
                    onPressed: _save,
                    child: const Text('Save block'),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _addMapItem() {
    setState(() => _items.add(<String, dynamic>{}));
  }

  void _save() {
    final block = <String, dynamic>{'type': widget.type};
    for (final field in _spec.fields) {
      final text = _fields[field.key]!.text.trim();
      if (text.isNotEmpty) block[field.key] = text;
    }
    if (_spec.itemsField != null) block[_spec.itemsField!] = _items;
    Navigator.of(context).pop(block);
  }
}

class ItemDialog extends StatefulWidget {
  const ItemDialog({super.key, required this.spec, this.existing});

  final BlockSpec spec;
  final Map<String, dynamic>? existing;

  @override
  State<ItemDialog> createState() => _ItemDialogState();
}

class _ItemDialogState extends State<ItemDialog> {
  late final Map<String, TextEditingController> _fields = {
    for (final field in widget.spec.itemFields)
      field.key: TextEditingController(
        text: widget.existing?[field.key]?.toString(),
      ),
  };

  @override
  void dispose() {
    for (final controller in _fields.values) {
      controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('Edit ${widget.spec.itemLabel ?? ''}'),
      content: SizedBox(
        width: 460,
        child: ListView(
          shrinkWrap: true,
          children: [
            for (final field in widget.spec.itemFields)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    KTextField(
                      label: field.label,
                      controller: _fields[field.key]!,
                      lines: field.multiline ? 3 : 1,
                    ),
                    if (isImageField(field.key))
                      ImageLibraryButton(
                        onPicked: (url) =>
                            setState(() => _fields[field.key]!.text = url),
                      ),
                  ],
                ),
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
            final item = <String, dynamic>{};
            for (final field in widget.spec.itemFields) {
              final text = _fields[field.key]!.text.trim();
              if (text.isNotEmpty) item[field.key] = text;
            }
            Navigator.of(context).pop(item);
          },
          child: const Text('Save'),
        ),
      ],
    );
  }
}

class _StringItemRow extends StatelessWidget {
  const _StringItemRow({
    required this.index,
    required this.value,
    required this.onEdit,
    required this.onDelete,
  });

  final int index;
  final String value;
  final VoidCallback onEdit;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        dense: true,
        title: Text('${index + 1}. $value',
            maxLines: 1, overflow: TextOverflow.ellipsis),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            smallIcon(Icons.edit_outlined, 'Edit', onEdit),
            smallIcon(Icons.delete_outline, 'Remove', onDelete, danger: true),
          ],
        ),
      ),
    );
  }
}

class _MapItemRow extends StatelessWidget {
  const _MapItemRow({
    required this.index,
    required this.value,
    required this.spec,
    required this.onEdit,
    required this.onDelete,
  });

  final int index;
  final Map<String, dynamic> value;
  final BlockSpec spec;
  final VoidCallback onEdit;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final summary = spec.itemFields.isEmpty
        ? '(new)'
        : asStr(value[spec.itemFields.first.key]);
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        dense: true,
        title: Text('${index + 1}. $summary',
            maxLines: 1, overflow: TextOverflow.ellipsis),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            smallIcon(Icons.edit_outlined, 'Edit', onEdit),
            smallIcon(Icons.delete_outline, 'Remove', onDelete, danger: true),
          ],
        ),
      ),
    );
  }
}
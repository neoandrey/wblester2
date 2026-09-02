import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/helpers.dart';
import '../../core/session_controller.dart';
import '../../core/status.dart';
import '../../core/ui.dart';

class AuditScreen extends StatefulWidget {
  const AuditScreen({super.key});

  @override
  State<AuditScreen> createState() => _AuditScreenState();
}

class _AuditScreenState extends State<AuditScreen> {
  late Future<List<Map<String, dynamic>>> _future;
  final Set<String> _expanded = {};

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<Map<String, dynamic>>> _load() async {
    final api = context.read<SessionController>().api;
    final data = await api.get('/cpanel/jwt/data/AuditTrail?limit=100') as Map;
    final rows = List<Map<String, dynamic>>.from(data['AuditTrail'] ?? const []);
    rows.sort((a, b) {
      final at = asDate(a['change_time']);
      final bt = asDate(b['change_time']);
      if (at == null) return 1;
      if (bt == null) return -1;
      return bt.compareTo(at);
    });
    return rows;
  }

  void _reload() => setState(() => _future = _load());

  String _key(Map<String, dynamic> row) =>
      '${asStr(row['_id'])}|${row['change_time']}';

  void _toggle(Map<String, dynamic> row) {
    setState(() {
      final key = _key(row);
      if (!_expanded.remove(key)) _expanded.add(key);
    });
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
        final rows = snapshot.data!;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 12),
              child: ToolbarRow(
                children: [
                  const Text(
                    'Latest 100 operations, newest first.',
                    style: TextStyle(color: Color(0xFF607A82)),
                  ),
                  const Spacer(),
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
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                child: Card(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Column(
                      children: [
                        _headerRow(),
                        const Divider(height: 1),
                        if (rows.isEmpty)
                          const Padding(
                            padding: EdgeInsets.all(24),
                            child: Center(
                              child: Text('No audit entries yet.'),
                            ),
                          )
                        else
                          for (final row in rows)
                            _ActivityRow(
                              row: row,
                              expanded:
                                  _expanded.contains(_key(row)),
                              onToggle: () => _toggle(row),
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

  Widget _headerRow() {
    return const Padding(
      padding: EdgeInsets.fromLTRB(16, 12, 16, 12),
      child: Row(
        children: [
          SizedBox(width: 24, child: Text('')),
          SizedBox(
            width: 150,
            child: Text('When',
                style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF607A82))),
          ),
          SizedBox(
            width: 120,
            child: Text('User',
                style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF607A82))),
          ),
          SizedBox(
            width: 110,
            child: Text('Collection',
                style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF607A82))),
          ),
          SizedBox(
            width: 110,
            child: Text('Type',
                style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF607A82))),
          ),
          Expanded(
            child: Text('Description',
                style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF607A82))),
          ),
        ],
      ),
    );
  }
}

class _ActivityRow extends StatelessWidget {
  const _ActivityRow({
    required this.row,
    required this.expanded,
    required this.onToggle,
  });

  final Map<String, dynamic> row;
  final bool expanded;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    final changeType = asStr(row['change_type']);
    final username = asStr(row['username']);
    return Column(
      children: [
        InkWell(
          onTap: onToggle,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            child: Row(
              children: [
                SizedBox(
                  width: 24,
                  child: Icon(
                    expanded
                        ? Icons.keyboard_arrow_down
                        : Icons.keyboard_arrow_right,
                    size: 20,
                    color: const Color(0xFF607A82),
                  ),
                ),
                SizedBox(
                  width: 150,
                  child: Text(
                    fmtDateTime(asDate(row['change_time'])),
                    style: const TextStyle(
                        fontSize: 13, color: Color(0xFF607A82)),
                  ),
                ),
                SizedBox(
                  width: 120,
                  child: Text(
                    username.isEmpty ? '—' : username,
                    style: const TextStyle(
                        fontWeight: FontWeight.w600, fontSize: 13),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                SizedBox(
                  width: 110,
                  child: Text(
                    humanize(asStr(row['affected_table'])),
                    style: const TextStyle(fontSize: 13),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                SizedBox(
                  width: 110,
                  child: ChipStatus(
                    spec: kChangeType[changeType] ??
                        StatusSpec(changeType, const Color(0xFFB0BEC5)),
                  ),
                ),
                Expanded(
                  child: Text(
                    asStr(row['description']).isEmpty
                        ? '${humanize(asStr(row['affected_table']))} '
                            '${changeType.toLowerCase()}'
                        : asStr(row['description']),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 13.5),
                  ),
                ),
              ],
            ),
          ),
        ),
        if (expanded)
          Container(
            width: double.infinity,
            color: const Color(0xFFF4F7F9),
            padding: const EdgeInsets.fromLTRB(40, 12, 16, 14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _kv('Record', asStr(row['_id'])),
                if (row['old_data'] is Map &&
                    (row['old_data'] as Map).isNotEmpty)
                  _json('Old value', row['old_data']),
                if (row['new_data'] is Map &&
                    (row['new_data'] as Map).isNotEmpty)
                  _json('New value', row['new_data']),
                if (asStr(row['description']).isNotEmpty)
                  _kv('Description', asStr(row['description'])),
              ],
            ),
          ),
        const Divider(height: 1),
      ],
    );
  }

  Widget _kv(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(label,
                style: const TextStyle(
                    color: Color(0xFF607A82), fontSize: 13)),
          ),
          Expanded(
            child: SelectableText(value,
                style: const TextStyle(fontSize: 13.5)),
          ),
        ],
      ),
    );
  }

  Widget _json(String title, Object? value) {
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style:
                  const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
          const SizedBox(height: 4),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFFE0E7EA)),
            ),
            child: SelectableText(
              jsonPretty(value),
              style: const TextStyle(fontSize: 12.5, fontFamily: 'monospace'),
            ),
          ),
        ],
      ),
    );
  }
}
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/helpers.dart';
import '../../core/session_controller.dart';
import '../../core/ui.dart';

/// Consolidated SIEM-style log browser: merges the WebApi rotating log, the
/// backend AuditTrail and browser-reported frontend errors into one stream.
class LogsScreen extends StatefulWidget {
  const LogsScreen({super.key});

  @override
  State<LogsScreen> createState() => _LogsScreenState();
}

class _LogEntry {
  const _LogEntry({
    required this.source,
    required this.ts,
    required this.level,
    required this.page,
    required this.message,
    required this.username,
  });

  final String source;
  final String ts;
  final String level;
  final String page;
  final String message;
  final String username;

  factory _LogEntry.fromJson(Map<String, dynamic> json) => _LogEntry(
        source: asStr(json['source']),
        ts: asStr(json['ts']),
        level: asStr(json['level']).toUpperCase(),
        page: asStr(json['page']),
        message: asStr(json['message']),
        username: asStr(json['username']),
      );
}

class _LogsModel {
  const _LogsModel({required this.entries, required this.error,
      required this.warning, required this.info});

  final List<_LogEntry> entries;
  final int error;
  final int warning;
  final int info;
}

class _LogsScreenState extends State<LogsScreen> {
  String _source = 'all';
  String _level = '';
  late Future<_LogsModel> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_LogsModel> _load() async {
    final api = context.read<SessionController>().api;
    final params = <String>['limit=500'];
    if (_source != 'all') params.add('source=$_source');
    if (_level.isNotEmpty) params.add('level=$_level');
    final data = await api.get('/cpanel/jwt/logs?${params.join('&')}') as Map;
    final counts = (data['counts'] as Map?) ?? const <String, dynamic>{};
    final raw = (data['logs'] as List?) ?? const [];
    return _LogsModel(
      entries: raw
          .whereType<Map>()
          .map((e) => _LogEntry.fromJson(e.cast<String, dynamic>()))
          .toList(),
      error: asInt(counts['error']) ?? 0,
      warning: asInt(counts['warning']) ?? 0,
      info: asInt(counts['info']) ?? 0,
    );
  }

  void _reload() => setState(() => _future = _load());

  void _setSource(String? value) {
    if (value == null || value == _source) return;
    setState(() {
      _source = value;
      _future = _load();
    });
  }

  void _setLevel(String? value) {
    if (value == null || value == _level) return;
    setState(() {
      _level = value;
      _future = _load();
    });
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<_LogsModel>(
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
        final model = snapshot.data!;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      SegmentedButton<String>(
                        key: const ValueKey('log-source'),
                        segments: const [
                          ButtonSegment(value: 'all', label: Text('All')),
                          ButtonSegment(value: 'webapi', label: Text('Web API')),
                          ButtonSegment(value: 'backend', label: Text('Backend')),
                          ButtonSegment(
                              value: 'frontend', label: Text('Frontend')),
                        ],
                        selected: {_source},
                        onSelectionChanged: (s) => _setSource(s.first),
                      ),
                      const SizedBox(width: 12),
                      DropdownButton<String>(
                        key: const ValueKey('log-level'),
                        value: _level.isEmpty ? 'all' : _level,
                        items: const [
                          DropdownMenuItem(value: 'all', child: Text('Any level')),
                          DropdownMenuItem(value: 'INFO', child: Text('INFO')),
                          DropdownMenuItem(value: 'WARN', child: Text('WARN')),
                          DropdownMenuItem(value: 'ERROR', child: Text('ERROR')),
                        ],
                        onChanged: (v) =>
                            _setLevel(v == null || v == 'all' ? '' : v),
                      ),
                      const Spacer(),
                      Wrap(
                        spacing: 8,
                        children: [
                          _countChip('${model.error} errors',
                              const Color(0xFFC62828)),
                          _countChip('${model.warning} warnings',
                              const Color(0xFFB26A00)),
                          _countChip('${model.info} info',
                              const Color(0xFF2E7D32)),
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Merged stream · WebApi rotator · AuditTrail · '
                    'browser frontend reports',
                    style: const TextStyle(
                        fontSize: 11.5, color: Color(0xFF607A82)),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      OutlinedButton.icon(
                        onPressed: _reload,
                        icon: const Icon(Icons.refresh, size: 16),
                        label: const Text('Refresh'),
                      ),
                      const Spacer(),
                      Text(
                        '${model.entries.length} row(s)',
                        style: const TextStyle(
                            fontSize: 12, color: Color(0xFF607A82)),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                child: Card(
                  clipBehavior: Clip.antiAlias,
                  child: model.entries.isEmpty
                      ? const Padding(
                          padding: EdgeInsets.all(32),
                          child: Center(child: Text('No log entries.')),
                        )
                      : Column(
                          children: [
                            for (final entry in model.entries)
                              _logRow(entry),
                          ],
                        ),
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _countChip(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600),
      ),
    );
  }

  Widget _logRow(_LogEntry entry) {
    final (icon, color) = switch (entry.level) {
      'ERROR' => (Icons.error_outline, const Color(0xFFC62828)),
      'WARN' || 'WARNING' => (Icons.warning_amber_outlined,
          const Color(0xFFB26A00)),
      _ => (Icons.info_outline, const Color(0xFF2E7D32)),
    };
    final sourceColor = switch (entry.source) {
      'webapi' => const Color(0xFF1565C0),
      'backend' => const Color(0xFF6A1B9A),
      _ => const Color(0xFF00695C),
    };
    return InkWell(
      onTap: null,
      child: Container(
        padding: const EdgeInsets.fromLTRB(16, 10, 16, 10),
        decoration: const BoxDecoration(
          border: Border(bottom: BorderSide(color: Color(0xFFE8EDEF))),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: 18, color: color),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    entry.message,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        fontSize: 13.5, color: Color(0xFF17242B), height: 1.3),
                  ),
                  const SizedBox(height: 2),
                  Row(
                    children: [
                      _sourcePill(entry.source, sourceColor),
                      const SizedBox(width: 8),
                      Text(
                        entry.ts,
                        style: const TextStyle(
                            fontSize: 11.5, color: Color(0xFF90A4AE)),
                      ),
                      if (entry.page.isNotEmpty) ...[
                        const Text(' · ',
                            style: TextStyle(
                                fontSize: 11.5, color: Color(0xFF90A4AE))),
                        Expanded(
                          child: Text(
                            entry.page,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                                fontSize: 11.5, color: Color(0xFF90A4AE)),
                          ),
                        ),
                      ],
                      if (entry.username.isNotEmpty)
                        Text(
                          ' · ${entry.username}',
                          style: const TextStyle(
                              fontSize: 11.5, color: Color(0xFF607A82)),
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

  Widget _sourcePill(String source, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 1),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        source,
        style: TextStyle(
            color: color, fontSize: 10.5, fontWeight: FontWeight.w700),
      ),
    );
  }
}
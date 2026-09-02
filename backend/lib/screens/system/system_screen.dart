import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/helpers.dart';
import '../../core/session_controller.dart';
import '../../core/status.dart';
import '../../core/ui.dart';

class SystemScreen extends StatefulWidget {
  const SystemScreen({super.key});

  @override
  State<SystemScreen> createState() => _SystemScreenState();
}

class _Diagnostics {
  const _Diagnostics({
    required this.generatedAt,
    required this.overall,
    required this.services,
    required this.errorCount,
    required this.warningCount,
    required this.logs,
  });

  final String generatedAt;
  final String overall;
  final List<Map<String, dynamic>> services;
  final int errorCount;
  final int warningCount;
  final List<Map<String, dynamic>> logs;
}

class _SystemScreenState extends State<SystemScreen> {
  late Future<_Diagnostics> _future;
  String? _logFilter;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_Diagnostics> _load() async {
    final api = context.read<SessionController>().api;
    final data = await api.get('/cpanel/jwt/diagnostics') as Map;
    return _Diagnostics(
      generatedAt: asStr(data['generated_at']),
      overall: asStr(data['overall']),
      services: (data['services'] as List).cast<Map<String, dynamic>>(),
      errorCount: asInt(data['counts']?['error']) ?? 0,
      warningCount: asInt(data['counts']?['warning']) ?? 0,
      logs: (data['logs'] as List).cast<Map<String, dynamic>>(),
    );
  }

  void _reload() => setState(() => _future = _load());

  Color _overallColor(String overall) {
    switch (overall) {
      case 'up':
        return const Color(0xFF2E7D32);
      case 'attention':
        return const Color(0xFF8E6E2E);
      default:
        return const Color(0xFFC62828);
    }
  }

  Color _levelColor(String level) {
    switch (level) {
      case 'ERROR':
        return const Color(0xFFC62828);
      case 'WARNING':
        return const Color(0xFF8E6E2E);
      default:
        return const Color(0xFF1976D2);
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<_Diagnostics>(
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
        final diag = snapshot.data!;
        final filtered = _logFilter == null
            ? diag.logs
            : diag.logs.where((row) => asStr(row['level']) == _logFilter).toList();
        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Row(
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: _overallColor(diag.overall).withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                        color: _overallColor(diag.overall)
                            .withValues(alpha: 0.4)),
                  ),
                  child: Text(
                    diag.overall.toUpperCase(),
                    style: TextStyle(
                      color: _overallColor(diag.overall),
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                const Expanded(
                  child: Text(
                    'WebApi, MongoDB and Redis health plus recent log output.',
                    style: TextStyle(color: Color(0xFF607A82)),
                  ),
                ),
                IconButton(
                  tooltip: 'Refresh',
                  icon: const Icon(Icons.refresh),
                  onPressed: _reload,
                ),
              ],
            ),
            const SizedBox(height: 16),
            GridView(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                maxCrossAxisExtent: 320,
                mainAxisSpacing: 14,
                crossAxisSpacing: 14,
                childAspectRatio: 2.4,
              ),
              children: [
                for (final service in diag.services)
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Row(
                        children: [
                          Container(
                            width: 12,
                            height: 12,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: service['status'] == 'up'
                                  ? const Color(0xFF2E7D32)
                                  : service['status'] == 'down'
                                      ? const Color(0xFFC62828)
                                      : const Color(0xFFB0BEC5),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(asStr(service['name']),
                                    style: const TextStyle(
                                        fontWeight: FontWeight.w700)),
                                Text(
                                  asStr(service['detail']),
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                      color: Color(0xFF607A82),
                                      fontSize: 12),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    _CountBox(
                      label: 'Errors',
                      value: '${diag.errorCount}',
                      color: const Color(0xFFC62828),
                    ),
                    const SizedBox(width: 24),
                    _CountBox(
                      label: 'Warnings',
                      value: '${diag.warningCount}',
                      color: const Color(0xFF8E6E2E),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 14, 16, 4),
                    child: SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: Row(
                        children: [
                          _LogFilter(
                            label: 'All',
                            selected: _logFilter == null,
                            onTap: () => setState(() => _logFilter = null),
                          ),
                          for (final level in const ['ERROR', 'WARNING', 'INFO'])
                            _LogFilter(
                              label: level,
                              selected: _logFilter == level,
                              onTap: () =>
                                  setState(() => _logFilter = level),
                            ),
                        ],
                      ),
                    ),
                  ),
                  const Divider(),
                  if (filtered.isEmpty)
                    const Padding(
                      padding: EdgeInsets.all(24),
                      child: Text('No log lines.',
                          style: TextStyle(color: Color(0xFF607A82))),
                    )
                  else
                    for (final row in filtered.reversed)
                      Padding(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 6),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            SizedBox(
                              width: 150,
                              child: Text(
                                asStr(row['ts']),
                                style: const TextStyle(
                                    fontSize: 12,
                                    fontFamily: 'monospace',
                                    color: Color(0xFF607A82)),
                              ),
                            ),
                            SizedBox(
                              width: 74,
                              child: ChipStatus(
                                spec: StatusSpec(
                                  asStr(row['level']),
                                  _levelColor(asStr(row['level'])),
                                ),
                              ),
                            ),
                            Expanded(
                              child: Text(
                                asStr(row['message']),
                                style: const TextStyle(fontSize: 13),
                              ),
                            ),
                          ],
                        ),
                      ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}

class _CountBox extends StatelessWidget {
  const _CountBox({required this.label, required this.value, required this.color});

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 34,
          height: 34,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            value,
            style: TextStyle(
                color: color, fontWeight: FontWeight.w800, fontSize: 15),
          ),
        ),
        const SizedBox(width: 10),
        Text(label,
            style: const TextStyle(fontSize: 13.5, color: Color(0xFF455A64))),
      ],
    );
  }
}

class _LogFilter extends StatelessWidget {
  const _LogFilter({
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
      padding: const EdgeInsets.only(right: 8, bottom: 8),
      child: FilterChip(
        label: Text(label),
        selected: selected,
        onSelected: (_) => onTap(),
      ),
    );
  }
}
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/helpers.dart';
import '../../core/session_controller.dart';
import '../../core/status.dart';
import '../../core/ui.dart';

class JobsScreen extends StatefulWidget {
  const JobsScreen({super.key});

  @override
  State<JobsScreen> createState() => _JobsScreenState();
}

class _JobsScreenState extends State<JobsScreen> {
  late Future<List<Map<String, dynamic>>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<Map<String, dynamic>>> _load() async {
    final api = context.read<SessionController>().api;
    final data = await api.get('/cpanel/jwt/scheduler/jobs') as Map;
    return (data['Jobs'] as List).cast<Map<String, dynamic>>();
  }

  void _reload() => setState(() => _future = _load());

  Future<void> _retry(Map<String, dynamic> job) async {
    final api = context.read<SessionController>().api;
    try {
      final result = await api
          .post('/cpanel/jwt/scheduler/jobs/${job['job_id']}/retry') as Map;
      if (!mounted) return;
      snack(context, asStr(result['message'] ?? 'Job re-queued.'));
      _reload();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    }
  }

  Future<void> _detail(Map<String, dynamic> job) async {
    await showDialog<void>(
      context: context,
      builder: (context) => _JobDialog(job: job),
    );
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
        final jobs = snapshot.data!;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 12),
              child: ToolbarRow(
                children: [
                  const Text(
                    'Outbox mail jobs. Failed jobs can be retried.',
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
                    child: DataTable(
                      headingRowHeight: 42,
                      columns: const [
                        DataColumn(label: Text('Job')),
                        DataColumn(label: Text('Started')),
                        DataColumn(label: Text('Ended')),
                        DataColumn(label: Text('Progress')),
                        DataColumn(label: Text('Status')),
                        DataColumn(label: Text('Errors')),
                        DataColumn(label: Text('')),
                      ],
                      rows: [
                        if (jobs.isEmpty)
                          const DataRow(cells: [
                            DataCell(Text('')),
                            DataCell(Text('No jobs yet.')),
                            DataCell(Text('')),
                            DataCell(Text('')),
                            DataCell(Text('')),
                            DataCell(Text('')),
                            DataCell(Text('')),
                          ])
                        else
                          for (final job in jobs)
                            DataRow(
                              onSelectChanged: (_) => _detail(job),
                              cells: [
                                tableCell(job['job_id'], strong: true),
                                tableCell(fmtDateTime(
                                    asDate(job['start_time']))),
                                tableCell(fmtDateTime(asDate(job['end_time']))),
                                tableCell('${asInt(job['progress']) ?? 0}%'),
                                tableCellWidget(ChipStatus(
                                  spec: kJobStatus[asInt(job['job_status']) ??
                                          0] ??
                                      const StatusSpec(
                                          '?', Color(0xFFB0BEC5)),
                                )),
                                tableCell(job['errors'] is List
                                    ? '${(job['errors'] as List).length}'
                                    : '0'),
                                tableCellWidget(Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    if (asInt(job['job_status']) == 3)
                                      smallIcon(
                                          Icons.replay,
                                          'Retry',
                                          () => _retry(job)),
                                  ],
                                )),
                              ],
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
}

class _JobDialog extends StatelessWidget {
  const _JobDialog({required this.job});

  final Map<String, dynamic> job;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(asStr(job['job_id'])),
      content: SizedBox(
        width: 560,
        child: ListView(
          shrinkWrap: true,
          children: [
            _kv('Name', asStr(job['name'])),
            _kv('Description', asStr(job['description'])),
            _kv('Status',
                asStr(kJobStatus[asInt(job['job_status']) ?? 0]?.label ?? '')),
            _kv('Started', fmtDateTime(asDate(job['start_time']))),
            _kv('Ended', fmtDateTime(asDate(job['end_time']))),
            _kv('Complete', asStr(job['complete'])),
            _kv('Schedule', asStr(job['schedule'])),
            if (job['info'] is List && (job['info'] as List).isNotEmpty)
              _section('Info', job['info']),
            if (job['errors'] is List && (job['errors'] as List).isNotEmpty)
              _section('Errors', job['errors']),
            if (job['parameters'] is Map)
              _section('Parameters', job['parameters']),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Close'),
        ),
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
            child: Text(value,
                style: const TextStyle(fontSize: 13.5),
                textAlign: TextAlign.right),
          ),
        ],
      ),
    );
  }

  Widget _section(String title, Object? value) {
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style: const TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: const Color(0xFFF0F4F2),
              borderRadius: BorderRadius.circular(8),
            ),
            child: SelectableText(
              value is String ? value : jsonPretty(value),
              style: const TextStyle(
                  fontSize: 12.5, fontFamily: 'monospace'),
            ),
          ),
        ],
      ),
    );
  }
}
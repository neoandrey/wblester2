import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/helpers.dart';
import '../../core/session_controller.dart';
import '../../core/status.dart';
import '../../core/ui.dart';

class EventsScreen extends StatefulWidget {
  const EventsScreen({super.key});

  @override
  State<EventsScreen> createState() => _EventsScreenState();
}

class _EventsModel {
  const _EventsModel({required this.events, required this.types});

  final List<Map<String, dynamic>> events;
  final Map<int, String> types;
}

class _EventsScreenState extends State<EventsScreen> {
  late Future<_EventsModel> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_EventsModel> _load() async {
    final api = context.read<SessionController>().api;
    final eventsData = await api.get('/cpanel/jwt/scheduler/events') as Map;
    final typesData = await api.get('/cpanel/jwt/data/EventTypes') as Map;
    final events = (eventsData['Events'] as List).cast<Map<String, dynamic>>();
    final types = <int, String>{
      for (final type
          in (typesData['EventTypes'] as List).cast<Map<String, dynamic>>())
        asInt(type['type_id']) ?? 0: asStr(type['type_name']),
    };
    return _EventsModel(events: events, types: types);
  }

  void _reload() => setState(() => _future = _load());

  Future<void> _runNow(Map<String, dynamic> event) async {
    final api = context.read<SessionController>().api;
    final id = asInt(event['event_id']);
    try {
      final result = await api
          .post('/cpanel/jwt/scheduler/events/$id/run') as Map;
      if (!mounted) return;
      snack(context, asStr(result['message'] ?? 'Event enqueued.'));
      _reload();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    }
  }

  String _typeName(_EventsModel model, Map<String, dynamic> event) {
    final typeId = asInt(event['event_type']);
    return typeId == null ? '—' : (model.types[typeId] ?? 'type #$typeId');
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<_EventsModel>(
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
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 12),
              child: ToolbarRow(
                children: [
                  const Text(
                    'Scheduled events may trigger template mail on a timer.',
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
                        DataColumn(label: Text('ID')),
                        DataColumn(label: Text('Event')),
                        DataColumn(label: Text('Type')),
                        DataColumn(label: Text('Status')),
                        DataColumn(label: Text('Params')),
                        DataColumn(label: Text('Created')),
                        DataColumn(label: Text('History')),
                        DataColumn(label: Text('')),
                      ],
                      rows: [
                        if (model.events.isEmpty)
                          const DataRow(cells: [
                            DataCell(Text('')),
                            DataCell(Text('No events yet.')),
                            DataCell(Text('')),
                            DataCell(Text('')),
                            DataCell(Text('')),
                            DataCell(Text('')),
                            DataCell(Text('')),
                            DataCell(Text('')),
                          ])
                        else
                          for (final event in model.events)
                            DataRow(cells: [
                              tableCell(asInt(event['event_id']), strong: true),
                              DataCell(Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text(asStr(event['event_name']),
                                      style: const TextStyle(
                                          fontWeight: FontWeight.w600)),
                                  if (asStr(event['description']).isNotEmpty)
                                    Text(
                                      asStr(event['description']),
                                      style: const TextStyle(
                                          fontSize: 11.5,
                                          color: Color(0xFF607A82)),
                                    ),
                                ],
                              )),
                              tableCell(_typeName(model, event)),
                              tableCellWidget(ChipStatus(
                                spec: kEventStatus[
                                        asStr(event['event_status'])] ??
                                    const StatusSpec('?', Color(0xFFB0BEC5)),
                              )),
                              tableCell(
                                  event['parameters'] is Map
                                      ? '${(event['parameters'] as Map).length}'
                                      : '0'),
                              tableCell(fmtDate(
                                  asDate(event['created_datetime']))),
                              tableCell(event['job_history'] is List
                                  ? '${(event['job_history'] as List).length}'
                                  : '0'),
                              tableCellWidget(Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  smallIcon(Icons.play_arrow, 'Run now',
                                      () => _runNow(event)),
                                ],
                              )),
                            ]),
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
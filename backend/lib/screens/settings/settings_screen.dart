import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/helpers.dart';
import '../../core/session_controller.dart';
import '../../core/ui.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<Map<String, dynamic>> _load() async {
    final api = context.read<SessionController>().api;
    final data = await api.get('/cpanel/jwt/settings');
    return data is Map
        ? Map<String, dynamic>.from(data)
        : <String, dynamic>{};
  }

  void _reload() => setState(() => _future = _load());

  Future<void> _edit() async {
    final initial = await _future;
    if (!mounted) return;
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => _SettingsDialog(initial: initial),
    );
    if (result == null || !mounted) return;
    final api = context.read<SessionController>().api;
    try {
      await api.put('/cpanel/jwt/settings', body: result);
      if (!mounted) return;
      snack(context, 'Settings saved.');
      _reload();
    } on ApiException catch (error) {
      if (!mounted) return;
      snack(context, error.message, error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Map<String, dynamic>>(
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
        final settings = snapshot.data!;
        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Row(
              children: [
                const Expanded(
                  child: Text(
                    'Site settings',
                    style: TextStyle(
                        fontSize: 20, fontWeight: FontWeight.w800),
                  ),
                ),
                FilledButton.icon(
                  onPressed: _edit,
                  icon: const Icon(Icons.edit_outlined, size: 18),
                  label: const Text('Edit settings'),
                ),
              ],
            ),
            const SizedBox(height: 16),
            _SettingsCard(
              title: 'Identity',
              icon: Icons.badge_outlined,
              cells: [
                ('Site name', settings['site_name']),
                ('Site title', settings['site_title']),
                ('Site description', settings['site_description']),
                ('Keywords', settings['site_keywords']),
                ('Startup message', settings['startup_message']),
              ],
            ),
            const SizedBox(height: 14),
            _SettingsCard(
              title: 'Contact',
              icon: Icons.contact_mail_outlined,
              cells: [
                ('Address', settings['address']),
                ('Email', settings['email']),
                ('Phone number', settings['phone_number']),
                ('Contact message', settings['contact_us_message']),
                ('Google map', settings['google_map']),
              ],
            ),
            const SizedBox(height: 14),
            _SettingsCard(
              title: 'Home & accounts',
              icon: Icons.home_outlined,
              cells: [
                ('Home page id', settings['home_page_id']),
                ('Default mailing account', settings['default_mailing_account']),
                ('Sync mode', settings['sync_mode']),
                ('Timeout (minutes)', settings['time_out_minutes']),
              ],
            ),
            const SizedBox(height: 14),
            _SettingsCard(
              title: 'Structured data',
              icon: Icons.data_object,
              cells: [
                ('Mailing list', jsonPretty(settings['mailing_list'])),
                ('Social media', jsonPretty(settings['social_media'])),
                ('Overrides', jsonPretty(settings['overrides'])),
              ],
            ),
          ],
        );
      },
    );
  }
}

class _SettingsCard extends StatelessWidget {
  const _SettingsCard({
    required this.title,
    required this.icon,
    required this.cells,
  });

  final String title;
  final IconData icon;
  final List<(String, Object?)> cells;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, size: 18, color: const Color(0xFF0E9F6E)),
                const SizedBox(width: 8),
                Text(title,
                    style: const TextStyle(
                        fontWeight: FontWeight.w700, fontSize: 15)),
              ],
            ),
            const SizedBox(height: 8),
            for (final (label, value) in cells)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(
                      width: 180,
                      child: Text(
                        humanize(label),
                        style: const TextStyle(
                            color: Color(0xFF607A82), fontSize: 13),
                      ),
                    ),
                    Expanded(
                      child: Text(
                        value == null
                            ? '—'
                            : value.toString().isEmpty
                                ? '—'
                                : value.toString(),
                        style: const TextStyle(
                            fontSize: 13.5, fontWeight: FontWeight.w500),
                      ),
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

class _SettingsDialog extends StatefulWidget {
  const _SettingsDialog({required this.initial});

  final Map<String, dynamic> initial;

  @override
  State<_SettingsDialog> createState() => _SettingsDialogState();
}

class _SettingsDialogState extends State<_SettingsDialog> {
  late final Map<String, TextEditingController> _text = {
    for (final key in [
      'site_name',
      'site_title',
      'site_description',
      'site_keywords',
      'startup_message',
      'address',
      'email',
      'phone_number',
      'contact_us_message',
      'google_map',
      'default_mailing_account',
    ])
      key: TextEditingController(text: asStr(widget.initial[key])),
  };
  late final TextEditingController _homePage = TextEditingController(
      text: asStr(widget.initial['home_page_id']));
  late final TextEditingController _timeout = TextEditingController(
      text: asStr(widget.initial['time_out_minutes']));
  late final TextEditingController _syncMode = TextEditingController(
      text: asStr(widget.initial['sync_mode']));
  late final TextEditingController _mailingList = TextEditingController(
      text: jsonPretty(widget.initial['mailing_list']));
  late final TextEditingController _socialMedia = TextEditingController(
      text: jsonPretty(widget.initial['social_media']));
  late final TextEditingController _overrides = TextEditingController(
      text: jsonPretty(widget.initial['overrides']));

  @override
  void dispose() {
    for (final controller in _text.values) {
      controller.dispose();
    }
    _homePage.dispose();
    _timeout.dispose();
    _syncMode.dispose();
    _mailingList.dispose();
    _socialMedia.dispose();
    _overrides.dispose();
    super.dispose();
  }

  Map<String, dynamic> _fieldState() {
    return {
      for (final entry in _text.entries) entry.key: entry.value.text.trim(),
      'home_page_id': int.tryParse(_homePage.text.trim()) ?? 0,
      'time_out_minutes': int.tryParse(_timeout.text.trim()) ?? 0,
      'sync_mode': int.tryParse(_syncMode.text.trim()) ?? 0,
    };
  }

  void _save() {
    final fieldState = _fieldState();
    if (asStr(fieldState['site_name']).isEmpty ||
        asStr(fieldState['site_title']).isEmpty) {
      snack(context, 'Site name and site title are required.', error: true);
      return;
    }
    final mailingList = jsonDecodeSafe(_mailingList.text);
    final socialMedia = jsonDecodeSafe(_socialMedia.text);
    final overrides = jsonDecodeSafe(_overrides.text);
    if (mailingList is! List || socialMedia is! Map || overrides is! Map) {
      snack(context,
          'Mailing list, social media and overrides must be valid JSON.',
          error: true);
      return;
    }
    Navigator.of(context).pop({
      ...fieldState,
      'mailing_list': mailingList,
      'social_media': socialMedia,
      'overrides': overrides,
    });
  }

  Widget _section(String title) {
    return Padding(
      padding: const EdgeInsets.only(top: 14, bottom: 4),
      child: Text(title,
          style: const TextStyle(
              fontWeight: FontWeight.w700,
              fontSize: 15,
              color: Color(0xFF17242B))),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Edit site settings'),
      content: SizedBox(
        width: 600,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              _section('Identity'),
              for (final key in [
                'site_name',
                'site_title',
                'site_description',
                'site_keywords',
              ])
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: KTextField(
                      label: humanize(key), controller: _text[key]!),
                ),
              KTextField(
                  label: 'Startup message',
                  controller: _text['startup_message']!,
                  lines: 3),
              _section('Contact'),
              for (final key in [
                'address',
                'email',
                'phone_number',
                'contact_us_message',
                'google_map',
              ])
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: KTextField(
                      label: humanize(key), controller: _text[key]!),
                ),
              _section('Home & accounts'),
              KTextField(
                  label: 'Home page id', controller: _homePage, number: true),
              const SizedBox(height: 12),
              KTextField(
                  label: 'Default mailing account',
                  controller: _text['default_mailing_account']!),
              const SizedBox(height: 12),
              KTextField(
                  label: 'Sync mode (0 online, 1 local)',
                  controller: _syncMode,
                  number: true),
              const SizedBox(height: 12),
              KTextField(
                  label: 'Timeout (minutes)',
                  controller: _timeout,
                  number: true),
              _section('Structured data (JSON)'),
              KTextField(
                  label: 'Mailing list',
                  controller: _mailingList,
                  lines: 3),
              const SizedBox(height: 12),
              KTextField(
                  label: 'Social media',
                  controller: _socialMedia,
                  lines: 3),
              const SizedBox(height: 12),
              KTextField(label: 'Overrides', controller: _overrides, lines: 3),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(onPressed: _save, child: const Text('Save settings')),
      ],
    );
  }
}
import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/browser.dart';
import '../../core/session_controller.dart';
import '../../core/theme.dart';
import '../../core/ui.dart';
import '../../routing/app_router.dart';
import '../../widgets/drop_notice.dart';
import '../audit/audit_screen.dart';
import '../categories/categories_screen.dart';
import '../dashboard/dashboard_screen.dart';
import '../events/events_screen.dart';
import '../jobs/jobs_screen.dart';
import '../mail_templates/mail_templates_screen.dart';
import '../media/files_screen.dart';
import '../media/images_screen.dart';
import '../messages/messages_screen.dart';
import '../pages/pages_screen.dart';
import '../roles/roles_screen.dart';
import '../settings/settings_screen.dart';
import '../system/logs_screen.dart';
import '../system/system_screen.dart';
import '../users/users_screen.dart';

class AdminShell extends StatefulWidget {
  const AdminShell({super.key, required this.section});

  final String section;

  @override
  State<AdminShell> createState() => _AdminShellState();
}

/// Title-cases each word ("mail templates" -> "Mail Templates").
String _tt(String value) {
  return value
      .split(' ')
      .map((w) => w.isEmpty ? w : w[0].toUpperCase() + w.substring(1))
      .join(' ');
}

class _AdminShellState extends State<AdminShell> {
  final Map<String, Widget> _visited = {};

  /// Index of the active section within the *filtered* sidebar list. Using the
  /// unfiltered kSectionOrder here indexes past the rendered destinations for
  /// non-superusers (events/jobs/system hidden) and makes NavigationRail throw,
  /// which froze navigation after visiting Audit - index against `specs` so the
  /// highlight always points at a visible destination.
  int _indexFor(List<_SectionSpec> specs) {
    final index = specs.indexWhere((s) => s.section == widget.section);
    return index < 0 ? 0 : index;
  }

  String get _title {
    final raw = switch (widget.section) {
      'pages' => 'Pages',
      'categories' => 'Categories',
      'messages' => 'Messages',
      'mail-templates' => 'Mail templates',
      'settings' => 'Site settings',
      'users' => 'Users',
      'roles' => 'Roles & permissions',
      'images' => 'Images',
      'files' => 'Files',
      'events' => 'Scheduled events',
      'jobs' => 'Mail jobs',
      'logs' => 'System logs',
      'system' => 'System diagnostics',
      'audit' => 'Audit trail',
      _ => 'Dashboard',
    };
    return _tt(raw);
  }

  List<_SectionSpec> _sections(SessionController session) {
    final specs = <_SectionSpec>[
      const _SectionSpec(
          'dashboard', 'Dashboard', Icons.dashboard_outlined,
          selectedIcon: Icons.dashboard),
      const _SectionSpec('pages', 'Pages', Icons.description_outlined,
          selectedIcon: Icons.description),
      const _SectionSpec('categories', 'Categories', Icons.category_outlined,
          selectedIcon: Icons.category),
      const _SectionSpec('messages', 'Messages', Icons.mail_outline,
          selectedIcon: Icons.mail),
      const _SectionSpec('mail-templates', 'Mail templates',
          Icons.email_outlined, selectedIcon: Icons.email),
      const _SectionSpec('settings', 'Settings', Icons.settings_outlined,
          selectedIcon: Icons.settings),
      const _SectionSpec('users', 'Users', Icons.group_outlined,
          selectedIcon: Icons.group),
      const _SectionSpec('roles', 'Roles', Icons.admin_panel_settings_outlined,
          selectedIcon: Icons.admin_panel_settings),
      const _SectionSpec('images', 'Images', Icons.photo_library_outlined,
          selectedIcon: Icons.photo_library),
      const _SectionSpec('files', 'Files', Icons.folder_outlined,
          selectedIcon: Icons.folder),
      const _SectionSpec('events', 'Events', Icons.event_outlined,
          selectedIcon: Icons.event, superuser: true),
      const _SectionSpec('jobs', 'Jobs', Icons.fact_check_outlined,
          selectedIcon: Icons.fact_check, superuser: true),
      const _SectionSpec('logs', 'Logs', Icons.manage_search_outlined,
          selectedIcon: Icons.manage_search, superuser: true),
      const _SectionSpec('system', 'System', Icons.monitor_heart_outlined,
          selectedIcon: Icons.monitor_heart, superuser: true),
      const _SectionSpec('audit', 'Audit trail', Icons.receipt_long_outlined,
          selectedIcon: Icons.receipt_long),
    ];
    return specs.where((s) => !s.superuser || session.isSuperuser).toList();
  }

  Widget _sectionWidget(String section) {
    return _visited.putIfAbsent(section, () {
      switch (section) {
        case 'pages':
          return const PagesScreen();
        case 'categories':
          return const CategoriesScreen();
        case 'messages':
          return const MessagesScreen();
        case 'mail-templates':
          return const MailTemplatesScreen();
        case 'settings':
          return const SettingsScreen();
        case 'users':
          return const UsersScreen();
        case 'roles':
          return const RolesScreen();
        case 'images':
          return const ImagesScreen();
        case 'files':
          return const FilesScreen();
        case 'events':
          return const EventsScreen();
        case 'jobs':
          return const JobsScreen();
        case 'system':
          return const SystemScreen();
        case 'logs':
          return const LogsScreen();
        case 'audit':
          return const AuditScreen();
        case 'dashboard':
        default:
          return const DashboardScreen();
      }
    });
  }

  Future<void> _logout() async {
    final ok = await confirmAction(
      context,
      title: 'Sign out',
      message: 'Sign out of the admin portal?',
      okLabel: 'Sign out',
    );
    if (ok && mounted) {
      await context.read<SessionController>().logout();
    }
  }

  Widget _brandBlock() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 18, 12, 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          SvgPicture.asset(
            'assets/logo.svg',
            width: 38,
            height: 38,
            semanticsLabel: 'WBLester and O',
          ),
          const SizedBox(width: 10),
          const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'WBLester & O.',
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                  fontSize: 15,
                ),
              ),
              Text(
                'Admin Console',
                style: TextStyle(color: kSidebarMuted, fontSize: 11),
              ),
            ],
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionController>();
    final specs = _sections(session);
    final activeIndex = _indexFor(specs);
    final isWide = MediaQuery.sizeOf(context).width >= 1000;
    final appBar = AppBar(
      title: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(_title,
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
          Text(
            session.username,
            style: TextStyle(
              fontSize: 12,
              color: Colors.grey.shade600,
              fontWeight: FontWeight.w400,
            ),
          ),
        ],
      ),
      actions: [
        IconButton(
          tooltip: 'View website',
          icon: const Icon(Icons.open_in_new),
          onPressed: () => openUrl('/'),
        ),
        IconButton(
          tooltip: 'Reload',
          icon: const Icon(Icons.refresh),
          onPressed: () => setState(() {
            _visited.remove(widget.section);
          }),
        ),
        const SizedBox(width: 4),
        IconButton(
          tooltip: 'Sign out',
          icon: const Icon(Icons.logout),
          onPressed: _logout,
        ),
        const SizedBox(width: 12),
      ],
    );

    if (!isWide) {
      return Scaffold(
        appBar: appBar,
        drawer: Drawer(
          backgroundColor: kSidebar,
          child: SafeArea(
            child: Column(
              children: [
                _brandBlock(),
                Expanded(
                  child: ListView(
                    children: [
                      for (final (i, spec) in specs.indexed)
                        ListTile(
                          selected: i == activeIndex,
                          selectedTileColor: kSidebarSelected,
                          leading: Icon(
                            i == activeIndex ? spec.selectedIcon : spec.icon,
                            color: i == activeIndex
                                ? kSidebarSelectedFg
                                : kSidebarMuted,
                          ),
                          title: Text(
                            _tt(spec.label),
                            style: TextStyle(
                              color: i == activeIndex
                                  ? kSidebarSelectedFg
                                  : kSidebarMuted,
                              fontWeight: i == activeIndex
                                  ? FontWeight.w600
                                  : FontWeight.w400,
                            ),
                          ),
                          onTap: () {
                            Navigator.of(context).pop();
                            context.go(
                                '${appPrefix()}/app/${spec.section}');
                          },
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        body: Stack(
          children: [
            Positioned.fill(
              child: SafeArea(child: _sectionWidget(widget.section)),
            ),
            const DropNotice(),
          ],
        ),
      );
    }

    return Scaffold(
      appBar: appBar,
      body: Row(
        children: [
          _SidebarRail(
            specs: specs,
            activeIndex: activeIndex,
            brand: _brandBlock(),
            onSelect: (i) =>
                context.go('${appPrefix()}/app/${specs[i].section}'),
            onWebsite: () => openUrl('/'),
            onLogout: _logout,
          ),
          const VerticalDivider(width: 1, thickness: 1, color: kCardBorder),
          Expanded(
            child: Stack(
              children: [
                Positioned.fill(
                  child: _sectionWidget(widget.section),
                ),
                const DropNotice(),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SidebarRail extends StatelessWidget {
  const _SidebarRail({
    required this.specs,
    required this.activeIndex,
    required this.brand,
    required this.onSelect,
    required this.onWebsite,
    required this.onLogout,
  });

  final List<_SectionSpec> specs;
  final int activeIndex;
  final Widget brand;
  final ValueChanged<int> onSelect;
  final VoidCallback onWebsite;
  final VoidCallback onLogout;

  static const _divider = Color(0xFF21404F);

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 112,
      color: kSidebar,
      child: Column(
        children: [
          brand,
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(vertical: 4),
              children: [
                for (final (i, spec) in specs.indexed)
                  _RailItem(
                    spec: spec,
                    selected: i == activeIndex,
                    onTap: () => onSelect(i),
                  ),
              ],
            ),
          ),
          const Divider(height: 1, thickness: 1, color: _divider),
          _RailActions(onWebsite: onWebsite, onLogout: onLogout),
        ],
      ),
    );
  }
}

class _RailItem extends StatelessWidget {
  const _RailItem({
    required this.spec,
    required this.selected,
    required this.onTap,
  });

  final _SectionSpec spec;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 2, 8, 2),
      child: Tooltip(
        message: _tt(spec.label),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(14),
            onTap: onTap,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 150),
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 9),
              decoration: BoxDecoration(
                color: selected ? kSidebarSelected : Colors.transparent,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    selected ? spec.selectedIcon : spec.icon,
                    size: 22,
                    color: selected ? kSidebarSelectedFg : kSidebarMuted,
                  ),
                  const SizedBox(height: 5),
                  Text(
                    _tt(spec.label),
                    textAlign: TextAlign.center,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 11,
                      height: 1.15,
                      color: selected ? kSidebarSelectedFg : kSidebarMuted,
                      fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _RailActions extends StatelessWidget {
  const _RailActions({required this.onWebsite, required this.onLogout});

  final VoidCallback onWebsite;
  final VoidCallback onLogout;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 2, bottom: 10),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            tooltip: 'View website',
            icon: const Icon(Icons.open_in_new, color: kSidebarMuted),
            onPressed: onWebsite,
          ),
          IconButton(
            tooltip: 'Sign out',
            icon: const Icon(Icons.logout, color: kSidebarMuted),
            onPressed: onLogout,
          ),
        ],
      ),
    );
  }
}

class _SectionSpec {
  const _SectionSpec(
    this.section,
    this.label,
    this.icon, {
    required this.selectedIcon,
    this.superuser = false,
  });

  final String section;
  final String label;
  final IconData icon;
  final IconData selectedIcon;
  final bool superuser;
}
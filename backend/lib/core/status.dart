import 'package:flutter/material.dart';

class StatusSpec {
  const StatusSpec(this.label, this.color);

  final String label;
  final Color color;
}

/// WebApi event lifecycle (events.event_status).
const Map<String, StatusSpec> kEventStatus = {
  'OPEN': StatusSpec('OPEN', Color(0xFF0E9F6E)),
  'QUEUED': StatusSpec('QUEUED', Color(0xFF1976D2)),
  'RUNNING': StatusSpec('RUNNING', Color(0xFF7B1FA2)),
  'SUCCEEDED': StatusSpec('SUCCEEDED', Color(0xFF2E7D32)),
  'FAILED': StatusSpec('FAILED', Color(0xFFC62828)),
};

/// Outbox job state (jobs.job_status: 0..3).
const Map<int, StatusSpec> kJobStatus = {
  0: StatusSpec('QUEUED', Color(0xFF1976D2)),
  1: StatusSpec('RUNNING', Color(0xFF7B1FA2)),
  2: StatusSpec('SUCCEEDED', Color(0xFF2E7D32)),
  3: StatusSpec('FAILED', Color(0xFFC62828)),
};

/// Mailbox state (messages.status: 0..4).
const Map<int, StatusSpec> kMessageStatus = {
  0: StatusSpec('NEW', Color(0xFF0091EA)),
  1: StatusSpec('READ', Color(0xFF607D8B)),
  2: StatusSpec('REPLIED', Color(0xFF2E7D32)),
  3: StatusSpec('ARCHIVED', Color(0xFF8E6E2E)),
  4: StatusSpec('TRASHED', Color(0xFFC62828)),
};

/// RBAC access levels (-1 deny, 0 read, 1 modify, 2 full).
const Map<int, StatusSpec> kAccessLevel = {
  -1: StatusSpec('Deny', Color(0xFFC62828)),
  0: StatusSpec('Read', Color(0xFF607D8B)),
  1: StatusSpec('Modify', Color(0xFF1976D2)),
  2: StatusSpec('Full', Color(0xFF2E7D32)),
};

/// Audit change types.
const Map<String, StatusSpec> kChangeType = {
  'CREATE': StatusSpec('CREATE', Color(0xFF2E7D32)),
  'UPDATE': StatusSpec('UPDATE', Color(0xFF1976D2)),
  'DELETE': StatusSpec('DELETE', Color(0xFFC62828)),
  'LOGIN': StatusSpec('LOGIN', Color(0xFF0E9F6E)),
  'LOGIN_FAILED': StatusSpec('LOGIN FAILED', Color(0xFFC62828)),
  'PASSWORD_CHANGE': StatusSpec('PASSWORD', Color(0xFF8E6E2E)),
};

StatusSpec specFor(int? level) =>
    kAccessLevel[level] ?? const StatusSpec('Deny', Color(0xFFC62828));
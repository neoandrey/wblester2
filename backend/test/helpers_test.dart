import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:wblester/core/helpers.dart';
import 'package:wblester/core/status.dart';

void main() {
  group('asInt', () {
    test('handles int, num, string and null', () {
      expect(asInt(7), 7);
      expect(asInt(7.9), 7);
      expect(asInt('42'), 42);
      expect(asInt('nope'), isNull);
      expect(asInt(null), isNull);
    });
  });

  group('asStr / asBool', () {
    test('coerces without throwing', () {
      expect(asStr(12), '12');
      expect(asStr(null), '');
      expect(asBool(true), isTrue);
      expect(asBool('yes'), isFalse);
    });
  });

  group('asDate', () {
    test('parses ISO strings', () {
      expect(asDate(null), isNull);
      expect(asDate('2025-01-02T03:04:05'), isNotNull);
      final parsed = asDate('2025-01-02T03:04:05')!;
      expect(parsed.year, 2025);
      expect(parsed.hour, 3);
    });
  });

  group('humanize', () {
    test('title-cases snake_case keys', () {
      expect(humanize('home_page_id'), 'Home Page Id');
      expect(humanize('site_name'), 'Site Name');
      expect(humanize(''), '');
    });
  });

  group('fmtDate / fmtDateTime', () {
    test('renders dash for null', () {
      expect(fmtDate(null), '—');
      expect(fmtDateTime(null), '—');
    });

    test('formats datetimes', () {
      final value = DateTime(2025, 3, 4, 9, 30);
      expect(fmtDateTime(value), contains('2025-03-04'));
      expect(fmtDate(value), '2025-03-04');
    });
  });

  group('jsonDecodeSafe / jsonPretty', () {
    test('decodes and pretty-prints JSON', () {
      expect(jsonDecodeSafe('{'), isNull);
      expect(jsonDecodeSafe('  '), isNull);
      expect(jsonDecodeSafe('[1,2]'), [1, 2]);
      final pretty = jsonPretty({'a': 1});
      expect(pretty, contains('"a": 1'));
    });
  });

  group('status maps', () {
    test('message status labels match CMS model', () {
      expect(kMessageStatus[0]!.label, 'NEW');
      expect(kMessageStatus[1]!.label, 'READ');
      expect(kMessageStatus[2]!.label, 'REPLIED');
      expect(kMessageStatus[3]!.label, 'ARCHIVED');
      expect(kMessageStatus[4]!.label, 'TRASHED');
    });

    test('job status labels match jobs.job_status', () {
      expect(kJobStatus[0]!.label, 'QUEUED');
      expect(kJobStatus[1]!.label, 'RUNNING');
      expect(kJobStatus[2]!.label, 'SUCCEEDED');
      expect(kJobStatus[3]!.label, 'FAILED');
    });

    test('event status handles unknown gracefully', () {
      expect(kEventStatus['QUEUED']!.color, const Color(0xFF1976D2));
      expect(specFor(-1).label, 'Deny');
      expect(specFor(99).label, 'Deny');
    });
  });
}
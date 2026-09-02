import 'package:flutter/material.dart';

/// Brand palette.
const Color kBrand = Color(0xFF0E9F6E);
const Color kBrandDark = Color(0xFF0B7A54);
const Color kSidebar = Color(0xFF132B38);
const Color kSidebarMuted = Color(0xFF9FB8AE);
const Color kSidebarSelected = Color(0xFFC8E6C9);
const Color kSidebarSelectedFg = Color(0xFF1B5E20);
const Color kContentBg = Color(0xFFF3F6F4);
const Color kCardBorder = Color(0xFFE2E8E5);

ThemeData buildAdminTheme() {
  final scheme = ColorScheme.fromSeed(seedColor: kBrand);
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: kContentBg,
    appBarTheme: AppBarTheme(
      backgroundColor: Colors.white,
      foregroundColor: scheme.onSurface,
      surfaceTintColor: Colors.transparent,
      elevation: 1,
      scrolledUnderElevation: 2,
    ),
    cardTheme: CardThemeData(
      color: Colors.white,
      elevation: 0,
      margin: EdgeInsets.zero,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: kCardBorder),
      ),
    ),
    dividerTheme: const DividerThemeData(color: kCardBorder, thickness: 1),
    inputDecorationTheme: InputDecorationTheme(
      isDense: true,
      contentPadding:
          const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: kBrand,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: kBrandDark,
        side: const BorderSide(color: kBrand),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
    ),
    dataTableTheme: DataTableThemeData(
      dataRowMinHeight: 46,
      dataRowMaxHeight: 54,
      headingRowColor: const WidgetStatePropertyAll(Color(0xFF0E3A2F)),
      headingTextStyle: const TextStyle(
        color: Color(0xFFF4FAF7),
        fontWeight: FontWeight.w600,
        fontSize: 12.5,
        letterSpacing: 0.3,
      ),
      dataTextStyle: const TextStyle(
        color: Color(0xFF233238),
        fontSize: 13.5,
      ),
      dividerThickness: 0,
    ),
  );
}
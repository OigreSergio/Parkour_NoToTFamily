import 'package:flutter/material.dart';

/// The look of PkFAMILY: linen, embroidery thread and rounded corners.
///
/// The map is a piece of stitching on linen (see
/// `scripts/pk_embroidery_style.py`) and the spots are sewing pins, so the rest
/// of the app is dressed in the same colours instead of the default Material
/// blue-grey. Everything here comes from that palette — nothing invented for
/// the occasion — and the shapes are deliberately round and generous: this is
/// a family's map, not an admin console.
class PkTheme {
  const PkTheme._();

  // ---------------------------------------------------------------------
  // Thread palette — the same hexes the map style uses.
  // ---------------------------------------------------------------------

  /// The linen everything is stitched on.
  static const Color linen = Color(0xFFF1E7D3);
  static const Color linenLight = Color(0xFFFAF3E2);
  static const Color linenDeep = Color(0xFFEADCC0);

  /// Red thread — the family's own spots, and the app's main colour.
  static const Color threadRed = Color(0xFFCD7862);

  /// Orange thread — the roads on the map, highlights here.
  static const Color threadOrange = Color(0xFFD9A35E);
  static const Color threadTan = Color(0xFFC2AD83);
  static const Color threadBrown = Color(0xFF8D7350);
  static const Color threadGreen = Color(0xFF7FA05E);

  /// Blue thread — water on the map, community spots on the pins.
  static const Color threadBlue = Color(0xFF6F9CB8);
  static const Color threadPurple = Color(0xFFB391B6);

  /// Ink for text: dark brown, never pure black — like thread on cloth.
  static const Color ink = Color(0xFF4A3A28);

  /// Night version of the linen, for the dark theme: a workshop after dark.
  static const Color nightCloth = Color(0xFF241E18);
  static const Color nightClothRaised = Color(0xFF322A22);

  /// The font that carries the whole friendly tone.
  static const String fontFamily = 'Quicksand';

  /// Corner radius used by cards, sheets and inputs.
  static const double radius = 20;

  static ThemeData light() => _build(
        ColorScheme.fromSeed(
          seedColor: threadRed,
          brightness: Brightness.light,
        ).copyWith(
          primary: threadRed,
          onPrimary: Colors.white,
          secondary: threadGreen,
          tertiary: threadBlue,
          surface: linenLight,
          surfaceContainerHighest: linenDeep,
          onSurface: ink,
        ),
        scaffold: linen,
      );

  static ThemeData dark() => _build(
        ColorScheme.fromSeed(
          seedColor: threadRed,
          brightness: Brightness.dark,
        ).copyWith(
          primary: threadOrange,
          secondary: threadGreen,
          tertiary: threadBlue,
          surface: nightCloth,
          surfaceContainerHighest: nightClothRaised,
        ),
        scaffold: nightCloth,
      );

  static ThemeData _build(ColorScheme scheme, {required Color scaffold}) {
    final base = ThemeData(
      colorScheme: scheme,
      useMaterial3: true,
      fontFamily: fontFamily,
      scaffoldBackgroundColor: scaffold,
    );

    final shape = RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(radius),
    );

    return base.copyWith(
      textTheme: _textTheme(base.textTheme, scheme),
      appBarTheme: AppBarTheme(
        backgroundColor: scaffold,
        foregroundColor: scheme.onSurface,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: base.textTheme.titleLarge?.copyWith(
          fontFamily: fontFamily,
          fontWeight: FontWeight.w700,
          color: scheme.onSurface,
          letterSpacing: 0.2,
        ),
      ),
      cardTheme: CardThemeData(
        shape: shape,
        elevation: 0,
        color: scheme.surface,
        margin: EdgeInsets.zero,
      ),
      chipTheme: ChipThemeData(
        shape: StadiumBorder(
          side: BorderSide(color: scheme.outlineVariant),
        ),
        backgroundColor: scheme.surface,
        labelStyle: base.textTheme.labelLarge?.copyWith(
          fontFamily: fontFamily,
          fontWeight: FontWeight.w600,
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          shape: const StadiumBorder(),
          padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 14),
          textStyle: const TextStyle(
            fontFamily: fontFamily,
            fontWeight: FontWeight.w700,
            fontSize: 15,
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          shape: const StadiumBorder(),
          textStyle: const TextStyle(
            fontFamily: fontFamily,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          shape: const StadiumBorder(),
          textStyle: const TextStyle(
            fontFamily: fontFamily,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: scheme.primary,
        foregroundColor: scheme.onPrimary,
        shape: const StadiumBorder(),
        extendedTextStyle: const TextStyle(
          fontFamily: fontFamily,
          fontWeight: FontWeight.w700,
          fontSize: 15,
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: scheme.surface,
        indicatorColor: scheme.primary.withValues(alpha: 0.18),
        elevation: 0,
        height: 68,
        labelTextStyle: WidgetStatePropertyAll(
          TextStyle(
            fontFamily: fontFamily,
            fontWeight: FontWeight.w600,
            fontSize: 12,
            color: scheme.onSurface,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: scheme.surface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radius),
          borderSide: BorderSide(color: scheme.outlineVariant),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radius),
          borderSide: BorderSide(color: scheme.outlineVariant),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radius),
          borderSide: BorderSide(color: scheme.primary, width: 2),
        ),
      ),
      listTileTheme: ListTileThemeData(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radius - 4),
        ),
        titleTextStyle: base.textTheme.titleMedium?.copyWith(
          fontFamily: fontFamily,
          fontWeight: FontWeight.w600,
          color: scheme.onSurface,
        ),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: scheme.surface,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
        ),
      ),
      dialogTheme: DialogThemeData(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(28),
        ),
        backgroundColor: scheme.surface,
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        contentTextStyle: const TextStyle(
          fontFamily: fontFamily,
          fontWeight: FontWeight.w600,
        ),
      ),
      dividerTheme: DividerThemeData(
        color: scheme.outlineVariant.withValues(alpha: 0.6),
        space: 1,
      ),
    );
  }

  /// Titles a touch bolder and wider than Material's default — the app should
  /// read like a handwritten label, not like a form.
  static TextTheme _textTheme(TextTheme base, ColorScheme scheme) =>
      base
          .apply(fontFamily: fontFamily, bodyColor: scheme.onSurface, displayColor: scheme.onSurface)
          .copyWith(
            headlineSmall: base.headlineSmall?.copyWith(
              fontFamily: fontFamily,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.2,
            ),
            titleLarge: base.titleLarge?.copyWith(
              fontFamily: fontFamily,
              fontWeight: FontWeight.w700,
            ),
            titleMedium: base.titleMedium?.copyWith(
              fontFamily: fontFamily,
              fontWeight: FontWeight.w600,
            ),
            bodyMedium: base.bodyMedium?.copyWith(
              fontFamily: fontFamily,
              height: 1.35,
            ),
            labelLarge: base.labelLarge?.copyWith(
              fontFamily: fontFamily,
              fontWeight: FontWeight.w600,
            ),
          );
}

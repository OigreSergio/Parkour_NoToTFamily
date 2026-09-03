import 'package:flutter/material.dart';

/// The spot marker: a sewing pin, needle down, head coloured by spot status —
/// the same marker the web app uses (see `scripts/patch-gh-pages-test-free.py`).
///
/// The tip sits at the bottom centre of the widget, so a `Marker` with
/// `alignment: Alignment.topCenter` puts it exactly on the coordinates.
class SewingPin extends StatelessWidget {
  const SewingPin({
    super.key,
    required this.color,
    this.size = const Size(34, 52),
    this.selected = false,
  });

  /// Head colour. Thread palette: see [pinRed] and [pinBlue].
  final Color color;
  final Size size;
  final bool selected;

  /// Head of a spot verified by the family — red thread.
  static const Color pinRed = Color(0xFFCD7862);

  /// Head of a community spot (imported list) — blue thread.
  static const Color pinBlue = Color(0xFF6F9CB8);

  @override
  Widget build(BuildContext context) {
    return AnimatedScale(
      scale: selected ? 1.25 : 1,
      alignment: Alignment.bottomCenter,
      duration: const Duration(milliseconds: 150),
      child: CustomPaint(size: size, painter: _SewingPinPainter(color)),
    );
  }
}

class _SewingPinPainter extends CustomPainter {
  _SewingPinPainter(this.color);

  final Color color;

  // Drawn in the 34x52 viewBox of the web marker, then scaled.
  static const double _vbWidth = 34;
  static const double _vbHeight = 52;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.scale(size.width / _vbWidth, size.height / _vbHeight);

    // Drop shadow, so the pin reads over both linen and photos.
    canvas.drawShadow(
      Path()..addOval(Rect.fromCircle(center: const Offset(17, 9), radius: 7.5)),
      Colors.black54,
      2,
      false,
    );

    // Needle.
    final needle = Path()
      ..moveTo(16, 13)
      ..lineTo(18, 13)
      ..lineTo(17.6, 46)
      ..lineTo(17, 51)
      ..lineTo(16.4, 46)
      ..close();
    canvas.drawPath(needle, Paint()..color = const Color(0xFFAEB4BD));
    canvas.drawLine(
      const Offset(16.5, 14),
      const Offset(16.5, 44),
      Paint()
        ..color = const Color(0xFFE8EBEF)
        ..strokeWidth = 0.6,
    );

    // Head, with its stroke and highlight.
    canvas.drawCircle(const Offset(17, 9), 7.5, Paint()..color = color);
    canvas.drawCircle(
      const Offset(17, 9),
      7.5,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..color = Colors.black.withValues(alpha: 0.25),
    );
    canvas.drawCircle(
      const Offset(14.2, 6.4),
      2.2,
      Paint()..color = Colors.white.withValues(alpha: 0.55),
    );

    canvas.restore();
  }

  @override
  bool shouldRepaint(_SewingPinPainter oldDelegate) => oldDelegate.color != color;
}

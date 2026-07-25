import 'dart:math' as math;

import 'package:flutter/material.dart';

/// Small circular gauge showing a 1–10 difficulty, colored from green (easy)
/// through yellow/orange to red (hard) — like the tutorial list in the
/// reference design.
class DifficultyGauge extends StatelessWidget {
  const DifficultyGauge({super.key, required this.difficulty, this.size = 32});

  /// 1–10, clamped for safety.
  final int difficulty;

  final double size;

  Color get _color {
    final d = difficulty.clamp(1, 10);
    if (d <= 3) return Colors.green;
    if (d <= 5) return Colors.amber;
    if (d <= 7) return Colors.orange;
    return Colors.red;
  }

  @override
  Widget build(BuildContext context) {
    final d = difficulty.clamp(1, 10);
    return Semantics(
      label: 'Difficulty $d out of 10',
      child: SizedBox(
        width: size,
        height: size,
        child: CustomPaint(
          painter: _GaugePainter(fraction: d / 10, color: _color),
          child: Center(
            child: Text(
              '$d',
              style: TextStyle(
                fontSize: size * 0.4,
                fontWeight: FontWeight.w600,
                color: Colors.grey.shade700,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _GaugePainter extends CustomPainter {
  const _GaugePainter({required this.fraction, required this.color});

  /// 0.0–1.0 portion of the ring to fill.
  final double fraction;

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final stroke = size.width * 0.12;
    final rect = Offset(stroke / 2, stroke / 2) &
        Size(size.width - stroke, size.height - stroke);

    final track = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..color = Colors.grey.shade300;
    canvas.drawArc(rect, 0, 2 * math.pi, false, track);

    final arc = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.round
      ..color = color;
    // Start at 12 o'clock, sweep clockwise.
    canvas.drawArc(rect, -math.pi / 2, 2 * math.pi * fraction, false, arc);
  }

  @override
  bool shouldRepaint(_GaugePainter oldDelegate) =>
      oldDelegate.fraction != fraction || oldDelegate.color != color;
}

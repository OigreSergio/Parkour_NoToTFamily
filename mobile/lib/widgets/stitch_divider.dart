import 'package:flutter/material.dart';

import '../theme/pk_theme.dart';

/// A line of running stitch, the same one the map draws for its roads.
///
/// Used instead of a flat rule so the screens feel sewn together like the map,
/// rather than ruled like a form.
class StitchDivider extends StatelessWidget {
  const StitchDivider({super.key, this.color, this.height = 18});

  final Color? color;
  final double height;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: height,
      width: double.infinity,
      child: CustomPaint(
        painter: _StitchPainter(
          color ?? Theme.of(context).colorScheme.primary.withValues(alpha: 0.55),
        ),
      ),
    );
  }
}

class _StitchPainter extends CustomPainter {
  _StitchPainter(this.color);

  final Color color;

  static const double _stitch = 9;
  static const double _gap = 6;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = 2
      ..strokeCap = StrokeCap.round;

    final y = size.height / 2;
    for (var x = 0.0; x < size.width; x += _stitch + _gap) {
      canvas.drawLine(
        Offset(x, y),
        Offset((x + _stitch).clamp(0, size.width), y),
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(_StitchPainter oldDelegate) => oldDelegate.color != color;
}

/// An empty state that keeps the app's tone: a pin, a line and a nudge.
class PinnedEmptyState extends StatelessWidget {
  const PinnedEmptyState({
    super.key,
    required this.title,
    this.subtitle,
    this.action,
  });

  final String title;
  final String? subtitle;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.push_pin_outlined, size: 44, color: PkTheme.threadRed),
            const SizedBox(height: 12),
            Text(
              title,
              textAlign: TextAlign.center,
              style: theme.textTheme.titleMedium,
            ),
            if (subtitle != null) ...[
              const SizedBox(height: 6),
              Text(
                subtitle!,
                textAlign: TextAlign.center,
                style: theme.textTheme.bodyMedium
                    ?.copyWith(color: theme.colorScheme.outline),
              ),
            ],
            const SizedBox(height: 16),
            const SizedBox(width: 160, child: StitchDivider()),
            if (action != null) ...[
              const SizedBox(height: 12),
              action!,
            ],
          ],
        ),
      ),
    );
  }
}

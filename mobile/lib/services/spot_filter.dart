import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/spot.dart';

/// Cosa mostrare sulla mappa e nella lista.
///
/// Un dettaglio che sembra pedante e non lo è: filtrare per livello o per acqua
/// **nasconde anche gli spot su cui non sappiamo niente**, che sono la
/// stragrande maggioranza. Un filtro "principiante" che mostrasse anche i non
/// valutati direbbe implicitamente che sono adatti a un principiante — e
/// nessuno lo ha mai verificato. Meglio una lista corta e vera.
class SpotFilter {
  const SpotFilter({
    this.onlyWithContent = false,
    this.onlyWithWater = false,
    this.levels = const {},
  });

  /// Nasconde i segnaposto di cui si conoscono solo le coordinate.
  final bool onlyWithContent;

  /// Solo dove risulta davvero una fontanella. `hasFountain == null` non passa:
  /// "non lo sappiamo" non è "sì".
  final bool onlyWithWater;

  /// `principiante` | `intermedio` | `avanzato`. Vuoto = nessun filtro.
  final Set<String> levels;

  bool get isActive => onlyWithContent || onlyWithWater || levels.isNotEmpty;

  SpotFilter copyWith({
    bool? onlyWithContent,
    bool? onlyWithWater,
    Set<String>? levels,
  }) => SpotFilter(
    onlyWithContent: onlyWithContent ?? this.onlyWithContent,
    onlyWithWater: onlyWithWater ?? this.onlyWithWater,
    levels: levels ?? this.levels,
  );

  List<Spot> apply(List<Spot> spots) {
    if (!isActive) return spots;

    return [
      for (final s in spots)
        if (_passes(s)) s,
    ];
  }

  bool _passes(Spot s) {
    if (onlyWithContent && s.completeness == SpotCompleteness.daCompletare) {
      return false;
    }
    if (onlyWithWater && s.hasFountain != true) return false;
    if (levels.isNotEmpty && !levels.contains(s.skillLevel)) return false;
    return true;
  }
}

class SpotFilterNotifier extends Notifier<SpotFilter> {
  @override
  SpotFilter build() => const SpotFilter();

  void setOnlyWithContent(bool value) =>
      state = state.copyWith(onlyWithContent: value);

  void setOnlyWithWater(bool value) =>
      state = state.copyWith(onlyWithWater: value);

  void toggleLevel(String level) {
    final next = Set<String>.of(state.levels);
    if (!next.add(level)) next.remove(level);
    state = state.copyWith(levels: next);
  }

  void clear() => state = const SpotFilter();
}

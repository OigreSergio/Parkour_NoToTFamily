/// A place to fill a bottle near a spot.
///
/// Comes from OpenStreetMap — the same database the drinking-water apps
/// (Fontanelle, Refill and friends) are built on — so the data is as good as
/// what the local mappers have surveyed, and it improves when they do.
class WaterPoint {
  const WaterPoint({
    required this.id,
    required this.lat,
    required this.lng,
    required this.kind,
    required this.distanceMeters,
    this.name,
    this.drinkable = true,
  });

  /// OpenStreetMap node id, so the point can be looked up or fixed upstream.
  final int id;
  final double lat;
  final double lng;

  /// What OpenStreetMap calls it: `drinking_water`, `water_tap`, `water_well`,
  /// `drinking_fountain`, `fountain`, `spring`, `standpipe`… Anything not in
  /// [label] below still reads as plain drinking water, which is true of all
  /// of them — the name only says what you will be standing in front of.
  final String kind;

  /// Straight-line distance from the spot, in metres.
  final double distanceMeters;

  final String? name;

  /// False when the source is tagged as not drinkable (`drinking_water=no`).
  final bool drinkable;

  /// `Fountain`, `Tap`, `Spring`… for the UI.
  String get label => switch (kind) {
        'water_tap' => 'Tap',
        'spring' => 'Spring',
        'fountain' || 'drinking_fountain' => 'Fountain',
        'water_well' => 'Well',
        'standpipe' => 'Standpipe',
        _ => 'Drinking water',
      };
}

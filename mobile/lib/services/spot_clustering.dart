import 'dart:math' as math;

import 'package:flutter_map/flutter_map.dart' show LatLngBounds;
import 'package:latlong2/latlong.dart';

import '../models/spot.dart';

/// Un gruppo di spot vicini fra loro, oppure un singolo spot.
class SpotCluster {
  const SpotCluster(this.center, this.spots);

  final LatLng center;
  final List<Spot> spots;

  bool get isSingle => spots.length == 1;
  Spot get single => spots.first;
  int get count => spots.length;

  /// Lo spot più "raccontato" del gruppo: è quello che vale la pena mostrare
  /// nell'anteprima, non il primo capitato.
  Spot get best {
    final sorted = [...spots]
      ..sort((a, b) => b.completeness.index.compareTo(a.completeness.index));
    return sorted.first;
  }

  /// C'è almeno uno spot con qualcosa da mostrare?
  bool get hasContent =>
      spots.any((s) => s.completeness != SpotCompleteness.daCompletare);
}

/// Raggruppa gli spot per il viewport corrente.
///
/// Perché serve: la mappa porta ~1.700 spot, e costruire un widget per ognuno
/// blocca il thread di rendering — soprattutto su web. È lo stesso problema che
/// il vecchio bundle Expo risolveva creando i marker solo per il viewport e
/// sfoltendoli su griglia ai livelli di zoom bassi.
///
/// L'approccio è volutamente semplice: si scartano gli spot fuori schermo, e
/// quelli rimasti si raggruppano su una griglia la cui maglia dipende dallo
/// zoom. Niente k-means, niente albero: a questi numeri una griglia è
/// indistinguibile a occhio e costa una frazione.
class SpotClustering {
  const SpotClustering._();

  /// Oltre questo zoom si mostrano i singoli spot: si è abbastanza vicini che
  /// raggruppare nasconderebbe informazione utile.
  static const double detailZoom = 15;

  /// Margine attorno al viewport, in frazione della sua dimensione.
  ///
  /// Serve a non far comparire i marker con uno scatto sul bordo mentre si
  /// trascina la mappa.
  static const double _padding = 0.25;

  static List<SpotCluster> clusterize({
    required List<Spot> spots,
    required LatLngBounds bounds,
    required double zoom,
  }) {
    final visible = _inViewport(spots, bounds);

    if (zoom >= detailZoom || visible.length <= 30) {
      return [
        for (final s in visible) SpotCluster(s.location.toLatLng(), [s]),
      ];
    }

    // Maglia della griglia in gradi: si dimezza a ogni livello di zoom, così
    // i gruppi conservano più o meno la stessa dimensione sullo schermo.
    final cell = 360 / math.pow(2, zoom + 3);

    final buckets = <String, List<Spot>>{};
    for (final spot in visible) {
      final row = (spot.location.lat / cell).floor();
      final col = (spot.location.lng / cell).floor();
      buckets.putIfAbsent('$row:$col', () => []).add(spot);
    }

    return [
      for (final group in buckets.values) SpotCluster(_centroid(group), group),
    ];
  }

  static List<Spot> _inViewport(List<Spot> spots, LatLngBounds bounds) {
    final latPad = (bounds.north - bounds.south).abs() * _padding;
    final lngPad = (bounds.east - bounds.west).abs() * _padding;

    final south = bounds.south - latPad;
    final north = bounds.north + latPad;
    final west = bounds.west - lngPad;
    final east = bounds.east + lngPad;

    // A cavallo dell'antimeridiano il viewport "gira": west > east. Senza
    // questo caso la mappa si svuoterebbe nel Pacifico.
    final wraps = west > east;

    return [
      for (final s in spots)
        if (s.location.lat >= south &&
            s.location.lat <= north &&
            (wraps
                ? (s.location.lng >= west || s.location.lng <= east)
                : (s.location.lng >= west && s.location.lng <= east)))
          s,
    ];
  }

  static LatLng _centroid(List<Spot> spots) {
    var lat = 0.0;
    var lng = 0.0;
    for (final s in spots) {
      lat += s.location.lat;
      lng += s.location.lng;
    }
    return LatLng(lat / spots.length, lng / spots.length);
  }
}

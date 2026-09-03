import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:parkour_notot/models/spot.dart';
import 'package:parkour_notot/repositories/water_repository.dart';

Spot _spot() => Spot(
      id: 's1',
      name: 'Colle Oppio Park',
      description: '',
      location: const GeoPoint(lat: 41.8925, lng: 12.4966),
      photoUrls: const [],
      status: 'verified',
      submittedBy: null,
      verifiedAt: null,
      createdAt: DateTime(2026, 1, 1),
    );

String _overpass(List<Map<String, dynamic>> elements) =>
    jsonEncode({'elements': elements});

void main() {
  test('reads the fountains around a spot, nearest first', () async {
    final repository = WaterRepository(
      httpClient: MockClient((request) async => http.Response(
            _overpass([
              {
                'id': 2,
                'lat': 41.8955,
                'lon': 12.4966,
                'tags': {'amenity': 'drinking_water', 'name': 'Nasone'},
              },
              {
                'id': 1,
                'lat': 41.8926,
                'lon': 12.4967,
                'tags': {'amenity': 'drinking_water'},
              },
            ]),
            200,
          )),
    );

    final points = await repository.nearSpot(_spot());

    expect(points.length, 2);
    expect(points.first.id, 1, reason: 'the nearest one comes first');
    expect(points.first.distanceMeters, lessThan(30));
    expect(points.last.name, 'Nasone');
  });

  test('a source tagged as not drinkable is left out', () async {
    final repository = WaterRepository(
      httpClient: MockClient((request) async => http.Response(
            _overpass([
              {
                'id': 3,
                'lat': 41.8926,
                'lon': 12.4967,
                'tags': {'amenity': 'fountain', 'drinking_water': 'no'},
              },
            ]),
            200,
          )),
    );

    expect(await repository.nearSpot(_spot()), isEmpty);
  });

  test('an area with nothing mapped answers "none", not an error', () async {
    final repository = WaterRepository(
      httpClient: MockClient((request) async => http.Response(_overpass([]), 200)),
    );

    expect(await repository.nearSpot(_spot()), isEmpty);
  });

  test('a busy mirror is retried on the next one', () async {
    final tried = <String>[];
    final repository = WaterRepository(
      endpoints: const ['https://busy.example/api', 'https://spare.example/api'],
      httpClient: MockClient((request) async {
        tried.add(request.url.host);
        if (request.url.host == 'busy.example') {
          return http.Response('rate limited', 429);
        }
        return http.Response(
          _overpass([
            {
              'id': 9,
              'lat': 41.8926,
              'lon': 12.4967,
              'tags': {'man_made': 'water_tap'},
            },
          ]),
          200,
        );
      }),
    );

    final points = await repository.nearSpot(_spot());

    expect(tried, ['busy.example', 'spare.example']);
    expect(points.single.label, 'Tap');
  });

  test('when no mirror answers the caller is told, not fed an empty list',
      () async {
    final repository = WaterRepository(
      endpoints: const ['https://down.example/api'],
      httpClient: MockClient((request) async => http.Response('nope', 500)),
    );

    expect(
      () => repository.nearSpot(_spot()),
      throwsA(isA<WaterLookupException>()),
    );
  });

  test('the query asks for the spot coordinates and the radius', () async {
    late Uri asked;
    final repository = WaterRepository(
      httpClient: MockClient((request) async {
        asked = request.url;
        return http.Response(_overpass([]), 200);
      }),
    );

    await repository.nearSpot(_spot(), radiusMeters: 250);

    final query = asked.queryParameters['data']!;
    expect(query, contains('around:250,41.8925,12.4966'));
    expect(query, contains('drinking_water'));
  });
}

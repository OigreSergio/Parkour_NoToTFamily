import 'dart:math' as math;

import 'package:supabase_flutter/supabase_flutter.dart';

import '../models/spot.dart';

/// Legge gli spot da Supabase.
///
/// Cosa è visibile lo decidono le policy RLS sulla tabella `spots`, non questo
/// codice: un client non autenticato vede solo gli spot pubblici, e uno spot
/// `pending` è visibile al suo autore e agli admin. Il filtro qui sotto serve
/// a non scaricare l'inutile, non a proteggere niente — la protezione sta nel
/// database (`scripts/audit_rls.mjs` la verifica).
class SpotRepository {
  const SpotRepository(this._db);

  final SupabaseClient _db;

  static const String _table = 'spots';

  /// Colonne reali di `spots`, più le foto in join.
  static const String _columns =
      'id, name, lat, lng, description, skill_level, crowd_level, '
      'has_fountain, status, author_id, verified_at, created_at, '
      'spot_photos(url, author, license, source_url, source)';

  /// Spot pubblici entro [radiusMeters] da ([lat], [lng]).
  ///
  /// Il filtro geografico è un **bounding box** su `lat`/`lng`: la tabella non
  /// ha PostGIS, quindi non esiste una query per raggio. Il box è leggermente
  /// più largo del cerchio richiesto — i risultati agli angoli sono un po' più
  /// lontani di [radiusMeters]. Per la mappa va bene; se un giorno serve il
  /// raggio esatto, la strada è aggiungere PostGIS con una migration dedicata.
  Future<List<Spot>> fetchSpots({
    required double lat,
    required double lng,
    int radiusMeters = 50000,
    int limit = 500,
  }) async {
    final dLat = radiusMeters / 111320.0;
    // I meridiani si stringono verso i poli: a latitudine φ un grado di
    // longitudine vale cos(φ) volte un grado all'equatore. Il clamp evita la
    // divisione per zero ai poli.
    final cosLat = math.cos(lat * math.pi / 180).abs();
    final dLng = radiusMeters / (111320.0 * math.max(cosLat, 0.01));

    final rows = await _db
        .from(_table)
        .select(_columns)
        .gte('lat', lat - dLat)
        .lte('lat', lat + dLat)
        .gte('lng', lng - dLng)
        .lte('lng', lng + dLng)
        .limit(limit);

    return _parse(rows);
  }

  /// Un singolo spot, o null se non esiste o le RLS non lo rendono visibile.
  Future<Spot?> fetchSpot(String id) async {
    final row =
        await _db.from(_table).select(_columns).eq('id', id).maybeSingle();
    return row == null ? null : Spot.fromJson(row);
  }

  List<Spot> _parse(List<dynamic> rows) => rows
      .whereType<Map<String, dynamic>>()
      .map(Spot.fromJson)
      .toList(growable: false);
}

/// Scritture sugli spot: proposte e contributi.
///
/// Separato da [SpotRepository] perché richiede un account, mentre la lettura
/// no. Quello che passa lo decidono comunque le policy RLS: qui non c'è nessun
/// controllo di sicurezza.
class SpotWriteRepository {
  const SpotWriteRepository(this._db);

  final SupabaseClient _db;

  /// Propone un nuovo spot. Nasce `pending` e non è visibile a nessuno tranne
  /// l'autore e i moderatori, finché non viene verificato.
  ///
  /// `status` è imposto anche dalla policy di insert: passarlo qui serve a
  /// essere espliciti, non a decidere.
  Future<void> propose({
    required String name,
    required double lat,
    required double lng,
    String description = '',
    String? skillLevel,
    String? crowdLevel,
    bool? hasFountain,
  }) async {
    final userId = _db.auth.currentUser?.id;
    if (userId == null) {
      throw StateError('Serve un account per proporre uno spot.');
    }

    await _db.from('spots').insert({
      'name': name.trim(),
      'lat': lat,
      'lng': lng,
      'description': description.trim(),
      // Null quando chi propone non se la sente di valutare: è meglio di un
      // default. Vale per una proposta quanto per uno spot importato.
      'skill_level': skillLevel,
      'crowd_level': crowdLevel,
      'has_fountain': hasFountain,
      'status': 'pending',
      'author_id': userId,
      // Mai 'verificato' da qui: quello stato dice «una persona c'è stata e
      // l'ha descritto» ed è la moderazione ad accertarlo. Lasciarlo scegliere
      // a chi propone significherebbe autocertificarsi verificati.
      'completeness':
          description.trim().isEmpty ? 'da_completare' : 'arricchito',
    });
  }

  /// Aggiunge quello che si sa di uno spot già sulla mappa.
  ///
  /// Va in moderazione come una proposta: è l'unico canale da cui possono
  /// arrivare livello, affollamento e descrizione dei 1.680 spot importati.
  Future<void> contribute({
    required String spotId,
    String? description,
    String? skillLevel,
    String? crowdLevel,
    bool? hasFountain,
  }) async {
    final userId = _db.auth.currentUser?.id;
    if (userId == null) {
      throw StateError('Serve un account per contribuire.');
    }

    await _db.from('spot_contributions').insert({
      'spot_id': spotId,
      'author_id': userId,
      'description': description?.trim(),
      'skill_level': skillLevel,
      'crowd_level': crowdLevel,
      'has_fountain': hasFountain,
      'status': 'pending',
    });
  }
}

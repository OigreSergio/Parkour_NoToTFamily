import 'package:latlong2/latlong.dart';

/// Un punto geografico.
///
/// In produzione le coordinate sono due colonne numeriche (`lat`, `lng`) sulla
/// tabella `spots`: niente PostGIS, contrariamente a quanto descrive la
/// migration storica `0001_initial.sql`.
class GeoPoint {
  const GeoPoint({required this.lat, required this.lng});

  final double lat;
  final double lng;

  Map<String, dynamic> toJson() => {'lat': lat, 'lng': lng};

  LatLng toLatLng() => LatLng(lat, lng);
}

/// Quanto è completa la scheda di uno spot.
///
/// I 1.680 spot importati dalla lista Google Maps sono segnaposto: coordinate e
/// poco altro. Distinguerli da quelli davvero descritti non è un dettaglio di
/// UI — è la differenza tra una mappa informativa e una che mostra valutazioni
/// che nessuno ha dato.
enum SpotCompleteness {
  /// Solo coordinate e toponimo. Nessuno c'è ancora stato per raccontarlo.
  daCompletare,

  /// Toponimo reale, contesto da OpenStreetMap e almeno una foto con licenza.
  arricchito,

  /// Un membro della community c'è stato e l'ha descritto.
  verificato;

  static SpotCompleteness parse(String? raw) => switch (raw) {
    'arricchito' => SpotCompleteness.arricchito,
    'verificato' => SpotCompleteness.verificato,
    _ => SpotCompleteness.daCompletare,
  };

  String get label => switch (this) {
    SpotCompleteness.daCompletare => 'Da completare',
    SpotCompleteness.arricchito => 'Arricchito',
    SpotCompleteness.verificato => 'Verificato dalla community',
  };
}

/// Uno spot di parkour, nella forma in cui vive davvero su Supabase.
///
/// Colonne reali di `spots`: `id, name, lat, lng, description, skill_level,
/// crowd_level, has_fountain, status, rejection_reason, author_id,
/// verified_by, created_at, verified_at`.
///
/// Il modello resta **tollerante** come impone
/// `docs/PROJECT_RULES_AND_ROADMAP.md` §3: campi mancanti o sconosciuti hanno
/// un default e non fanno mai lanciare `fromJson`.
///
/// Una nota che vale più della struttura: [skillLevel], [crowdLevel] e
/// [hasFountain] sono **nullable, e null significa "non lo sappiamo"**. Prima
/// della pulizia del BLOCCO 3-bis tutti e 1.680 gli spot importati portavano
/// `intermedio`/`medio`/`false` — valori di default identici, mostrati come se
/// fossero valutazioni. Non riempirli con un default: mostrare "non ancora
/// valutato" è l'unica risposta onesta, ed è ciò su cui si regge la
/// qualificazione del servizio come informativo.
class Spot {
  const Spot({
    required this.id,
    required this.name,
    required this.description,
    required this.location,
    this.photos = const [],
    this.skillLevel,
    this.crowdLevel,
    this.hasFountain,
    this.status = 'verified',
    this.completeness = SpotCompleteness.daCompletare,
    this.locality,
    this.country,
    this.authorId,
    this.likes = 0,
    this.liked = false,
    this.verifiedAt,
    this.createdAt,
  });

  final String id;
  final String name;
  final String description;
  final GeoPoint location;

  /// Foto dalla tabella `spot_photos`, con la loro provenienza.
  final List<SpotPhoto> photos;

  /// `principiante` | `intermedio` | `avanzato`, oppure **null = non valutato**.
  final String? skillLevel;

  /// `tranquillo` | `medio` | `affollato`, oppure **null = non valutato**.
  final String? crowdLevel;

  /// Acqua potabile allo spot o nei pressi. **null = non lo sappiamo** — è
  /// diverso da "non c'è".
  final bool? hasFountain;

  /// `pending` | `verified` | `rejected` | `community`.
  final String status;

  final SpotCompleteness completeness;

  /// Località e paese: campi veri, non più sepolti nella descrizione.
  final String? locality;
  final String? country;

  final String? authorId;
  final int likes;
  final bool liked;
  final DateTime? verifiedAt;
  final DateTime? createdAt;

  /// Prima foto, per la miniatura in lista e sulla mappa.
  String? get previewUrl => photos.isEmpty ? null : photos.first.url;

  /// Solo gli URL, per i widget che non mostrano i crediti.
  ///
  /// Dove la foto è visibile all'utente vanno mostrati **autore e licenza**:
  /// usa [photos], non questa. Mapillary è CC-BY-SA e Wikimedia richiede
  /// attribuzione — senza crediti la foto non è pubblicabile.
  List<String> get photoUrls =>
      photos.map((p) => p.url).toList(growable: false);

  /// Etichetta del livello, o null se nessuno l'ha ancora valutato.
  ///
  /// Non esiste una difficoltà numerica: la tabella `spots` ha tre livelli
  /// testuali. Derivarne un punteggio 1–5 sarebbe precisione inventata, ed è
  /// esattamente il tipo di dato finto che il BLOCCO 3-bis rimuove.
  String? get skillLabel => switch (skillLevel) {
    'principiante' => 'Principiante',
    'intermedio' => 'Intermedio',
    'avanzato' => 'Avanzato',
    _ => null,
  };

  String? get crowdLabel => switch (crowdLevel) {
    'tranquillo' => 'Tranquillo',
    'medio' => 'Mediamente affollato',
    'affollato' => 'Affollato',
    _ => null,
  };

  bool get isRated => skillLevel != null;

  /// Dove si trova, in forma leggibile.
  String? get where {
    final parts = [locality, country].where((p) => p != null && p.isNotEmpty);
    return parts.isEmpty ? null : parts.join(', ');
  }

  /// Cosa manca perché questa scheda dica qualcosa a chi la legge.
  ///
  /// Vuota quando lo spot è completo. Serve a chiedere alla community
  /// esattamente ciò che manca, invece di un generico "aggiungi informazioni".
  List<String> get missing => [
    if (description.trim().isEmpty) 'una descrizione',
    if (photos.isEmpty) 'una foto',
    if (skillLevel == null) 'il livello',
    if (crowdLevel == null) 'quanto è affollato',
    if (hasFountain == null) 'se c\'è acqua',
  ];

  Spot copyWith({bool? liked, int? likes}) => Spot(
    id: id,
    name: name,
    description: description,
    location: location,
    photos: photos,
    skillLevel: skillLevel,
    crowdLevel: crowdLevel,
    hasFountain: hasFountain,
    status: status,
    completeness: completeness,
    locality: locality,
    country: country,
    authorId: authorId,
    likes: likes ?? this.likes,
    liked: liked ?? this.liked,
    verifiedAt: verifiedAt,
    createdAt: createdAt,
  );

  /// Aggiornamento ottimistico del like, prima della conferma dal server.
  Spot toggleLike() =>
      copyWith(liked: !liked, likes: liked ? likes - 1 : likes + 1);

  factory Spot.fromJson(Map<String, dynamic> json) {
    final photos = (json['spot_photos'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(SpotPhoto.fromJson)
        .toList(growable: false);

    return Spot(
      id: json['id'] as String,
      name: (json['name'] as String?) ?? 'Spot senza nome',
      description: (json['description'] as String?) ?? '',
      location: GeoPoint(
        lat: _toDouble(json['lat']) ?? 0,
        lng: _toDouble(json['lng']) ?? 0,
      ),
      photos: photos,
      skillLevel: _nonEmpty(json['skill_level']),
      crowdLevel: _nonEmpty(json['crowd_level']),
      hasFountain: json['has_fountain'] as bool?,
      status: (json['status'] as String?) ?? 'verified',
      completeness: SpotCompleteness.parse(json['completeness'] as String?),
      locality: _nonEmpty(json['locality']),
      country: _nonEmpty(json['country']),
      authorId: json['author_id'] as String?,
      likes: (json['likes'] as num?)?.toInt() ?? 0,
      liked: (json['liked'] as bool?) ?? false,
      verifiedAt: _toDate(json['verified_at']),
      createdAt: _toDate(json['created_at']),
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'description': description,
    'lat': location.lat,
    'lng': location.lng,
    'skill_level': skillLevel,
    'crowd_level': crowdLevel,
    'has_fountain': hasFountain,
    'status': status,
    'completeness': completeness.name,
    'locality': locality,
    'country': country,
    'author_id': authorId,
    'verified_at': verifiedAt?.toIso8601String(),
    'created_at': createdAt?.toIso8601String(),
  };
}

/// Una foto di uno spot, con la provenienza attaccata.
///
/// I crediti non sono decorativi: Mapillary pubblica in CC-BY-SA 4.0 e
/// Wikimedia Commons richiede l'attribuzione. Una foto senza autore e licenza
/// noti **non va pubblicata** — è la regola che il BLOCCO 3-bis applica al
/// posto degli hotlink attuali verso Street View e siti terzi.
class SpotPhoto {
  const SpotPhoto({
    required this.url,
    this.author,
    this.license,
    this.sourceUrl,
    this.source,
  });

  final String url;
  final String? author;
  final String? license;
  final String? sourceUrl;

  /// `mapillary` | `wikimedia` | `community`.
  final String? source;

  /// Riga di credito da mostrare sotto la foto, o null se non c'è nulla da
  /// dichiarare (foto caricata dalla community, il cui autore è l'utente).
  String? get credit {
    final parts = [author, license].where((p) => p != null && p.isNotEmpty);
    return parts.isEmpty ? null : parts.join(' · ');
  }

  factory SpotPhoto.fromJson(Map<String, dynamic> json) => SpotPhoto(
    url: (json['url'] as String?) ?? '',
    author: _nonEmpty(json['author']),
    license: _nonEmpty(json['license']),
    sourceUrl: _nonEmpty(json['source_url']),
    source: _nonEmpty(json['source']),
  );
}

double? _toDouble(Object? v) => switch (v) {
  num n => n.toDouble(),
  String s => double.tryParse(s),
  _ => null,
};

DateTime? _toDate(Object? v) => v is String ? DateTime.tryParse(v) : null;

String? _nonEmpty(Object? v) {
  final s = v as String?;
  return (s == null || s.isEmpty) ? null : s;
}

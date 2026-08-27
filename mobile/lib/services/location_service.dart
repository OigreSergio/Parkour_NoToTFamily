import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';

/// Esito di una richiesta di posizione.
///
/// Un enum invece di un `LatLng?`: la mappa deve poter distinguere «non l'ho
/// chiesto» da «l'utente ha detto no» da «il GPS è spento», perché sono tre
/// messaggi diversi da dare a chi guarda.
enum LocationStatus {
  notRequested,
  granted,
  denied,
  deniedForever,
  serviceOff,
  error,
}

class LocationResult {
  const LocationResult(this.status, [this.position]);

  final LocationStatus status;
  final LatLng? position;

  bool get hasPosition => position != null;
}

/// Posizione del dispositivo, chiesta **solo quando serve davvero**.
///
/// La differenza rispetto a prima non è cosmetica: il permesso veniva richiesto
/// all'avvio, perché la mappa aveva bisogno di un centro. Chiedere l'accesso
/// alla posizione precisa senza che l'utente abbia fatto niente, e senza
/// spiegargli perché, è la richiesta che la gente nega per riflesso — e
/// giustamente.
///
/// Ora il centro iniziale è [fallbackCenter] e la posizione si chiede solo al
/// tocco di «dove sono» o «percorso», dopo una schermata che dice a cosa serve.
///
/// **La posizione non viene salvata né trasmessa.** Non finisce su Supabase,
/// non entra nei log, non viene messa in cache: resta nel dispositivo per il
/// tempo di centrare la mappa o calcolare una distanza. È il motivo per cui
/// nell'informativa il trattamento "geolocalizzazione" ha come conservazione
/// «nessuna».
class LocationService {
  const LocationService();

  /// Centro di ripiego: Roma. Usato all'avvio e quando la posizione non è
  /// disponibile, così la mappa ha sempre qualcosa da mostrare.
  static const LatLng fallbackCenter = LatLng(41.9028, 12.4964);

  /// Chiede la posizione. Da chiamare **solo** in risposta a un gesto
  /// dell'utente, mai all'avvio.
  Future<LocationResult> request() async {
    try {
      if (!await Geolocator.isLocationServiceEnabled()) {
        return const LocationResult(LocationStatus.serviceOff);
      }

      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }

      if (permission == LocationPermission.deniedForever) {
        return const LocationResult(LocationStatus.deniedForever);
      }
      if (permission == LocationPermission.denied) {
        return const LocationResult(LocationStatus.denied);
      }

      final pos = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        // Senza limite, su un dispositivo con GPS debole la richiesta resta
        // appesa e il pulsante «dove sono» sembra rotto.
        timeLimit: const Duration(seconds: 15),
      );
      return LocationResult(
        LocationStatus.granted,
        LatLng(pos.latitude, pos.longitude),
      );
    } catch (_) {
      // Plugin assente (nei test), timeout, errori hardware: la mappa continua
      // a funzionare dal centro di ripiego.
      return const LocationResult(LocationStatus.error);
    }
  }

  /// Il permesso è già stato concesso in passato?
  ///
  /// Non chiede niente e non apre nessun dialogo: serve solo a sapere se il
  /// pulsante «dove sono» porterà a una richiesta di sistema o a una risposta
  /// immediata.
  Future<bool> hasPermission() async {
    try {
      final p = await Geolocator.checkPermission();
      return p == LocationPermission.always ||
          p == LocationPermission.whileInUse;
    } catch (_) {
      return false;
    }
  }

  /// Distanza in metri fra due punti, sul dispositivo.
  static double distanceMeters(LatLng a, LatLng b) =>
      const Distance().as(LengthUnit.Meter, a, b);
}

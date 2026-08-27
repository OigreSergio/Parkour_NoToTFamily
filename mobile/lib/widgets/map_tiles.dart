import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:vector_map_tiles/vector_map_tiles.dart';

/// Lo sfondo della mappa.
///
/// **Perché non i tile di OpenStreetMap.** Fino a ieri la mappa usava
/// `tile.openstreetmap.org`, che la [Tile Usage Policy](https://operations.osmfoundation.org/policies/tiles/)
/// di OSM riserva a usi modesti e vieta esplicitamente alle app distribuite:
/// quei server sono pagati da donazioni e non sono un CDN gratuito. Non era una
/// questione di limiti tecnici, era un uso che non ci spettava.
///
/// **Perché OpenFreeMap.** È gratuito, senza chiave e senza quota, e chi lo
/// gestisce lo dichiara esplicitamente aperto all'uso pubblico. Serve tile
/// vettoriali, quindi il rendering avviene sul dispositivo: pesa un po' di più
/// sulla CPU di un'immagine già pronta, ma è l'unica sorgente conforme che non
/// costi niente a un progetto senza budget.
///
/// **Se un giorno servisse cambiare.** Lo stile è configurabile a build time
/// (`--dart-define=MAP_STYLE_URL=...`): con una chiave MapTiler o Stadia si
/// passa a un altro fornitore senza toccare il codice.
class OpenFreeMapLayer extends StatelessWidget {
  const OpenFreeMapLayer({super.key});

  static const String styleUrl = String.fromEnvironment(
    'MAP_STYLE_URL',
    defaultValue: 'https://tiles.openfreemap.org/styles/liberty',
  );

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Style>(
      future: _style,
      builder: (context, snapshot) {
        if (snapshot.hasError) {
          // Senza sfondo la mappa non è inutile: i marker restano al loro
          // posto e le coordinate pure. Meglio una mappa spoglia di una
          // schermata di errore.
          return const _BlankBackdrop();
        }
        if (!snapshot.hasData) return const _BlankBackdrop();

        return VectorTileLayer(
          theme: snapshot.data!.theme,
          sprites: snapshot.data!.sprites,
          tileProviders: snapshot.data!.providers,
          // I tile vettoriali si ridisegnano a ogni frame di zoom: senza
          // questo, su web lo scroll diventa a scatti.
          layerMode: VectorTileLayerMode.raster,
          tileOffset: TileOffset.DEFAULT,
        );
      },
    );
  }

  static Future<Style>? _cached;
  static Future<Style> get _style =>
      _cached ??= StyleReader(uri: styleUrl).read();
}

class _BlankBackdrop extends StatelessWidget {
  const _BlankBackdrop();

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      child: const SizedBox.expand(),
    );
  }
}

/// L'attribuzione a OpenStreetMap.
///
/// Non è una cortesia: i dati OSM sono sotto ODbL, che **richiede** di citare
/// la fonte. Una mappa senza questa riga sta violando la licenza dei dati che
/// mostra.
class MapAttribution extends StatelessWidget {
  const MapAttribution({super.key});

  @override
  Widget build(BuildContext context) {
    return RichAttributionWidget(
      alignment: AttributionAlignment.bottomRight,
      attributions: [
        TextSourceAttribution(
          '© OpenStreetMap',
          onTap:
              () => launchUrl(
                Uri.parse('https://www.openstreetmap.org/copyright'),
                mode: LaunchMode.externalApplication,
              ),
        ),
        TextSourceAttribution(
          'OpenFreeMap',
          onTap:
              () => launchUrl(
                Uri.parse('https://openfreemap.org/'),
                mode: LaunchMode.externalApplication,
              ),
        ),
      ],
    );
  }
}

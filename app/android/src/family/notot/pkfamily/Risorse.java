package family.notot.pkfamily;

import android.content.res.AssetFileDescriptor;
import android.content.res.AssetManager;
import android.net.Uri;
import android.webkit.WebResourceResponse;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.HashMap;
import java.util.Map;

/**
 * Dà all'app i suoi file, presi da dentro l'APK, fingendo che arrivino dalla
 * rete.
 *
 * Perché non `file:///android_asset/`. L'app è fatta di moduli ES che si
 * chiamano fra loro, legge i dati con `fetch` e tiene le preferenze in
 * IndexedDB; da `file://` nessuna delle tre cose funziona, e il service
 * worker — cioè l'offline vero — non esiste proprio.
 *
 * Perché non un piccolo server su `127.0.0.1`. Perché la porta la sceglie il
 * sistema e cambia a ogni avvio, e la porta fa parte dell'origine: al secondo
 * avvio il browser non riconoscerebbe più né le preferenze, né gli spot messi
 * da parte, né le tessere scaricate. Qui l'indirizzo è sempre lo stesso.
 *
 * `appassets.androidplatform.net` è il nome che Android riserva proprio a
 * questo: non esiste in rete, non si risolve, e nessuna richiesta esce
 * davvero dal telefono. In più è `https`, quindi per il browser è un'origine
 * sicura — la condizione perché il service worker possa registrarsi.
 */
final class Risorse {

  private static final String DOMINIO = "appassets.androidplatform.net";

  /** Da qui parte l'app. */
  static final String CASA = "https://" + DOMINIO + "/index.html";

  /** La cartella dentro `assets/` dove sta l'app. */
  private static final String RADICE = "guscio";

  /** I tipi che un browser sbaglia da solo se nessuno glieli dice. */
  private static final Map<String, String> TIPI = new HashMap<String, String>();

  static {
    TIPI.put("html", "text/html");
    TIPI.put("js", "text/javascript");
    TIPI.put("mjs", "text/javascript");
    TIPI.put("css", "text/css");
    TIPI.put("json", "application/json");
    TIPI.put("webmanifest", "application/manifest+json");
    TIPI.put("svg", "image/svg+xml");
    TIPI.put("png", "image/png");
    TIPI.put("jpg", "image/jpeg");
    TIPI.put("jpeg", "image/jpeg");
    TIPI.put("webp", "image/webp");
    TIPI.put("ico", "image/x-icon");
    TIPI.put("woff2", "font/woff2");
    TIPI.put("mp4", "video/mp4");
    TIPI.put("txt", "text/plain");
  }

  private final AssetManager risorse;

  Risorse(AssetManager risorse) {
    this.risorse = risorse;
  }

  /** Vero se quell'indirizzo è l'app, e non un posto là fuori. */
  static boolean nostro(Uri indirizzo) {
    return DOMINIO.equals(indirizzo.getHost());
  }

  /**
   * La risposta per un indirizzo dell'app, o `null` per lasciar passare tutto
   * il resto — tessere, foto, video — alla rete vera.
   */
  WebResourceResponse per(Uri indirizzo) {
    if (!nostro(indirizzo)) return null;

    String percorso = indirizzo.getPath();
    if (percorso == null || percorso.isEmpty() || percorso.endsWith("/")) {
      percorso = (percorso == null ? "/" : percorso) + "index.html";
    }
    if (percorso.startsWith("/")) percorso = percorso.substring(1);
    // Gli `assets` sono di sola lettura, ma un percorso che risale non porta
    // da nessuna parte lo stesso.
    if (percorso.contains("..")) return vuota(403, "Forbidden");

    String dentro = RADICE + "/" + percorso;
    Map<String, String> testa = intestazioni();

    // Un video non si carica senza sapere quanto è lungo: la tela web chiede
    // un pezzo per volta, e con una risposta che non dice la misura resta
    // ferma sulla locandina. `openFd` la sa, ma solo per i file che il
    // pacchetto non ha compresso — per gli altri si ripiega sullo stream, che
    // è quello che serve a tutto il resto.
    try {
      AssetFileDescriptor descrittore = risorse.openFd(dentro);
      testa.put("Content-Length", String.valueOf(descrittore.getLength()));
      testa.put("Accept-Ranges", "none");
      return new WebResourceResponse(
          tipo(percorso), "utf-8", 200, "OK", testa, descrittore.createInputStream());
    } catch (IOException compresso) {
      // Va bene così: il file c'è, solo non sa dire la propria misura.
    }

    try {
      InputStream file = risorse.open(dentro);
      return new WebResourceResponse(tipo(percorso), "utf-8", 200, "OK", testa, file);
    } catch (IOException mancante) {
      return vuota(404, "Not Found");
    }
  }

  private static Map<String, String> intestazioni() {
    Map<String, String> testa = new HashMap<String, String>();
    // Il service worker può prendersi tutta la radice.
    testa.put("Service-Worker-Allowed", "/");
    // La cache la gestisce il service worker dell'app: quella del browser
    // qui in mezzo servirebbe solo a nascondere un aggiornamento.
    testa.put("Cache-Control", "no-cache");
    return testa;
  }

  private static WebResourceResponse vuota(int codice, String motivo) {
    return new WebResourceResponse(
        "text/plain", "utf-8", codice, motivo, intestazioni(), new ByteArrayInputStream(new byte[0]));
  }

  private static String tipo(String percorso) {
    int punto = percorso.lastIndexOf('.');
    if (punto < 0) return "application/octet-stream";
    String tipo = TIPI.get(percorso.substring(punto + 1).toLowerCase());
    return tipo != null ? tipo : "application/octet-stream";
  }
}

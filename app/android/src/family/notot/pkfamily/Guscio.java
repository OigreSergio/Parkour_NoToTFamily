package family.notot.pkfamily;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Bundle;
import android.view.ViewGroup;
import android.webkit.GeolocationPermissions;
import android.webkit.ServiceWorkerClient;
import android.webkit.ServiceWorkerController;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

/**
 * L'unica schermata: una tela web a tutto schermo con dentro PkFAMILY.
 *
 * L'app non è riscritta in Java. È la stessa che gira nel browser del telefono
 * e sul computer dalla beta: qui i suoi file arrivano da dentro l'APK (vedi
 * {@link Risorse}), a un indirizzo che non cambia mai, così il service worker,
 * IndexedDB e i moduli funzionano come devono.
 *
 * Se quell'indirizzo non si aprisse — non dovrebbe succedere, ma un'app che
 * parte su una pagina bianca non la salva nessuno — si ripiega sulla copia in
 * un file solo, `assets/pkfamily.html`, che da `file://` funziona lo stesso.
 */
public class Guscio extends Activity {

  private static final int CHIESTA_POSIZIONE = 41;
  private static final String RIPIEGO = "file:///android_asset/pkfamily.html";

  private WebView tela;
  private Risorse dentro;
  private boolean ripiegato;

  /** Chi ha chiesto la posizione alla pagina, in attesa della risposta di Android. */
  private String origineInAttesa;
  private GeolocationPermissions.Callback rispostaInAttesa;

  @Override
  protected void onCreate(Bundle stato) {
    super.onCreate(stato);
    dentro = new Risorse(getAssets());

    tela = new WebView(this);
    tela.setLayoutParams(
        new ViewGroup.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

    WebSettings impostazioni = tela.getSettings();
    impostazioni.setJavaScriptEnabled(true);
    impostazioni.setDomStorageEnabled(true);
    impostazioni.setDatabaseEnabled(true);
    impostazioni.setGeolocationEnabled(true);
    impostazioni.setMediaPlaybackRequiresUserGesture(false);
    impostazioni.setSupportZoom(false);
    impostazioni.setBuiltInZoomControls(false);
    // Servono solo al ripiego: la pagina in un file solo ha tutto dentro di sé.
    impostazioni.setAllowFileAccess(true);
    impostazioni.setAllowFileAccessFromFileURLs(true);

    tela.setWebViewClient(
        new WebViewClient() {
          @Override
          public WebResourceResponse shouldInterceptRequest(
              WebView vista, WebResourceRequest richiesta) {
            return dentro.per(richiesta.getUrl());
          }

          @Override
          public boolean shouldOverrideUrlLoading(WebView vista, WebResourceRequest richiesta) {
            return apriFuori(richiesta.getUrl(), richiesta.isForMainFrame());
          }

          @Override
          public void onReceivedError(
              WebView vista,
              WebResourceRequest richiesta,
              android.webkit.WebResourceError errore) {
            if (richiesta.isForMainFrame()) vaiAlRipiego();
          }
        });

    // Le richieste che parte il service worker non passano dal WebViewClient:
    // hanno un cliente tutto loro, e senza questo l'offline non troverebbe i
    // file dell'app da mettere in cache.
    try {
      ServiceWorkerController.getInstance()
          .setServiceWorkerClient(
              new ServiceWorkerClient() {
                @Override
                public WebResourceResponse shouldInterceptRequest(WebResourceRequest richiesta) {
                  return dentro.per(richiesta.getUrl());
                }
              });
    } catch (RuntimeException senzaControllo) {
      // Una tela web senza questo pezzo esiste: l'app funziona lo stesso, è
      // l'offline che non si prepara. Meglio così che non partire affatto.
    }

    tela.setWebChromeClient(
        new WebChromeClient() {
          @Override
          public void onGeolocationPermissionsShowPrompt(
              String origine, GeolocationPermissions.Callback risposta) {
            chiediPosizione(origine, risposta);
          }
        });

    setContentView(tela);

    if (stato != null) {
      // Ricreata dopo che il sistema si era ripreso la memoria: si riprende
      // da dov'era. L'indirizzo dell'app è sempre lo stesso, quindi il
      // percorso salvato vale ancora.
      tela.restoreState(stato);
      return;
    }
    tela.loadUrl(Risorse.CASA);
  }

  /** L'app non si è aperta: si riparte dalla copia in un file solo, una volta sola. */
  private void vaiAlRipiego() {
    if (ripiegato || tela == null) return;
    ripiegato = true;
    tela.loadUrl(RIPIEGO);
  }

  /**
   * La posizione la chiede la pagina, quando la persona tocca «Dove sono».
   * Qui si gira la domanda ad Android: se il permesso c'è già si risponde
   * subito, altrimenti si aspetta la finestra di sistema.
   */
  private void chiediPosizione(String origine, GeolocationPermissions.Callback risposta) {
    if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)
            == PackageManager.PERMISSION_GRANTED
        || checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)
            == PackageManager.PERMISSION_GRANTED) {
      risposta.invoke(origine, true, false);
      return;
    }
    origineInAttesa = origine;
    rispostaInAttesa = risposta;
    requestPermissions(
        new String[] {
          Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION
        },
        CHIESTA_POSIZIONE);
  }

  @Override
  public void onRequestPermissionsResult(int codice, String[] permessi, int[] esiti) {
    if (codice != CHIESTA_POSIZIONE || rispostaInAttesa == null) {
      super.onRequestPermissionsResult(codice, permessi, esiti);
      return;
    }
    boolean concesso = false;
    for (int esito : esiti) {
      if (esito == PackageManager.PERMISSION_GRANTED) concesso = true;
    }
    // Comunque vada la pagina deve avere una risposta: senza, il bottone
    // «Dove sono» resterebbe a girare per sempre.
    rispostaInAttesa.invoke(origineInAttesa, concesso, false);
    rispostaInAttesa = null;
    origineInAttesa = null;
  }

  /**
   * Una foto su Wikimedia o il video di un tutorial non sono l'app: si aprono
   * nel browser, che ha i suoi comandi, invece di intrappolare la persona in
   * una tela senza barra degli indirizzi.
   */
  private boolean apriFuori(Uri indirizzo, boolean principale) {
    if (!principale) return false;
    if (Risorse.nostro(indirizzo) || "file".equals(indirizzo.getScheme())) return false;
    try {
      startActivity(new Intent(Intent.ACTION_VIEW, indirizzo));
      return true;
    } catch (RuntimeException senzaBrowser) {
      return false; // nessuno sa aprirlo: tanto vale provarci qui dentro
    }
  }

  @Override
  public void onBackPressed() {
    // Dentro l'app «indietro» vuol dire la schermata prima, non uscire.
    if (tela != null && tela.canGoBack()) {
      tela.goBack();
      return;
    }
    super.onBackPressed();
  }

  @Override
  protected void onSaveInstanceState(Bundle stato) {
    super.onSaveInstanceState(stato);
    if (tela != null) tela.saveState(stato);
  }

  @Override
  protected void onDestroy() {
    if (tela != null) {
      tela.destroy();
      tela = null;
    }
    super.onDestroy();
  }
}

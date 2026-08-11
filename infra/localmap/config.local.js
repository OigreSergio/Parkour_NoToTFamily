// Config per far girare la mappa ricamo dal server locale.
// Sostituisci SERVER_IP con l'IP del PC sulla rete locale (es. 192.168.1.10)
// e includi questo file in index.html PRIMA dello script del bundle.
globalThis.__PK_TILES__ = 'http://SERVER_IP:8080/map.json';
globalThis.__PK_GLYPHS__ = 'http://SERVER_IP:8081/fonts/{fontstack}/{range}.pbf';

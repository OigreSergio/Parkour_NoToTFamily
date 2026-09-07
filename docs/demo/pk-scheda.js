/* PkFAMILY — contesto visivo nella scheda spot.
 *
 * Generato da docs/demo/tools/build_pk_scheda.py — NON modificare a mano.
 * Caricato da index.html accanto al bundle Expo (stesso pattern di
 * pk-route.js). Interviene SOLO sulla rotta /spot/{id}: quando la family
 * apre la scheda, in fondo compaiono la miniatura Street View puntata
 * sullo spot come COPERTINA al posto di \u201CAncora nessuna foto\u201D, il
 * panorama 360\u00B0 apribile inline, una foto della zona (con licenza) o una
 * seconda angolazione Street View, la vista aerea, il link a Google Street
 * View e i contenuti Instagram collegati allo spot (post incorporabili,
 * profili, pagina del luogo con le foto geotaggate l\u00EC).
 * Se lo spot ha gi\u00E0 foto proprie nella galleria, la copertina non viene
 * toccata. Nessuna API key: stessi endpoint pubblici della pagina demo.
 *
 * Copre TUTTI gli spot: i 26 della family sono inline (SPOTS), gli altri
 * ~1700 arrivano da pk-scheda-spots.json (scaricato una volta alla prima
 * scheda), e uno spot nato dopo il build viene risolto al volo (Supabase
 * con chiave pubblica + ricerca del panorama dal browser).
 */
(function () {
  'use strict';

  var SPOTS = {"0f9ac7ae-0dd1-4827-84ac-3f1874507b5e":{"name":"EUR Laghetto","lat":41.8305,"lng":12.4703,"city":"Roma","sv":{"pano_id":"TPBKfMbblYg9aX2p7xH_Nw","pano_lat":41.83052208708717,"pano_lng":12.4703204266273,"yaw":214.6,"date":"2024-06","distance_m":3},"sv2":{"pano_id":"T5CotV_FKhGyLn8XuC0BOg","pano_lat":41.83045863838245,"pano_lng":12.47025551338506,"yaw":38.7,"date":null,"distance_m":6},"photo":{"src":"https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Roma_EUR_Laghetto_vista_dal_basso.jpg/960px-Roma_EUR_Laghetto_vista_dal_basso.jpg","page":"https://commons.wikimedia.org/wiki/File:Roma_EUR_Laghetto_vista_dal_basso.jpg","credit":"Wikimedia Commons · CC BY-SA 3.0 IT"},"ig":{"location":{"id":"16408234","slug":"laghetto-delleur","name":"Laghetto dell'Eur"},"posts":[{"url":"https://www.instagram.com/p/DW0dfiuDMIl/","kind":"post","title":"Laghetto dell'Eur - Roma"},{"url":"https://www.instagram.com/p/CcfLRUdtfkI/","kind":"post","title":"📍 Passeggiata del Giappone, Laghetto dell'Eur, Roma"},{"url":"https://www.instagram.com/reel/DH-zTG2NrXi/","kind":"reel","title":"I ciliegi al Laghetto dell'Eur a Roma sono finalmente fioriti"}]}},"c1f8bcc4-e5e7-4ddd-bf8f-d5c080c1f082":{"name":"Villa Borghese — Piazza di Siena","lat":41.9142,"lng":12.4849,"city":"Roma","sv":{"pano_id":"Rx8AqZz-p7uLjUJyZlIpJQ","pano_lat":41.91385317860745,"pano_lng":12.484470822088,"yaw":42.6,"date":"2015-09","distance_m":52},"sv2":{"pano_id":"mijtSXkHn_siG3EUUvwhFw","pano_lat":41.91379446191918,"pano_lng":12.48456321689805,"yaw":31.7,"date":null,"distance_m":53},"photo":{"src":"https://upload.wikimedia.org/wikipedia/commons/thumb/2/28/Plaza_de_Siena%2C_Villa_Borghese%2C_Roma%2C_Italia%2C_2022-09-14%2C_DD_14.jpg/960px-Plaza_de_Siena%2C_Villa_Borghese%2C_Roma%2C_Italia%2C_2022-09-14%2C_DD_14.jpg","page":"https://commons.wikimedia.org/wiki/File:Plaza_de_Siena,_Villa_Borghese,_Roma,_Italia,_2022-09-14,_DD_14.jpg","credit":"Wikimedia Commons · CC BY-SA 4.0"},"ig":{"location":{"id":"214442562","slug":"piazza-di-siena---villa-borghese","name":"Piazza di Siena - Villa Borghese"},"posts":[{"url":"https://www.instagram.com/antoniadellatte/reel/Csv86bKIOcr/","kind":"reel","title":"Piazza di Siena, oggi a Villa Borghese, #roma …"}]}},"8b0b9c9b-a6b8-42ba-8013-3686281d443e":{"name":"Foro Italico — Stadio dei Marmi","lat":41.9317,"lng":12.4547,"city":"Roma","sv":{"pano_id":"cGJf698SxV9_NS00EjjKjg","pano_lat":41.93148089713848,"pano_lng":12.45424538270189,"yaw":57.1,"date":"2017-06","distance_m":45},"sv2":{"pano_id":"kFsenh15kXNLWOPL3qHCAg","pano_lat":41.93135859292831,"pano_lng":12.45434754982032,"yaw":37.5,"date":null,"distance_m":48},"photo":{"src":"https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Stadio_dei_marmi_009.jpg/960px-Stadio_dei_marmi_009.jpg","page":"https://commons.wikimedia.org/wiki/File:Stadio_dei_marmi_009.jpg","credit":"Wikimedia Commons · Pubblico dominio"},"ig":{"location":{"id":"1159732194162988","slug":"stadio-dei-marmi-foro-italico-roma","name":"Stadio dei Marmi - Foro Italico"},"posts":[{"url":"https://www.instagram.com/moreno_maggi_/p/CO3GtXzsI6y/","kind":"post","title":"Statue dello Stadio dei Marmi - Foro Italico Roma"},{"url":"https://www.instagram.com/p/DXrmq4TjLL-/","kind":"post","title":"Roma: lo Stadio dei Marmi avrà nuova pista e sarà aperto …"}]}},"7afa8505-b5b3-4781-8e25-d42897f5353e":{"name":"Garbatella — Scalinate","lat":41.8622,"lng":12.4823,"city":"Roma","sv":{"pano_id":"qNRSxLQakVwGqy2FLcEQSg","pano_lat":41.86216744602794,"pano_lng":12.48233150070373,"yaw":324.2,"date":"2022-02","distance_m":4},"sv2":{"pano_id":"-Ew1rItnCjoX3hyLEZk-1Q","pano_lat":41.86225458982317,"pano_lng":12.48236308582817,"yaw":220.7,"date":null,"distance_m":8},"photo":{"src":"https://live.staticflickr.com/34/72998499_c2311608eb_b.jpg","page":"https://www.flickr.com/photos/93226994@N00/72998499","credit":"antmoose (Flickr) · CC BY 2.0"},"ig":{"location":{"id":"1498530246926745","slug":"garbatella-roma","name":"Garbatella, Roma"}}},"e117b08f-7cd9-4f98-b3b3-983944ab4155":{"name":"MA Spot — Largo Emanuele Ruspoli","lat":41.858017,"lng":12.455528,"city":"Roma","sv":{"pano_id":"qKZ4gqWC8RooDH4PWWAziQ","pano_lat":41.8580151467124,"pano_lng":12.455315342905,"yaw":89.3,"date":"2015-07","distance_m":18},"sv2":{"pano_id":"H1ODSF9-jF8qV5BMxVWY6w","pano_lat":41.85789193263358,"pano_lng":12.45534692052979,"yaw":47.2,"date":null,"distance_m":20},"ig":{"location":{"id":"1028325823","slug":"roma-quartiere-portuense","name":"Roma Quartiere Portuense"}}},"d6668114-4fb1-46a2-b23b-02c3ed2d2d13":{"name":"Spot Metro Colosseo","lat":41.891806,"lng":12.491545,"city":"Roma","sv":{"pano_id":"DtoulutpPZxIRrfX-6A5vw","pano_lat":41.89184691512483,"pano_lng":12.49153162875579,"yaw":166.3,"date":"2018-06","distance_m":5},"sv2":{"pano_id":"hzCHfzFuePfL1dmwKJdzHw","pano_lat":41.89178474052124,"pano_lng":12.49143502828026,"yaw":75.4,"date":null,"distance_m":9},"photo":{"src":"https://upload.wikimedia.org/wikipedia/commons/thumb/7/7f/Colosseo_-_panoramio_%2810%29.jpg/960px-Colosseo_-_panoramio_%2810%29.jpg","page":"https://commons.wikimedia.org/wiki/File:Colosseo_-_panoramio_(10).jpg","credit":"Wikimedia Commons · CC BY 3.0"},"ig":{"location":{"id":"347678956","slug":"colosseo---roma","name":"Colosseo - Roma"}}},"af810dbb-3109-4974-82c7-6cbdd5054efa":{"name":"Parkour Park Municipio Roma III","lat":41.960813,"lng":12.539902,"city":"Roma","sv":{"pano_id":"7ASDd0jbZ1llpPynE7_StA","pano_lat":41.96075536956421,"pano_lng":12.53971779209702,"yaw":67.2,"date":"2026-04","distance_m":17},"sv2":{"pano_id":"6SUpHnRLC3fVD7tUKdJfOw","pano_lat":41.96084161591976,"pano_lng":12.53970116000582,"yaw":100.8,"date":null,"distance_m":17},"ig":{"location":{"id":"272111109","slug":"vigne-nuove-montesacro-porte-di-roma","name":"Vigne Nuove - Montesacro"},"posts":[{"url":"https://www.instagram.com/p/DU_VC2giPeT/","kind":"post","title":"Roma ha il suo Parkour Park. E non è …"},{"url":"https://www.instagram.com/reel/DVjF5rPiBKE/","kind":"reel","title":"Il primo Parkour Park di Roma! Grazie ai ragazzi di …"},{"url":"https://www.instagram.com/reel/DU8KEB2CGLH/","kind":"reel","title":"Il primo Parkour Park di Roma! Grazie ai ragazzi di …"},{"url":"https://www.instagram.com/p/DU797H_DIb6/","kind":"post","title":"#MunicipioIII, inaugurati piazzale Ennio Flaiano, il Parkour Park e l'area ludica"},{"url":"https://www.instagram.com/reel/DU6LPKbjOHg/","kind":"reel","title":"Riqualificazione Piazzale Ennio Flaiano — oggi, insieme al …"}]}},"1aaaa16f-66a6-4888-8fd2-29618bcd7f90":{"name":"Spot EUR","lat":41.829641,"lng":12.466853,"city":"Roma","sv":{"pano_id":"51CGqz-wF7GOkxQc4Herpg","pano_lat":41.82958154467747,"pano_lng":12.46678060936479,"yaw":42.2,"date":"2022-07","distance_m":9},"sv2":{"pano_id":"Xu5ieckQKLNlkI10ZCVlxw","pano_lat":41.82953959440798,"pano_lng":12.46689389790778,"yaw":343.3,"date":null,"distance_m":12},"photo":{"src":"https://upload.wikimedia.org/wikipedia/commons/thumb/b/bd/2024-05-06-Palazzo-dello-Sport-2.jpg/960px-2024-05-06-Palazzo-dello-Sport-2.jpg","page":"https://commons.wikimedia.org/wiki/File:2024-05-06-Palazzo-dello-Sport-2.jpg","credit":"Wikimedia Commons · CC BY-SA 4.0"},"ig":{"location":{"id":"100943021363694","slug":"palazzo-dello-sport-roma","name":"Palazzo dello Sport - Roma"},"accounts":[{"handle":"palazzodellosportroma","name":"Palazzo dello Sport - Roma","why":"pagina ufficiale del palazzetto accanto allo spot"}]}},"3660d036-5be3-4044-b2fc-b6cc35c5a9b6":{"name":"Spot Rooftop Casal Lumbroso","lat":41.862819,"lng":12.363478,"city":"Roma","sv":{"pano_id":"QVW0A2SHgY6KGxagnXYkvQ","pano_lat":41.86339265162889,"pano_lng":12.36283098028132,"yaw":140.0,"date":"2025-07","distance_m":83},"sv2":{"pano_id":"YGRSPqyWPKArCuq9-TusbA","pano_lat":41.86333150602263,"pano_lng":12.36274183125475,"yaw":133.1,"date":null,"distance_m":83},"ig":{"location":{"id":"244493289","slug":"casal-lumbroso---massimina","name":"Casal Lumbroso - Massimina"}}},"a6487801-aa3b-47e1-92b1-7c88069cb08f":{"name":"Spot Pizzeria Massimina","lat":41.877788,"lng":12.349671,"city":"Roma","sv":{"pano_id":"EMjz0OVSkt-f31-1sNp99g","pano_lat":41.87780538429979,"pano_lng":12.34962572178195,"yaw":117.3,"date":"2025-07","distance_m":4},"sv2":{"pano_id":"6uvUPFe-j2gpLYZhl8g2MQ","pano_lat":41.87779985111844,"pano_lng":12.3497485932567,"yaw":258.4,"date":null,"distance_m":7},"ig":{"location":{"id":"693126625","slug":"massimina-casal-lumbroso","name":"Massimina-Casal Lumbroso"}}},"6411a98b-594b-4d5e-8f0f-ba5ec243e6b5":{"name":"Spot Scuola Massimina","lat":41.882734,"lng":12.360117,"city":"Roma","sv":{"pano_id":"lX4dCfIvkq-IE5E7uMjdfw","pano_lat":41.8828742384333,"pano_lng":12.36064265433101,"yaw":250.3,"date":"2025-07","distance_m":46},"sv2":{"pano_id":"7FxCo2Dhf53bnAEm1daW5g","pano_lat":41.88278530433528,"pano_lng":12.36067796366923,"yaw":263.0,"date":null,"distance_m":47},"ig":{"location":{"id":"693126625","slug":"massimina-casal-lumbroso","name":"Massimina-Casal Lumbroso"}}},"58ca88db-1761-4aa5-b34a-48a6968c6176":{"name":"Spot Massimina Parco Nord","lat":41.87995,"lng":12.359791,"city":"Roma","sv":{"pano_id":"7ElPP3PlCeaDw2W-NBogRg","pano_lat":41.8800533139586,"pano_lng":12.36021946753247,"yaw":252.1,"date":"2025-07","distance_m":37},"sv2":{"pano_id":"wsA9WM119W32o_Fs26hIBQ","pano_lat":41.87997295446806,"pano_lng":12.3602527665598,"yaw":266.2,"date":null,"distance_m":38},"ig":{"location":{"id":"693126625","slug":"massimina-casal-lumbroso","name":"Massimina-Casal Lumbroso"}}},"dfb21f27-574e-40da-a767-4a4b6fba767f":{"name":"Spot Massimina Parco Sud","lat":41.869537,"lng":12.356947,"city":"Roma","sv":{"pano_id":"HT_1ExiBdITjyPjRrfCQaw","pano_lat":41.86954065320352,"pano_lng":12.35716220442339,"yaw":268.7,"date":"2025-07","distance_m":18},"sv2":{"pano_id":"UKep72L9OZpu37zFkggcEg","pano_lat":41.86962925965248,"pano_lng":12.35712803234661,"yaw":235.6,"date":null,"distance_m":18},"ig":{"location":{"id":"693126625","slug":"massimina-casal-lumbroso","name":"Massimina-Casal Lumbroso"}}},"9bc3566a-374b-4be8-a7ed-a34beb385024":{"name":"Spot Corviale 1","lat":41.851164,"lng":12.413137,"city":"Roma","sv":{"pano_id":"oxz0piHxD7QaqM6zLgdIMg","pano_lat":41.85100398130709,"pano_lng":12.41367350829766,"yaw":291.8,"date":"2025-10","distance_m":48},"sv2":{"pano_id":"e7l5gUeF3jpydJh7L1xyRQ","pano_lat":41.85109160637583,"pano_lng":12.41371005842785,"yaw":279.6,"date":null,"distance_m":48},"photo":{"src":"https://upload.wikimedia.org/wikipedia/commons/thumb/7/7f/Corviale_%285582072620%29.jpg/960px-Corviale_%285582072620%29.jpg","page":"https://commons.wikimedia.org/wiki/File:Corviale_(5582072620).jpg","credit":"Wikimedia Commons · Pubblico dominio"},"ig":{"location":{"id":"308660553","slug":"corviale---serpentone","name":"Corviale - Serpentone"},"posts":[{"url":"https://www.instagram.com/p/C8NIownItyi/","kind":"post","title":"Il Corviale di Roma Nord #roma #rome #italia …"},{"url":"https://www.instagram.com/p/DKjNYUXPnnp/","kind":"post","title":"Una #piazza pubblica per gli abitanti di Corviale …"}],"accounts":[{"handle":"corvialepark","name":"Corviale Park","why":"il parco del Corviale"}]}},"ab93fa95-6329-43f7-84b2-bd69ca07b57e":{"name":"Spot Corviale 2","lat":41.850893,"lng":12.41161,"city":"Roma","sv":{"pano_id":"o0G1TNJUZ_ZeI94i66c5EA","pano_lat":41.85089248839245,"pano_lng":12.41147125360772,"yaw":89.7,"date":"2022-08","distance_m":11},"sv2":{"pano_id":"EqNq-5HpYUqPYaftuM3uWw","pano_lat":41.85098207007761,"pano_lng":12.41150972667951,"yaw":140.0,"date":null,"distance_m":13},"photo":{"src":"https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/Municipio_XI_%28Roma%29_in_2020.03.jpg/960px-Municipio_XI_%28Roma%29_in_2020.03.jpg","page":"https://commons.wikimedia.org/wiki/File:Municipio_XI_(Roma)_in_2020.03.jpg","credit":"Wikimedia Commons · CC BY-SA 4.0"},"ig":{"location":{"id":"308660553","slug":"corviale---serpentone","name":"Corviale - Serpentone"},"posts":[{"url":"https://www.instagram.com/p/C8NIownItyi/","kind":"post","title":"Il Corviale di Roma Nord #roma #rome #italia …"},{"url":"https://www.instagram.com/p/DKjNYUXPnnp/","kind":"post","title":"Una #piazza pubblica per gli abitanti di Corviale …"}],"accounts":[{"handle":"corvialepark","name":"Corviale Park","why":"il parco del Corviale"}]}},"c9cb7a8e-f7c9-4462-b0a0-81bcb9fbbf6f":{"name":"Spot Corviale 3","lat":41.851311,"lng":12.412888,"city":"Roma","sv":{"pano_id":"SvJ-2_r2bpn8yJS_WuWkjQ","pano_lat":41.85136123714386,"pano_lng":12.41254422002827,"yaw":101.1,"date":"2024-06","distance_m":29},"sv2":{"pano_id":"sEPJP8k7juYvZAxkKyo1PQ","pano_lat":41.85145125950879,"pano_lng":12.41258138187073,"yaw":121.6,"date":null,"distance_m":30},"photo":{"src":"https://upload.wikimedia.org/wikipedia/commons/thumb/e/e2/Municipio_XI_%28Roma%29_in_2020.02.jpg/960px-Municipio_XI_%28Roma%29_in_2020.02.jpg","page":"https://commons.wikimedia.org/wiki/File:Municipio_XI_(Roma)_in_2020.02.jpg","credit":"Wikimedia Commons · CC BY-SA 4.0"},"ig":{"location":{"id":"308660553","slug":"corviale---serpentone","name":"Corviale - Serpentone"},"posts":[{"url":"https://www.instagram.com/p/C8NIownItyi/","kind":"post","title":"Il Corviale di Roma Nord #roma #rome #italia …"},{"url":"https://www.instagram.com/p/DKjNYUXPnnp/","kind":"post","title":"Una #piazza pubblica per gli abitanti di Corviale …"}],"accounts":[{"handle":"corvialepark","name":"Corviale Park","why":"il parco del Corviale"}]}},"1b76da0f-5c17-4c3f-a0db-d780bc708f96":{"name":"Spot Tufello","lat":41.95479,"lng":12.532099,"city":"Roma","sv":{"pano_id":"hJbExIhWQe51VSWJ3syH7A","pano_lat":41.95488971325576,"pano_lng":12.53196268464158,"yaw":134.5,"date":"2026-04","distance_m":16},"sv2":{"pano_id":"_QyJfA9huQ_xXtJVUq5FBA","pano_lat":41.95482077863186,"pano_lng":12.53188460665088,"yaw":100.9,"date":null,"distance_m":18},"ig":{"location":{"id":"390378695","slug":"tufello-roma","name":"Tufello - Roma"},"posts":[{"url":"https://www.instagram.com/p/DMkYCCKtmy7/","kind":"post","title":"Il Tufello è un quartiere dove ogni muro, ogni cortile, ogni …"}]}},"d967cfe9-fddd-4b87-9711-d3a0fedaad73":{"name":"Spot Via Giovanni Prati","lat":41.87381,"lng":12.462786,"city":"Roma","sv":{"pano_id":"YXWICva6q0YqjX8Oh-KVNg","pano_lat":41.87381404656958,"pano_lng":12.46273641352902,"yaw":96.3,"date":"2026-05","distance_m":4},"sv2":{"pano_id":"WrVi8HwmYWQeAucg9Ia73w","pano_lat":41.87372465402817,"pano_lng":12.46276886799984,"yaw":8.5,"date":null,"distance_m":10},"ig":{"location":{"id":"432017819","slug":"monteverde-roma","name":"Monteverde - Roma"}}},"2b1be419-9c83-4244-9e06-9e1213c1aedd":{"name":"Spot Primavalle","lat":41.90608,"lng":12.415025,"city":"Roma","sv":{"pano_id":"2MLVf2fPPWcmCHlWWb7b4A","pano_lat":41.90619794309863,"pano_lng":12.41521894206098,"yaw":230.7,"date":"2025-07","distance_m":21},"sv2":{"pano_id":"qLJLkXQyDDQyogzOOZYOJg","pano_lat":41.90624519657181,"pano_lng":12.41513001390302,"yaw":205.3,"date":null,"distance_m":20},"photo":{"src":"https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Largo_borromeo_primavalle_roma.jpg/960px-Largo_borromeo_primavalle_roma.jpg","page":"https://commons.wikimedia.org/wiki/File:Largo_borromeo_primavalle_roma.jpg","credit":"Wikimedia Commons · CC BY-SA 4.0"},"ig":{"location":{"id":"390145927","slug":"primavalle-roma","name":"Primavalle - Roma"},"accounts":[{"handle":"primavalle.roma","name":"Primavalle","why":"pagina del quartiere"}]}},"f5f25a61-5ba0-4083-87fc-d7c978d054b5":{"name":"Spot Villa Carpegna","lat":41.895616,"lng":12.427432,"city":"Roma","sv":{"pano_id":"8KHkrvhVREoaRoP1A5MjXg","pano_lat":41.8959892363694,"pano_lng":12.42881318094971,"yaw":250.0,"date":"2025-07","distance_m":122},"sv2":{"pano_id":"NWZPhc3KB3dPTJTKqYEekA","pano_lat":41.89607592422767,"pano_lng":12.42876420773253,"yaw":245.1,"date":null,"distance_m":122},"photo":{"src":"https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/Roma_-_Villa_Carpegna_innevata_-_panoramio.jpg/960px-Roma_-_Villa_Carpegna_innevata_-_panoramio.jpg","page":"https://commons.wikimedia.org/wiki/File:Roma_-_Villa_Carpegna_innevata_-_panoramio.jpg","credit":"Wikimedia Commons · CC BY 3.0"},"ig":{"location":{"id":"199935507484907","slug":"piazza-di-villa-carpegna","name":"Piazza di Villa Carpegna"}}},"6d816f11-19d8-4a01-a671-cd071c5450b6":{"name":"Spot Colosseo — Monte Oppio","lat":41.890649,"lng":12.497617,"city":"Roma","sv":{"pano_id":"yujmpiLuOOjWCD-VLTBNVQ","pano_lat":41.89079510080654,"pano_lng":12.49759819745326,"yaw":174.5,"date":"2019-08","distance_m":16},"sv2":{"pano_id":"5-joAYW41U-lRPGzzb27dw","pano_lat":41.89068795583224,"pano_lng":12.49764641278424,"yaw":209.3,"date":null,"distance_m":5},"photo":{"src":"https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Parc_Colle_Oppio_-_Rome_%28IT62%29_-_2021-08-29_-_1.jpg/960px-Parc_Colle_Oppio_-_Rome_%28IT62%29_-_2021-08-29_-_1.jpg","page":"https://commons.wikimedia.org/wiki/File:Parc_Colle_Oppio_-_Rome_(IT62)_-_2021-08-29_-_1.jpg","credit":"Wikimedia Commons · CC BY-SA 4.0"},"ig":{"location":{"id":"251273085","slug":"colle-oppio-roma","name":"Colle Oppio Roma"},"posts":[{"url":"https://www.instagram.com/p/DTWEqPSDPTO/","kind":"post","title":"Parchi di Roma, alcune vedute del colle Oppio …"},{"url":"https://www.instagram.com/p/DUBtOmJEajI/","kind":"post","title":"O Parco Colle Oppio é um dos lugares mais …"}],"accounts":[{"handle":"playground.colosseo","name":"Playground Colosseo (Colle Oppio)","why":"pagina del playground di Via del Monte Oppio"}]}},"85e0af17-1566-4583-b6f6-32f356504f6f":{"name":"Spot NoToT Game","lat":41.865012,"lng":12.44643,"city":"Roma","sv":{"pano_id":"h6Nw_NfQR_-dU9U5ykH7wA","pano_lat":41.86499062261667,"pano_lng":12.44630531946302,"yaw":77.0,"date":"2024-06","distance_m":11},"sv2":{"pano_id":"CbFPxk2sJSbkDUQ4Zr24gw","pano_lat":41.86499942089901,"pano_lng":12.44632106328837,"yaw":81.2,"date":null,"distance_m":9},"ig":{"location":{"id":"432017819","slug":"monteverde-roma","name":"Monteverde - Roma"},"hashtags":["nototfamily"]}},"2fb275b8-0643-43c9-b855-0be9abc46d57":{"name":"Spot Colonne Colosseo","lat":41.890839,"lng":12.494949,"city":"Roma","sv":{"pano_id":"_q4apootAkm9znhoPDkIgQ","pano_lat":41.89065674169301,"pano_lng":12.4949926747537,"yaw":349.9,"date":"2019-08","distance_m":21},"sv2":{"pano_id":"yRv5OANbRsVw7tOaDrL5LQ","pano_lat":41.890666102889,"pano_lng":12.4948209937575,"yaw":28.9,"date":null,"distance_m":22},"photo":{"src":"https://upload.wikimedia.org/wikipedia/commons/thumb/d/d6/Colonne_Tempio_Venere_Colosseo_Roma_09feb08.jpg/960px-Colonne_Tempio_Venere_Colosseo_Roma_09feb08.jpg","page":"https://commons.wikimedia.org/wiki/File:Colonne_Tempio_Venere_Colosseo_Roma_09feb08.jpg","credit":"Wikimedia Commons · CC BY-SA 3.0"},"ig":{"location":{"id":"777288141","slug":"tempio-di-venere-e-roma","name":"Tempio di Venere e Roma"}}},"2f8b8f1d-bb9f-4eca-9bc2-0d10dc5100a2":{"name":"Colle Oppio Park","lat":41.8925,"lng":12.4966,"city":"Roma","sv":{"pano_id":"0EO69nnDIQr50WKa-hKa4g","pano_lat":41.89247800037813,"pano_lng":12.49683541787556,"yaw":277.2,"date":"2016-10","distance_m":20},"sv2":{"pano_id":"H_f7p6RyCUycXVltm6Ll-A","pano_lat":41.89240519691482,"pano_lng":12.49682316724135,"yaw":299.7,"date":null,"distance_m":21},"photo":{"src":"https://upload.wikimedia.org/wikipedia/commons/thumb/b/bb/Parco_Del_Colle_Oppio_-_panoramio.jpg/960px-Parco_Del_Colle_Oppio_-_panoramio.jpg","page":"https://commons.wikimedia.org/wiki/File:Parco_Del_Colle_Oppio_-_panoramio.jpg","credit":"Wikimedia Commons · CC BY 3.0"},"ig":{"location":{"id":"882996","slug":"parco-del-colle-oppio","name":"Parco del Colle Oppio"},"posts":[{"url":"https://www.instagram.com/p/DTWEqPSDPTO/","kind":"post","title":"Parchi di Roma, alcune vedute del colle Oppio …"},{"url":"https://www.instagram.com/p/DUBtOmJEajI/","kind":"post","title":"O Parco Colle Oppio é um dos lugares mais …"}],"accounts":[{"handle":"playground.colosseo","name":"Playground Colosseo (Colle Oppio)","why":"pagina del playground di Via del Monte Oppio"}]}},"spot-metro-cipro":{"name":"Spot verso la metro Cipro","lat":41.907192,"lng":12.449997,"city":"Roma","sv":{"pano_id":"IUziUG_L-jkG8-d1-os-RQ","pano_lat":41.907308,"pano_lng":12.449856,"yaw":137.8,"date":"2024-06","distance_m":17},"sv2":{"pano_id":"r_C_Zfd7-DP1HAkfwxnfmA","pano_lat":41.907183,"pano_lng":12.449725,"yaw":87.4,"date":null,"distance_m":23},"ig":{"location":{"id":"268004176","slug":"metro-cipro","name":"Metro Cipro"}}},"spot-fontanella-trastevere-gianicolo":{"name":"Spot con fontanella - Trastevere/Gianicolo","lat":41.894056,"lng":12.433333,"city":"Roma","sv":{"pano_id":"py8fBA01POKMlyOXmq4gNA","pano_lat":41.893902,"pano_lng":12.433234,"yaw":25.5,"date":"2024-07","distance_m":19},"sv2":{"pano_id":"et4BJ1HvnvGlfCftOfOKUQ","pano_lat":41.893868,"pano_lng":12.43335,"yaw":356.1,"date":null,"distance_m":21},"ig":{"location":{"id":"1029769708","slug":"gianicolo-roma","name":"Gianicolo Roma"}}}};
  var DATA_FILE = 'pk-scheda-spots.json';
  var SUPABASE_URL = 'https://gkdzdtxqkftebrxhgway.supabase.co';
  var SUPABASE_KEY = 'sb_publishable_Xi0aGU8lnV182kEKpsmU3w__uAkFVXg';
  var SCRIPT_BASE = (function () {
    var s = document.currentScript;
    var src = s && s.src ? s.src : '';
    return src ? src.slice(0, src.lastIndexOf('/') + 1) : './';
  })();

  var MONTHS = ['gen', 'feb', 'mar', 'apr', 'mag', 'giu', 'lug', 'ago', 'set', 'ott', 'nov', 'dic'];
  var current = null; // id spot attualmente iniettato
  var COVER_TRIES = 20;   // ~14 s di ricerca del placeholder, poi stop
  var INJECT_TRIES = 8;   // ~5.6 s per l'aggancio inline prima del fallback
  var FALLBACK_TRIES = 4; // ulteriori tentativi col pannello flottante
  var attempts = { cover: 0, inject: 0 };
  var extra = null;       // tutti gli spot fissi, da pk-scheda-spots.json
  var extraState = 0;     // 0 da caricare \u00B7 1 in corso \u00B7 2 pronto \u00B7 3 fallito
  var runtime = {};       // id \u2192 spot risolto al volo (false = in corso, null = impossibile)
  var jsonpN = 0;

  function svThumb(sv) {
    return 'https://streetviewpixels-pa.googleapis.com/v1/thumbnail' +
      '?panoid=' + encodeURIComponent(sv.pano_id) + '&cb_client=maps_sv.tactile.gps' +
      '&w=640&h=360&yaw=' + sv.yaw + '&pitch=0&thumbfov=100';
  }
  function svEmbed(sv) {
    return 'https://www.google.com/maps/embed?pb=' +
      '!4v1!6m8!1m7!1s' + sv.pano_id + '!2m2!1d' + sv.pano_lat + '!2d' + sv.pano_lng +
      '!3f' + sv.yaw + '!4f0!5f0.7820865974627469';
  }
  function svOpen(spot) {
    // con un panorama noto apre proprio quello; altrimenti Street View
    // scelto da Google sul punto dello spot
    var u = 'https://www.google.com/maps/@?api=1&map_action=pano' +
      '&viewpoint=' + spot.lat + ',' + spot.lng;
    if (spot.sv) u += '&pano=' + encodeURIComponent(spot.sv.pano_id) + '&heading=' + spot.sv.yaw;
    return u;
  }
  function aerial(spot) {
    var dlng = 0.0015, dlat = 0.0006;
    return 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export' +
      '?bbox=' + (spot.lng - dlng) + ',' + (spot.lat - dlat) + ',' +
      (spot.lng + dlng) + ',' + (spot.lat + dlat) +
      '&bboxSR=4326&size=640,360&imageSR=3857&format=jpg&f=image';
  }
  function svDate(sv) {
    if (!sv.date) return '';
    var p = sv.date.split('-');
    return MONTHS[parseInt(p[1], 10) - 1] + ' ' + p[0];
  }

  // --- geometria (stesse formule di fetch_streetview.py) -------------------
  function bearing(lat1, lng1, lat2, lng2) {
    var rad = Math.PI / 180, p1 = lat1 * rad, p2 = lat2 * rad, dl = (lng2 - lng1) * rad;
    var y = Math.sin(dl) * Math.cos(p2);
    var x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl);
    return (Math.atan2(y, x) / rad + 360) % 360;
  }
  function distM(lat1, lng1, lat2, lng2) {
    var rad = Math.PI / 180, R = 6371000;
    var dp = (lat2 - lat1) * rad, dl = (lng2 - lng1) * rad;
    var a = Math.sin(dp / 2) * Math.sin(dp / 2) +
      Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dl / 2) * Math.sin(dl / 2);
    return 2 * R * Math.asin(Math.sqrt(a));
  }

  // --- dati: file per tutti gli spot fissi + fallback al volo --------------
  function loadExtra() {
    if (extraState) return;
    extraState = 1;
    fetch(SCRIPT_BASE + DATA_FILE)
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (j) { extra = (j && j.spots) || {}; extraState = 2; })
      .catch(function () { extraState = 3; });
  }

  function jsonp(url) {
    // l'endpoint di ricerca panorami risponde solo in JSONP: tag <script>
    // con callback univoca, timeout di sicurezza, niente residui nel DOM
    return new Promise(function (resolve, reject) {
      var name = '__pkSv' + (++jsonpN);
      var s = document.createElement('script');
      var done = false;
      var timer = setTimeout(function () { finish(); reject(new Error('timeout')); }, 8000);
      function finish() {
        if (done) return;
        done = true;
        clearTimeout(timer);
        window[name] = function () {}; // se arriva tardi non deve rompere nulla
        if (s.parentNode) s.parentNode.removeChild(s);
      }
      window[name] = function (data) { finish(); resolve(data); };
      s.onerror = function () { finish(); reject(new Error('script')); };
      s.src = url + '&callback=' + name;
      document.head.appendChild(s);
    });
  }

  var SV_SEARCH = 'https://maps.googleapis.com/maps/api/js/GeoPhotoService.SingleImageSearch' +
    '?pb=!1m5!1sapiv3!5sUS!11m2!1m1!1b0!2m4!1m2!3d{lat}!4d{lng}!2d{r}' +
    '!3m10!2m2!1sen!2sUS!9m1!1e2!11m4!1m3!1e2!2b1!3e2!4m10!1e1!1e2!1e3!1e4!1e8!1e6!5m1!1e2!6m1!1e2';

  function mkSv(id, plat, plng, date, lat, lng) {
    return {
      pano_id: id, pano_lat: plat, pano_lng: plng,
      yaw: Math.round(bearing(plat, plng, lat, lng) * 10) / 10,
      date: date, distance_m: Math.round(distM(plat, plng, lat, lng))
    };
  }

  function parsePanos(data, lat, lng) {
    // stesso parsing di fetch_streetview.py, sulla forma serializzata
    var blob = JSON.stringify(data);
    var pano = /\[2,"([A-Za-z0-9_-]{20,24})"\]/.exec(blob);
    var coords = /\[null,null,(-?\d{1,2}\.\d+),(-?\d{1,3}\.\d+)\]/.exec(blob);
    if (!pano || !coords) return null;
    var dates = blob.match(/\[(20\d\d),(\d{1,2})\]/g), date = null;
    if (dates) {
      var d = /\[(20\d\d),(\d{1,2})\]/.exec(dates[dates.length - 1]);
      date = d[1] + '-' + (d[2].length < 2 ? '0' + d[2] : d[2]);
    }
    var plat = parseFloat(coords[1]), plng = parseFloat(coords[2]);
    var sv = mkSv(pano[1], plat, plng, date, lat, lng);
    var sv2 = null, best = Infinity, m;
    var re = /\[\[2,"([A-Za-z0-9_-]{20,24})"\],null,\[\[null,null,(-?\d{1,2}\.\d+),(-?\d{1,3}\.\d+)\]/g;
    while ((m = re.exec(blob))) {
      var alat = parseFloat(m[2]), alng = parseFloat(m[3]);
      if (m[1] === pano[1] || distM(plat, plng, alat, alng) < 8) continue; // stessa inquadratura
      var d2 = distM(alat, alng, lat, lng);
      if (d2 < best) { best = d2; sv2 = mkSv(m[1], alat, alng, null, lat, lng); }
    }
    return { sv: sv, sv2: sv2 };
  }

  function findPano(lat, lng) {
    var radii = [50, 120, 300, 600], i = 0;
    function next() {
      if (i >= radii.length) return Promise.resolve(null);
      var url = SV_SEARCH.replace('{lat}', lat).replace('{lng}', lng).replace('{r}', radii[i++]);
      return jsonp(url).then(function (data) { return parsePanos(data, lat, lng) || next(); });
    }
    return next();
  }

  function fetchSpotFromDb(id) {
    if (!SUPABASE_URL || !/^[0-9a-f-]{36}$/.test(id)) return Promise.resolve(null);
    return fetch(SUPABASE_URL + '/rest/v1/spots?select=id,name,lat,lng&id=eq.' + encodeURIComponent(id),
      { headers: { apikey: SUPABASE_KEY, Authorization: 'Bearer ' + SUPABASE_KEY } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (rows) { return rows && rows[0] ? rows[0] : null; });
  }

  function resolveRuntime(id) {
    runtime[id] = false; // in corso
    fetchSpotFromDb(id).then(function (row) {
      var lat = row && Number(row.lat), lng = row && Number(row.lng);
      if (!row || !isFinite(lat) || !isFinite(lng)) { runtime[id] = null; return; }
      var spot = { name: row.name || 'Spot', lat: lat, lng: lng, city: null,
        sv: null, sv2: null, photo: null, ig: null };
      return findPano(lat, lng).catch(function () { return null; }).then(function (p) {
        if (p) { spot.sv = p.sv; spot.sv2 = p.sv2; }
        runtime[id] = spot;
      });
    }).catch(function () { runtime[id] = null; });
  }

  function spotFor(id) {
    if (SPOTS[id]) return SPOTS[id];
    if (extraState === 2 && extra[id]) return extra[id];
    if (runtime[id]) return runtime[id];
    if (extraState === 0) loadExtra();
    if (extraState >= 2 && runtime[id] === undefined) resolveRuntime(id);
    return null; // dati in arrivo: si riprova al prossimo tick
  }

  // --- DOM ------------------------------------------------------------------
  function el(tag, css, text) {
    var e = document.createElement(tag);
    if (css) e.style.cssText = css;
    if (text) e.textContent = text;
    return e;
  }

  function media(src, tagText, tagHref) {
    var wrap = el('div', 'position:relative;border-radius:12px;overflow:hidden;background:#222;margin:0 0 10px');
    var img = el('img', 'width:100%;aspect-ratio:16/9;object-fit:cover;display:block');
    img.loading = 'lazy';
    img.src = src;
    img.onerror = function () { wrap.remove(); };
    wrap.appendChild(img);
    var tag;
    if (tagHref) {
      tag = el('a', '', tagText);
      tag.href = tagHref;
      tag.target = '_blank';
      tag.rel = 'noopener';
    } else {
      tag = el('span', '', tagText);
    }
    tag.style.cssText += 'position:absolute;left:8px;bottom:8px;background:rgba(0,0,0,.62);' +
      'color:#fff;font:11px system-ui,sans-serif;padding:3px 8px;border-radius:6px;text-decoration:none';
    wrap.appendChild(tag);
    return wrap;
  }

  function btn(label, primary) {
    return el('button',
      'flex:1;min-width:120px;padding:10px 8px;border:0;border-radius:10px;cursor:pointer;' +
      'font:600 13px system-ui,sans-serif;' +
      (primary ? 'background:#ffd166;color:#1a1a1a' : 'background:#333;color:#eee'), label);
  }

  // --- Instagram ------------------------------------------------------------
  function igQuery(spot) {
    // "Spot Tor Tre Teste 2" \u2192 "Tor Tre Teste parkour"; la citt\u00E0 si aggiunge
    // solo se non \u00E8 gi\u00E0 nel nome
    var base = spot.name.replace(/^Spot /, '').replace(/\s+\d+$/, '');
    var city = spot.city || '';
    if (city && base.toLowerCase().indexOf(city.toLowerCase()) === -1) base += ' ' + city;
    return base + ' parkour';
  }
  function igLink(spot) {
    // hashtag della family > pagina del luogo (post geotaggati l\u00EC) > ricerca
    var ig = spot.ig;
    if (ig && ig.hashtags && ig.hashtags.length) {
      return 'https://www.instagram.com/explore/tags/' + encodeURIComponent(ig.hashtags[0]) + '/';
    }
    if (ig && ig.location && ig.location.id) {
      return 'https://www.instagram.com/explore/locations/' + ig.location.id + '/' +
        (ig.location.slug ? ig.location.slug + '/' : '');
    }
    return 'https://www.instagram.com/explore/search/keyword/?q=' + encodeURIComponent(igQuery(spot));
  }
  function igEmbedUrl(url) {
    // https://www.instagram.com/[utente/](p|reel)/CODICE/ \u2192 .../CODICE/embed/captioned/
    var m = /instagram\.com\/(?:[^\/]+\/)?(p|reel|tv)\/([A-Za-z0-9_-]+)/.exec(url);
    return m ? 'https://www.instagram.com/' + m[1] + '/' + m[2] + '/embed/captioned/' : url;
  }
  function igPost(p) {
    var card = el('div', 'background:#262628;border-radius:10px;padding:8px 10px;margin:0 0 8px');
    var head = el('div', 'display:flex;align-items:center;gap:8px');
    head.appendChild(el('div', 'flex:1;font:13px/1.3 system-ui,sans-serif;color:#ddd',
      (p.kind === 'reel' ? '\uD83C\uDFAC ' : '\uD83D\uDCF7 ') + (p.title || 'Post Instagram')));
    var open = el('a', 'color:#ffd166;font:600 12px system-ui,sans-serif;text-decoration:none;white-space:nowrap',
      'Apri \u2197');
    open.href = p.url;
    open.target = '_blank';
    open.rel = 'noopener';
    head.appendChild(open);
    card.appendChild(head);
    // il post vero e proprio si carica solo su richiesta (iframe ufficiale
    // di Instagram, pesante): chi vuole dare un'occhiata lo apre qui dentro
    var holder = el('div', 'display:none;margin-top:8px;border-radius:8px;overflow:hidden;background:#fff');
    var show = el('button',
      'margin-top:6px;padding:7px 10px;border:0;border-radius:8px;cursor:pointer;' +
      'background:#333;color:#eee;font:600 12px system-ui,sans-serif', '\u25B6 Mostra il post qui');
    show.onclick = function () {
      if (!holder.firstChild) {
        var f = document.createElement('iframe');
        f.src = igEmbedUrl(p.url);
        f.style.cssText = 'width:100%;height:560px;border:0;display:block';
        f.setAttribute('scrolling', 'no');
        f.setAttribute('allowtransparency', 'true');
        holder.appendChild(f);
      }
      var shown = holder.style.display !== 'none';
      holder.style.display = shown ? 'none' : 'block';
      show.textContent = shown ? '\u25B6 Mostra il post qui' : '\u2715 Nascondi il post';
    };
    card.appendChild(show);
    card.appendChild(holder);
    return card;
  }
  function igBlock(spot) {
    var ig = spot.ig;
    var posts = (ig && ig.posts) || [], accounts = (ig && ig.accounts) || [];
    if (!posts.length && !accounts.length) return null;
    var wrap = el('div', 'margin-top:12px;padding-top:10px;border-top:1px solid #333');
    wrap.appendChild(el('div', 'font:700 13px system-ui,sans-serif;margin-bottom:8px',
      '\uD83D\uDCF7 Dalla community su Instagram'));
    posts.forEach(function (p) { wrap.appendChild(igPost(p)); });
    if (accounts.length) {
      var row = el('div', 'display:flex;gap:6px;flex-wrap:wrap;margin-top:2px');
      accounts.forEach(function (a) {
        var chip = el('a', 'background:#333;color:#eee;font:600 12px system-ui,sans-serif;' +
          'padding:6px 10px;border-radius:999px;text-decoration:none', '@' + a.handle);
        chip.href = 'https://www.instagram.com/' + encodeURIComponent(a.handle) + '/';
        chip.target = '_blank';
        chip.rel = 'noopener';
        if (a.name) chip.title = a.name + (a.why ? ' \u2014 ' + a.why : '');
        row.appendChild(chip);
      });
      wrap.appendChild(row);
    }
    return wrap;
  }
  // altezza reale dei post incorporati (protocollo MEASURE di embed.js)
  window.addEventListener('message', function (e) {
    if (e.origin !== 'https://www.instagram.com') return;
    var d = e.data;
    try { if (typeof d === 'string') d = JSON.parse(d); } catch (err) { return; }
    if (!d || d.type !== 'MEASURE' || !d.details || !d.details.height) return;
    var frames = document.querySelectorAll('#pk-scheda-context iframe');
    for (var i = 0; i < frames.length; i++) {
      if (frames[i].contentWindow === e.source) frames[i].style.height = d.details.height + 'px';
    }
  });

  // --- la sezione ------------------------------------------------------------
  function buildSection(spot) {
    var box = el('div',
      'margin:14px 16px calc(28px + env(safe-area-inset-bottom));padding:14px;border-radius:14px;' +
      'background:#1c1c1e;color:#eee;font:14px system-ui,sans-serif;' +
      'box-shadow:0 2px 10px rgba(0,0,0,.35)');
    box.id = 'pk-scheda-context';

    box.appendChild(el('div', 'font:800 15px system-ui,sans-serif;margin-bottom:10px',
      '\uD83D\uDCF8 Contesto visivo'));

    // La miniatura Street View fa da copertina in testa alla scheda (vedi
    // ensureCover): qui le altre foto del posto \u2014 quella trovata online se
    // esiste, altrimenti una seconda Street View da un'angolazione diversa \u2014
    // pi\u00F9 la vista aerea.
    if (spot.photo) {
      box.appendChild(media(spot.photo.src, 'Foto: ' + spot.photo.credit, spot.photo.page));
    } else if (spot.sv2) {
      box.appendChild(media(svThumb(spot.sv2),
        'Street View \u00B7 altra angolazione \u00B7 ~' + spot.sv2.distance_m + ' m dallo spot'));
    } else if (spot.sv) {
      box.appendChild(media(svThumb(spot.sv),
        'Street View \u00B7 ' + svDate(spot.sv) + ' \u00B7 ~' + spot.sv.distance_m + ' m dallo spot'));
    }
    box.appendChild(media(aerial(spot), 'Vista aerea \u00B7 \u00A9 Esri, Maxar'));

    var row = el('div', 'display:flex;gap:8px;flex-wrap:wrap');
    if (spot.sv) {
      var pano = el('div', 'display:none;margin-top:10px;border-radius:12px;overflow:hidden');
      var b360 = btn('\uD83C\uDF10 Esplora a 360\u00B0', true);
      b360.onclick = function () {
        if (!pano.firstChild) {
          var f = document.createElement('iframe');
          f.src = svEmbed(spot.sv);
          f.style.cssText = 'width:100%;height:300px;border:0;display:block';
          f.allowFullscreen = true;
          pano.appendChild(f);
        }
        var open = pano.style.display !== 'none';
        pano.style.display = open ? 'none' : 'block';
        b360.textContent = open ? '\uD83C\uDF10 Esplora a 360\u00B0' : '\u2715 Chiudi il 360\u00B0';
      };
      row.appendChild(b360);
    }
    var bOpen = btn('\uD83D\uDEB6 Apri in Street View', !spot.sv);
    bOpen.onclick = function () { window.open(svOpen(spot), '_blank'); };
    row.appendChild(bOpen);
    box.appendChild(row);
    if (spot.sv) box.appendChild(pano);

    // Contenuti della community: "Su Instagram" apre la pagina del luogo
    // (le foto geotaggate proprio l\u00EC) quando la conosciamo, altrimenti la
    // ricerca gi\u00E0 compilata per QUESTO spot; i video restano su YouTube.
    var row2 = el('div', 'display:flex;gap:8px;flex-wrap:wrap;margin-top:8px');
    var bIg = btn('\uD83D\uDCF7 Su Instagram', false);
    bIg.title = spot.ig && spot.ig.hashtags && spot.ig.hashtags.length ? '#' + spot.ig.hashtags[0] :
      spot.ig && spot.ig.location ? 'Foto geotaggate: ' + spot.ig.location.name : 'Cerca lo spot su Instagram';
    bIg.onclick = function () { window.open(igLink(spot), '_blank'); };
    var bYt = btn('\uD83C\uDFAC Video community', false);
    bYt.onclick = function () {
      window.open('https://www.youtube.com/results?search_query=' +
        encodeURIComponent(igQuery(spot)), '_blank');
    };
    row2.appendChild(bIg);
    row2.appendChild(bYt);
    box.appendChild(row2);

    var ig = igBlock(spot);
    if (ig) box.appendChild(ig);

    box.appendChild(el('div', 'color:#777;font-size:10px;margin-top:10px',
      'Immagini \u00A9 Google Street View \u00B7 foto Wikimedia/Flickr con licenza \u00B7 aeree \u00A9 Esri' +
      (ig ? ' \u00B7 post Instagram \u00A9 dei rispettivi autori' : '')));
    return box;
  }

  function ensureCover(spot) {
    // Copertina: se la galleria nativa \u00E8 vuota (placeholder \u201CAncora
    // nessuna foto\u201D), la prima immagine \u2014 la Street View puntata sullo
    // spot \u2014 prende il suo posto. Con foto vere gi\u00E0 presenti non tocca nulla.
    // Le scansioni del DOM sono LIMITATE (attempts): senza placeholder \u2014
    // galleria piena o scheda lenta \u2014 dopo un po' si smette, niente lavoro
    // inutile a ogni tick su telefoni lenti.
    if (!spot.sv) return;
    if (attempts.cover >= COVER_TRIES) return;
    if (document.getElementById('pk-scheda-cover')) return;
    attempts.cover++;
    var root = document.getElementById('root');
    if (!root) return;
    var nodes = root.querySelectorAll('div,span');
    var textEl = null;
    for (var i = 0; i < nodes.length; i++) {
      if (nodes[i].children.length === 0 &&
          nodes[i].textContent.trim() === 'Ancora nessuna foto') { textEl = nodes[i]; break; }
    }
    if (!textEl) return;
    var boxEl = textEl.parentElement; // il placeholder con emoji + testo
    if (!boxEl) return;
    boxEl.style.position = 'relative';
    var img = el('img', 'position:absolute;inset:0;width:100%;height:100%;' +
      'object-fit:cover;display:block;z-index:1');
    img.id = 'pk-scheda-cover';
    img.alt = 'Street View: ' + spot.name;
    img.src = svThumb(spot.sv);
    img.onerror = function () { img.remove(); };
    var tag = el('span',
      'position:absolute;left:10px;bottom:10px;z-index:2;background:rgba(0,0,0,.62);' +
      'color:#fff;font:11px system-ui,sans-serif;padding:3px 8px;border-radius:6px',
      'Street View \u00B7 ' + svDate(spot.sv) + ' \u00B7 ~' + spot.sv.distance_m + ' m dallo spot');
    tag.id = 'pk-scheda-cover-tag';
    boxEl.appendChild(img);
    boxEl.appendChild(tag);
  }

  function findScrollHost(name) {
    // La scheda \u00E8 una ScrollView (div con overflow-y auto) che contiene
    // il nome dello spot: agganciamo quella, in fondo al contenuto.
    var root = document.getElementById('root');
    if (!root) return null;
    var divs = root.querySelectorAll('div');
    var best = null;
    for (var i = 0; i < divs.length; i++) {
      var s = getComputedStyle(divs[i]);
      if (s.overflowY !== 'auto' && s.overflowY !== 'scroll') continue;
      if (name && divs[i].textContent.indexOf(name) === -1) continue;
      best = divs[i];
    }
    return best;
  }

  function inject(spot) {
    if (document.getElementById('pk-scheda-context')) return true;
    if (attempts.inject >= INJECT_TRIES + FALLBACK_TRIES) return true; // basta
    attempts.inject++;
    var host = findScrollHost(spot.name) || findScrollHost(null);
    if (!host && attempts.inject <= INJECT_TRIES) {
      // scheda non ancora montata (dispositivo lento): riprova al prossimo
      // tick invece di ripiegare subito sul pannello flottante
      return false;
    }
    var section = buildSection(spot);
    if (host) {
      (host.firstElementChild || host).appendChild(section);
    } else {
      // fallback dopo INJECT_TRIES tentativi: pannello fisso sopra la tab bar
      section.style.cssText += ';position:fixed;left:10px;right:10px;' +
        'bottom:calc(84px + env(safe-area-inset-bottom));z-index:9999;max-height:55vh;overflow:auto';
      document.body.appendChild(section);
    }
    return true;
  }

  function currentSpotId() {
    var m = location.pathname.match(/\/spot\/([^\/?#]+)/);
    return m ? decodeURIComponent(m[1]) : null;
  }

  function removeInjected() {
    ['pk-scheda-context', 'pk-scheda-cover', 'pk-scheda-cover-tag'].forEach(function (id) {
      var n = document.getElementById(id);
      if (n) n.remove();
    });
  }

  function tick() {
    if (document.hidden) return; // tab in background: zero lavoro
    var id = currentSpotId();
    if (!id) {
      current = null;
      removeInjected();
      return;
    }
    if (id !== current) {
      removeInjected(); // cambiato spot: via i pezzi vecchi
      attempts = { cover: 0, inject: 0 };
    }
    current = id;
    var spot = spotFor(id);
    if (!spot) return; // dati non ancora disponibili (o spot sconosciuto)
    ensureCover(spot); // copertina: pu\u00F2 comparire dopo il caricamento dati
    inject(spot); // se la scheda non \u00E8 ancora montata, riprova il polling
  }

  // route-change: pushState/replaceState + popstate + polling di sicurezza
  ['pushState', 'replaceState'].forEach(function (fn) {
    var orig = history[fn];
    history[fn] = function () {
      var r = orig.apply(this, arguments);
      setTimeout(tick, 120);
      return r;
    };
  });
  window.addEventListener('popstate', function () { setTimeout(tick, 120); });
  setInterval(tick, 700);
})();

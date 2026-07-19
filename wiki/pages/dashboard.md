# Dashboard Streamlit

**Sorgenti**: `dashboard/Home.py`, `dashboard/pages/*.py`, `dashboard/components/*.py`,
`config.yaml` (sezione `dashboard`)

**Stato**: implementata ed eseguita su dati reali, avviabile con
`streamlit run dashboard/Home.py` su `http://localhost:8501`.

## Cronologia in breve

- **2026-07-15** — implementata ed eseguita per la prima volta, su 8 comuni
  (75.976 righe, 51 ondate). Estesa lo stesso giorno a 44 comuni (417.868
  righe, 145 ondate — vedi [ETL](etl-pipeline.md)), poi **ampliata
  sostanzialmente** nel contenuto delle 3 pagine di analisi (vedi
  "Contenuto delle pagine" sotto) su richiesta esplicita dell'utente.
  Filtri spostati da sidebar globale a widget inline per pagina (vedi
  sotto). Rinominata da `app.py` a `Home.py` (vedi sotto). Verificata
  senza browser via `streamlit.testing.v1.AppTest` (vedi sotto), poi
  avviata live.
- **2026-07-17** — copertura estesa da 44 a **63 comuni**, dati portati
  **fino ad oggi** (non più fermi al 31/12/2025) — vedi
  [Fonti Dati](data-sources.md) e [ETL](etl-pipeline.md) per la scoperta
  del limite giornaliero di Open-Meteo. Due bug reali corretti grazie
  all'arrivo di dati 2026 (vedi sotto). Restyling completo dell'identità
  visiva (vedi sotto).

Tutti i riferimenti a "44 comuni" nel resto di questa pagina descrivono lo
stato al 2026-07-15 e sono stati aggiornati dove riguardano il
comportamento attuale della dashboard; le narrazioni storiche di sessioni
precedenti restano invariate (coerente con la natura non-riscritta del log).

**Due bug trovati grazie ai dati 2026** (limiti fissi scritti quando "andava
bene così", mai più rivisitati):
- Lo slider anni (`components/filters.py`) aveva `YEAR_MIN`/`YEAR_MAX`
  fissi a `2000, 2025` nel codice — reso dinamico dalla data reale in
  `temperature`, altrimenti il 2026 non sarebbe mai stato selezionabile.
- `frequency_by_year()` (`src/analysis/heatwave_stats.py`) scartava in
  silenzio le ondate 2026 dal grafico, per lo stesso motivo (reindex con
  anno finale fisso).

## Struttura reale

```
dashboard/
├── Home.py                         # entry point = pagina Home (overview, KPI, card di navigazione)
├── pages/
│   ├── 02_analisi_temporale.py     # trend, anomalie, stagionalità, boxplot per quinquennio, STL
│   ├── 03_analisi_spaziale.py      # coropletiche per provincia, trend per comune, fasce altitudinali, uso del suolo, popolazione, cluster, Moran's I
│   ├── 04_ondate_di_calore.py      # frequenza/intensità/cumulato, mappa concentrazione, heatmap calendario
│   └── 05_download_dati.py         # export CSV (dati puliti + risultati di analisi)
└── components/
    ├── __init__.py                 # bootstrap sys.path (vedi bug sotto)
    ├── constants.py                # palette colori, soglie fasce altitudinali, capoluoghi, riferimenti letteratura, etichette Mann-Kendall (2026-07-15); token identità "calore" THEME_*/FONT_*/MAP_TILES (2026-07-17)
    ├── data_source.py              # selettore fonte Open-Meteo/ARPA/Confronto, riusabile tra pagine — nuovo 2026-07-18
    ├── filters.py                  # filtri anni/provincia, inline per pagina (non più sidebar dal 2026-07-15)
    ├── heatwave_definitions.py     # definizione alternativa (percentile) di ondata di calore + identify_heatwaves_events() (equivalente Python multi-comune della soglia fissa, per ARPA) (2026-07-15, esteso 2026-07-18)
    ├── styling.py                  # CSS condiviso + componenti HTML (hero/card/numeri chiave), iniettato in ogni pagina (2026-07-15, ampliato 2026-07-17)
    ├── charts.py                   # tema condiviso per i grafici Plotly (sfondo trasparente) — nuovo 2026-07-17
    ├── queries.py                  # accesso dati (DB + CSV di output), cache_data
    └── maps.py                     # conversione WKT → GeoJSON per folium

**`06_validazione_dati.py` — rimossa il 2026-07-18 (sera)**: esisteva come
pagina dedicata dal mattino dello stesso giorno. Con l'introduzione del
selettore fonte (vedi sotto), il suo contenuto è stato interamente
redistribuito: mappa bias e confronto ondate/trend sintetico dentro
Ondate di Calore/Analisi Temporale (modalità Confronto), il resto
(scatter bias/elevazione, istogramma, tabelle, metodologia) dentro
Analisi Spaziale → tab Dettaglio tecnico → sezione "Validazione ARPA —
dettaglio" (solo in modalità Confronto). Nessun contenuto perso, nessuna
pagina orfana: la cronologia di quando esisteva resta più sotto invariata
(natura non-riscritta del log), solo l'albero della struttura reale sopra
riflette lo stato attuale.

.streamlit/
└── config.toml                     # tema Streamlit nativo (colori, font, raggio angoli) — 2026-07-15
```

**Scostamenti deliberati dal piano**:
- Niente `pages/01_home.py` separato — `Home.py` stesso è la home page,
  convenzione standard di Streamlit multipage (l'entry point mostra già il
  contenuto della prima pagina).
- **Rinominato `app.py` → `Home.py` il 2026-07-15**, su richiesta esplicita
  dell'utente ("dobbiamo trovare un altro nome per la pagina principale,
  non si può chiamare app"). Rinominato con `git mv` (storia Git
  preservata), aggiornati i riferimenti nei docstring
  (`dashboard/Home.py`, `dashboard/components/__init__.py`) e in questa
  pagina. **Non toccati** `README.md`/`PROJECT_SUMMARY.md`/`docs/*.md`:
  per `CLAUDE.md` sono sorgenti di pianificazione immutabili, quindi
  citano ancora il comando `streamlit run dashboard/app.py` — ormai
  stale, il comando corretto è `streamlit run dashboard/Home.py`.
  Verificato con `AppTest` sul nuovo path (nessuna eccezione) e riavviato
  il server live sulla nuova entry point.

Configurazione da `config.yaml`: titolo (`dashboard.title`) passato a
`st.set_page_config`; porta 8501 passata da riga di comando
(`--server.port 8501`), non c'è un modo diretto per leggerla da
`config.yaml` all'avvio di `streamlit run`.

## Filtri: da sidebar globale a inline per pagina (2026-07-15)

**Prima versione**: una sidebar comune (`render_sidebar_filters()`, slider
anni + multiselect provincia) richiamata in cima a ogni pagina, home
inclusa. L'utente ha fatto notare che sembrava per lo più inutile ("non so
cosa possiamo aggiungere a lato") — su molte pagine i filtri non
aggiungevano valore reale o duplicavano controlli già presenti nel corpo
della pagina.

**Rimossa interamente la sidebar**; `components/filters.py` ora espone due
funzioni pensate per essere richiamate *inline*, solo dove il filtro serve
davvero:

- `render_year_range_filter(key)` — slider anni, con `key` univoca per
  pagina (necessaria perché non c'è più uno stato condiviso globale: ogni
  pagina ha il proprio, Streamlit lo persiste da solo tramite `key` per
  tutta la sessione, senza bisogno di gestire `st.session_state` a mano
  come richiedeva la sidebar condivisa).
- `render_province_filter(key)` — multiselect provincia, stessa logica.
  **Default vuoto** (fix del 2026-07-16, a seguito di un altro feedback
  dell'utente): la primissima versione default va a `all_provinces`,
  riempiendo il riquadro con tutti gli 8 tag già selezionati fin dal primo
  sguardo — "non facilmente capibile", secondo l'utente. Ora il box parte
  vuoto (`default=[]`, con `placeholder="Tutte le province con dati"`) e
  il fallback già esistente nella funzione (`return provinces or
  all_provinces`) fa sì che "nessuna selezione" continui a significare
  "tutti i comuni", senza dover mai spuntare/digitare nulla per lo stato
  di default — un click sul box serve solo se si vuole restringere,
  scegliendo dal menu (mai scrivendo a mano il nome di una provincia).

**Dove sono rimasti i filtri, dove sono stati tolti**:

| Pagina | Filtri | Perché |
|---|---|---|
| Home | Nessuno | Pagina di overview, mostra sempre tutti i comuni |
| Analisi Temporale | Solo intervallo anni | Unico filtro usato davvero (regressione, anomalie, stagioni, boxplot); il filtro provincia restringeva solo il menu comune, beneficio marginale |
| Analisi Spaziale | Anni **e** provincia | Pagina esplicitamente geografica: mappe coropletiche, fasce altitudinali, isola di calore hanno senso ristrette a un sottoinsieme di province |
| Ondate di Calore | Anni **e** provincia | Frequenza/intensità/mappa di concentrazione cambiano davvero in base a periodo e province |
| Download Dati | Nessuno (invariato) | I file scaricabili sono CSV completi, un filtro qui non avrebbe effetto |

**Altre modifiche estetiche dello stesso giro**:
- **Home con card di navigazione**: sostituiti i link testuali con 3
  `st.container(border=True, height=280)` affiancati (uno per pagina di
  analisi), ognuno con titolo, una frase di sintesi e `st.page_link()` per
  la navigazione reale (non solo testo). Altezza **fissa** (2026-07-16):
  senza `height` esplicito ogni card si dimensiona sul proprio contenuto,
  quindi 3 didascalie di lunghezza anche solo leggermente diversa
  producono 3 card di altezza diversa — non risolvibile in modo affidabile
  tarando a mano la lunghezza del testo (il punto di a-capo dipende dalla
  larghezza reale della colonna a schermo, non dal conteggio caratteri).
- **Palette coerente** (`components/constants.py`): scala sequenziale
  `RdYlBu_r` (blu→rosso) per ogni valore assoluto di temperatura in tutte
  le mappe/grafici; scala divergente `RdBu_r` centrata sullo zero solo per
  *variazioni* (trend, anomalie) — le due non vanno mai confuse, dato che
  nella prima il colore è un valore assoluto e nella seconda una velocità
  di cambiamento. Rosso "d'allarme" riservato ad anomalie/eventi critici,
  non usato come colore di sfondo generico.

## Contenuto delle pagine (dati reali)

### Home

Intro in linguaggio semplice, 3 card di navigazione, metriche generali
(righe di temperatura, periodo, comuni con dati reali, ondate identificate)
con didascalie, mappa dei comuni e tabella trend di riscaldamento — nessun
filtro (vedi sopra).

- **Spiegazione "cos'è un'ondata di calore" spostata (2026-07-16)**: era un
  riquadro `st.expander` a sé nella home. Su richiesta dell'utente,
  rimossa da qui — la home è una pagina di overview, non il posto giusto
  per una spiegazione di metodologia specifica — e integrata nel riquadro
  "ℹ️ Come si legge questa pagina" già esistente in
  `04_ondate_di_calore.py`, insieme alla sfumatura che nella home era
  presente ma nella pagina Ondate mancava ("i climatologi usano spesso
  soglie che variano da località a località, non un valore fisso").
- **Mappa colorata per trend, non più tutta rossa (2026-07-16)**: la mappa
  mostrava tutti i comuni con lo stesso rosso fisso (serviva solo a
  localizzarli, non trasmetteva informazione). Su segnalazione dell'utente
  ("perché non dividerla per gravità come le altre?"), ricolorata per
  `lr_slope_per_decade` (stesso `trend_analysis.csv` già usato dalla
  tabella accanto), con la stessa colormap divergente e la stessa legenda
  a 5 fasce (`render_gradient_legend()`) della mappa trend di Analisi
  Spaziale — coerenza visiva tra le due pagine.
- **Estesa a Open-Meteo + ARPA combinati (2026-07-18, sera)**: la Home
  mostrava solo i 177 comuni Open-Meteo, mentre le altre 3 pagine avevano
  già il selettore fonte. L'utente ha chiesto di "sommare" i dati ARPA
  invece di lasciare la Home indietro — non una somma ingenua (177+218
  conterebbe due volte i 51 comuni con entrambe le fonti), ma
  un'**unione**: Open-Meteo dove disponibile, ARPA per i comuni scoperti
  da Open-Meteo, mai le due fonti sullo stesso comune insieme. Home non
  ha (e non ha bisogno di) un selettore a 3 vie come le altre pagine — è
  una vista di sintesi, non di confronto.
  - Nuove funzioni in `queries.py`: `get_arpa_overview_stats()`,
    `get_combined_trend_analysis()` (unisce `trend_analysis.csv` con
    `get_arpa_trend_analysis()` per i soli comuni ARPA-only, colonna
    `source` per distinguerli), `get_combined_municipality_geometries_wkt()`,
    `get_combined_heatwave_count()` (conteggio ondate `heatwave_events`
    più le ondate rilevate al volo su ARPA **solo** per i comuni senza
    Open-Meteo — mai sommando due conteggi sullo stesso comune, che
    sarebbe la stessa ondata reale contata due volte da due metodi
    diversi).
  - Hero, warning di copertura, "Il progetto in numeri", mappa e tabella
    trend tutti aggiornati: **344/1180 comuni** (era 177/1180), riga di
    temperatura = Open-Meteo + ARPA sommate (somma legittima, sono
    osservazioni distinte), tabella trend con nuova colonna "Fonte".
  - Verificato con `AppTest`, nessuna eccezione (18s, più veloce delle
    pagine con selettore perché qui si calcola una sola combinazione, non
    tre).

### Analisi Temporale (`02_analisi_temporale.py`) — ampliata il 2026-07-15

**Tab Panoramica**:
- 4 metriche in alto: pendenza sul periodo selezionato, significatività,
  trend Mann-Kendall di riferimento sull'intero periodo, temperatura media
  dell'ultimo anno.
- Serie annuale max/media/min con **retta di regressione sovrapposta**,
  ricalcolata dal vivo sul periodo scelto con lo slider anni della pagina
  (non il CSV precalcolato, che copre sempre l'intero periodo).
- Grafico delle **anomalie** rispetto a una baseline **fissa** (primo
  decennio disponibile per il comune, non configurabile — vedi sotto).
- Confronto tra le **4 stagioni meteorologiche** (DJF/MAM/JJA/SON) anno per
  anno, con pendenza per stagione, per vedere quale si scalda più in
  fretta.
- **Boxplot per quinquennio** sulla serie giornaliera, per mostrare
  l'evoluzione della variabilità e non solo della media.
- Widget di confronto con **valori di riferimento pubblicati in
  letteratura** (IPCC AR6, rapporti ISPRA) — dichiarati esplicitamente
  come non calcolati da questo progetto e non scaricati in tempo reale,
  solo per dare un contesto di scala.

**Tab Dettaglio tecnico**: test Mann-Kendall/Sen's slope sull'intero
periodo, scomposizione STL, nota di metodologia.

- **Testo esplicativo esteso (2026-07-16)**: su richiesta esplicita
  dell'utente ("non capisco cosa c'è scritto, è poco chiara"), riscritte
  in linguaggio discorsivo, senza riferimenti al codice, le spiegazioni
  di: Mann-Kendall (confronta ogni coppia di anni, conta quante volte il
  più recente è più caldo del più vecchio), MK p-value (probabilità che
  il risultato sia solo caso), Sen's slope (mediana delle pendenze tra
  tutte le coppie di punti, robusta agli anni anomali), Regressione
  °C/decade (la retta di tendenza classica, più sensibile agli estremi ma
  standard nei report climatici) — con una sintesi finale su come i 4
  numeri si completano a vicenda. Stessa estensione per la STL: spiegato
  prima *perché* si scompone una serie giornaliera rumorosa (il segnale
  di riscaldamento, lento, è nascosto sotto oscillazioni stagionali e
  giornaliere molto più grandi), poi cosa mostra ciascuno dei 3 grafici
  (trend = tendenza di fondo ripulita; stagionalità = ciclo che si ripete
  identico ogni anno; residuo = giornate anomale non spiegate dagli altri
  due). Riscritta anche la sezione "Metodologia" in forma di domande e
  risposte (perché due pendenze diverse, perché le stagioni meteorologiche
  e non astronomiche, perché la baseline è fissa, cosa sono i riferimenti
  nazionale/globale) invece dell'elenco puntato originale, giudicato poco
  chiaro dall'utente.

**Opzione aggregata "Piemonte" (2026-07-15)**: una checkbox `🌍 Intero
Piemonte` accanto al selettore "Comune" (che si disabilita quando la
checkbox è attiva, invece di convivere come voce nella stessa lista —
prima versione scartata su richiesta dell'utente, vedi log). Quando
attiva:
- Ogni grafico/metrica della pagina (serie annuale, anomalie, stagioni,
  boxplot, STL, Mann-Kendall) viene calcolato sulla **media aritmetica non
  pesata** dei comuni con dati reali, invece che su un singolo comune.
- Un `st.info` esplicito chiarisce che non è una stima ufficiale della
  temperatura regionale (richiederebbe pesare per area/popolazione e
  includere tutti i 1180 comuni, non solo quelli monitorati; questa
  pagina non ha più un filtro provincia, la media è sempre su tutti i
  comuni monitorati).
- Mann-Kendall/regressione sull'intero periodo per l'aggregato sono
  ricalcolati al volo con le stesse funzioni pure di
  `src/analysis/trend_analysis.py` (`mann_kendall_trend()`/
  `linear_trend()`), non lette da `trend_analysis.csv` (che ha una riga
  per comune, non per l'aggregato); stesso discorso per la STL,
  ricalcolata al volo con `decompose()` di
  `src/analysis/seasonal_analysis.py`.

### Analisi Spaziale (`03_analisi_spaziale.py`) — ampliata il 2026-07-15

**Tab Panoramica**:
- 4 metriche: provincia più calda, provincia con trend più rapido, comune
  più in quota, comuni con dati nel filtro attuale.
- **Mappa coropletica per provincia** (temperatura media nel periodo
  selezionato), confine reale ottenuto aggregando via PostGIS (`ST_Union`)
  le geometrie di tutti i 1180 comuni di ciascuna provincia, non solo
  quelli con dati.
- **Mappa del trend** (punti per comune, colormap divergente centrata
  sullo zero, `lr_slope_per_decade` da `trend_analysis.csv`).
- **Legenda a fasce sotto entrambe le mappe** (2026-07-15,
  `components/maps.py::render_gradient_legend()`) — non il gradiente
  continuo di default di branca, ma 5 fasce discrete con swatch del
  colore realmente usato, range numerico ed etichetta di gravità/velocità
  esplicita (es. "Nella media", "Riscaldamento rapido"), richiesta
  dall'utente per capire subito cosa significa ogni colore senza dover
  interpretare una colorbar continua.
- Confronto per **fascia altitudinale** (pianura/collina/montagna, soglie
  300/700 m su elevazione reale da Open-Meteo).

**Uso del suolo, popolazione e temperatura (2026-07-16, sostituisce il
vecchio confronto "isola di calore urbana")**: il confronto originale
(Torino città vs media dei comuni rurali della sua provincia, dichiarato
esplicitamente "solo illustrativo") è stato sostituito con contenuto
basato sui dati reali di uso del suolo/popolazione aggiunti lo stesso
giorno (vedi [Modello Dati](data-model.md), tabella
`municipality_land_cover`) — su richiesta esplicita dell'utente ("procedi
con Aggiungere popolazione/uso del suolo alla dashboard"):

- **Mappa uso del suolo dominante**: tutti i 1180 comuni (non solo quelli
  con temperatura), colori vicini alla palette ufficiale CORINE
  (`LAND_COVER_COLORS` in `components/constants.py`, presi da
  `data/external/clc_legend.csv`).
- **Mappa densità di popolazione**: tutti i 1180 comuni, scala
  logaritmica (altrimenti Torino schiaccia la scala).
- **Scatter temperatura vs uso del suolo/popolazione**: solo i comuni con
  temperatura, con un selettore (`st.radio`) tra % urbano, % industriale/
  commerciale, densità di popolazione, NDVI (aggiunto 2026-07-17, vedi
  sotto); colore = fascia altitudinale (per valutare a occhio se l'effetto
  regge a parità di quota); metrica di correlazione di Pearson mostrata
  con caveat esplicito ("non controllata per quota"). Verificato con
  `AppTest` un valore reale di correlazione +0.30 (% urbano vs
  temperatura, tutti i comuni) — plausibile, non sospetto.

**NDVI in dashboard + testi metodologici aggiornati (2026-07-17)**: su
richiesta esplicita dell'utente, non appena `municipality_ndvi` è stata
popolata (vedi [Fonti dati](data-sources.md)), portata anche in dashboard
con lo stesso pattern di uso del suolo/popolazione:

- **Nuova mappa NDVI**: tutti i 1180 comuni, colormap continua
  marrone→verde (`NDVI_COLORS` in `components/constants.py`, convenzione
  standard di visualizzazione NDVI, deliberatamente diversa dalla scala
  blu→rosso di temperatura/trend per non confonderla con un'altra mappa di
  calore), legenda a 5 fasce con **2 decimali** (non 1 come le altre
  mappe — l'intervallo NDVI è troppo stretto per 1 decimale: aggiunto un
  parametro `decimals` a `render_gradient_legend()`, default 1 per non
  toccare le mappe esistenti).
- **NDVI aggiunto come 4ª opzione nello scatter** (vedi sopra).
- **Testi "non ancora costruito" corretti**: la pagina citava in due punti
  (caption sotto la metrica di correlazione, sezione Metodologia) un
  "modello che isola l'effetto della quota" come pianificato ma non
  costruito — non più vero da quando `src/analysis/spatial_regression.py`
  è stato scritto ed eseguito lo stesso giorno (vedi
  [Analisi statistica](statistical-analysis.md)). Entrambi i punti ora
  riportano il risultato reale (% urbano diventa significativo col segno
  atteso solo nel modello a errore spaziale, non nell'OLS classico),
  dichiarato esplicitamente provvisorio (n=63 comuni). Aggiunta anche una
  voce in Metodologia sul limite temporale dell'NDVI (composito singolo di
  10 giorni, non una media pluriennale come le temperature).

Verificato con `AppTest` dopo le modifiche: nessuna eccezione, mappa NDVI
e opzione scatter presenti.

**Aggiornamento 2026-07-17 (pomeriggio) — testo corretto dopo l'estensione
a 98 comuni**: dopo l'import dei 35 comuni extra da una seconda macchina
(vedi [ETL](etl-pipeline.md)) e la conseguente ri-esecuzione di
`spatial_regression.py` su n=98 (vedi [Analisi statistica](statistical-analysis.md)),
il risultato descritto sopra (**% urbano significativo nel modello a
errore spaziale**) non è più vero: a campione più ampio **% urbano non è
più significativo** (p=0.334, coefficiente ancora positivo/atteso ma
piccolo). Caption in `03_analisi_spaziale.py` corretta di conseguenza
(non lasciata con un risultato ormai falso solo perché era vero quando
scritta — a differenza delle voci di log storiche, i testi live nella UI
devono riflettere lo stato attuale). Corretto anche un commento
obsoleto in `components/queries.py` (`8 → 44 → 63` → `8 → 44 → 63 → 98`).
Verificato con `AppTest`: nessuna eccezione.

> **Bug corretto durante lo sviluppo**: le query di geometrie/uso del
> suolo condividono la colonna `province_name` — un primo merge tra le due
> produceva `province_name_x`/`province_name_y` invece del nome atteso
> (`KeyError` scoperto subito con `AppTest`, non in produzione), risolto
> escludendo la colonna duplicata da un lato del merge prima di unirle.

**Aggiornamento 2026-07-18 — testo corretto di nuovo dopo l'estensione a
177 comuni**: `spatial_regression.py` rieseguito due volte in più lo
stesso giorno (98 → 155 → 177 comuni, vedi [ETL](etl-pipeline.md) e
[Analisi statistica](statistical-analysis.md)). Il risultato del
2026-07-17 pomeriggio (% urbano non significativo, NDVI ancora
significativo) è cambiato ulteriormente: **a n=177 anche NDVI smette di
essere significativo** (p=0.58, era p=0.007 a n=98). Caption in
`03_analisi_spaziale.py` riscritta un'altra volta per riflettere lo stato
reale — solo l'elevazione resta un predittore robusto in tutte le
versioni provate (n=63/98/177); % urbano e NDVI sono risultati
significativi ciascuno in una sola delle tre versioni, mai insieme,
segno che il campione resta troppo piccolo per conclusioni stabili su
queste due covariate. Verificato con `py_compile` (server live riavviato
subito dopo per riflettere i nuovi dati, non solo il testo).

**Tab Dettaglio tecnico**: cluster climatici K-means (k=3) e indice di
Moran, nota di metodologia sui limiti delle sezioni sopra (fasce
altitudinali semplificate, confronto UHI illustrativo, mappa trend non
ricalcolata sul filtro anni).

- **Testo esplicativo esteso (2026-07-16)**: stessa richiesta e stesso
  trattamento già fatto per Analisi Temporale ("non capisco cosa c'è
  scritto, è poco chiara"). K-means spiegato passo per passo (si fissa in
  anticipo il numero di gruppi, k=3 — scelta pratica per avere zone
  descrivibili a parole, non calcolata con un metodo statistico tipo
  elbow — poi l'algoritmo assegna ogni comune al centro più vicino sulla
  base di temperatura/giorni caldi *standardizzati*, sposta i centri,
  ripete), chiarito esplicitamente che il raggruppamento non guarda la
  posizione geografica dei comuni (se i cluster risultano compatti sulla
  mappa è un risultato, non un'ipotesi di partenza).
- **Suddivisione dinamica dei 3 cluster**: invece di descriverli con
  etichette fisse ("alpino"/"pianura"/"intermedio", fragili se l'analisi
  viene ri-eseguita e la numerazione dei cluster cambia), il codice ora
  ordina i 3 gruppi trovati dal più fresco al più caldo in base alla
  temperatura media reale e genera la descrizione al volo (temperatura
  media, giorni sopra 30°C, elenco comuni) — sempre corretta anche se
  `spatial_analysis.py` venisse ri-eseguito con un'assegnazione di
  cluster diversa.
- **Aggiornamento 2026-07-16**: l'utente ha notato che l'assegnazione
  delle etichette 0/1/2 non seguiva "una logica di ordinamento" — sklearn
  assegna le etichette grezze di K-means in un ordine arbitrario, senza
  legame con la temperatura. Corretto **alla fonte**, non solo nel testo
  della dashboard: `climate_clustering()` in
  `src/analysis/spatial_analysis.py` ora rinumera le etichette per
  temperatura media crescente prima di salvarle (0 = più fresco, 2 = più
  caldo — vedi [Analisi Statistica](statistical-analysis.md)). La logica
  di ordinamento-per-temperatura già scritta lato dashboard resta com'era
  — ora è ridondante rispetto al dato già ordinato alla fonte, ma non
  dannosa, ed è comunque una difesa in più se in futuro l'analisi
  cambiasse. Aggiornati anche i colori: `CLUSTER_COLORS` in
  `components/constants.py` passa da 3 colori categorici senza relazione
  con la temperatura a blu→arancio→rosso (stessa logica della colormap di
  temperatura usata altrove nel sito), e lo stesso schema colori è stato
  applicato anche alla mappa QGIS `hotspot_analysis.qgz`
  (`qgis_projects/build_maps.py`), rigenerata di conseguenza.
- **Indice di Moran**: aggiunta la distinzione esplicita rispetto ai
  cluster K-means (Moran guarda la geografia, K-means no), spiegato il
  calcolo (peso inversamente proporzionale alla distanza tra comuni,
  combinato con quanto ciascuno si discosta dalla media) e perché il
  p-value viene da una permutazione (si mescolano le temperature a caso
  migliaia di volte e si confronta il valore osservato con quelli
  casuali) invece che da una formula diretta. **Metodologia** riscritta
  in domande e risposte, come per Analisi Temporale.

### Ondate di Calore (`04_ondate_di_calore.py`) — ampliata il 2026-07-15

4 metriche in alto (n. ondate nel filtro attuale, n. ondate nell'ultimo
anno della finestra, durata media, intensità media).

**Tab Panoramica**:
- Grafico a barre a doppio asse (n. eventi + durata media per anno).
- Intensità media per anno, con **legenda a 5 fasce** (2026-07-16, "Bassa"
  → "Estrema" — i colori delle barre vengono campionati dalla stessa
  colorscale Plotly del grafico, `plotly.colors.sample_colorscale()`, non
  approssimati con una colormap diversa: legenda e barre garantite
  identiche).
- **Conteggio cumulato** dal 2000 per mostrare se il fenomeno accelera.
- **Mappa di concentrazione geografica** (coropletica per comune, quante
  ondate nel filtro attuale, con legenda a 5 fasce 2026-07-16 — "Poche" →
  "Molto alto", stessa funzione `render_gradient_legend()` delle altre
  mappe, qui con `integer=True` per non mostrare range decimali su un
  conteggio di eventi).
- **Heatmap "calendario"** (anno × giorno dell'anno, colore = quanti
  comuni in ondata quel giorno) per vedere se gli eventi si spostano verso
  primavera/autunno.

**Tab Dettaglio tecnico**: confronto con una **definizione alternativa**
di ondata di calore a soglia percentile (relativa al singolo comune, non
fissa per tutti — vedi sotto), nota di metodologia.

Sotto le tab, invariate: tabella statistiche per comune ed elenco ondate.

- **Testo esplicativo esteso (2026-07-16)**: stesso trattamento già
  applicato ad Analisi Temporale e Analisi Spaziale ("stessa cosa... con
  lo stesso pattern delle altre due pagine"). Spiegato in linguaggio
  discorsivo perché esiste una definizione alternativa a soglia percentile
  (la soglia fissa 35°C tratta tutti i comuni allo stesso modo,
  penalizzando i comuni di montagna che raramente la raggiungono anche in
  estati eccezionali per i loro standard), cos'è un percentile e come si
  calcola in pratica (ordinare tutte le temperature massime storiche di un
  comune, il 90° percentile è il valore sotto cui sta il 90% dei giorni —
  diverso per ogni comune, a differenza dei 35°C fissi). **Metodologia**
  riscritta in domande e risposte (perché il resto del sito usa comunque
  la soglia fissa e non sostituisce mai i numeri ufficiali con quelli
  percentile, perché la durata minima resta 3 giorni in entrambe le
  definizioni per un confronto equo, cosa aggrega esattamente la heatmap
  calendario) — stesso trattamento delle altre due pagine.

### Download Dati

Invariata: ogni file ha una descrizione in linguaggio semplice di cosa
contiene, oltre al bottone di export per i CSV di `data/processed/`,
`data/external/` e `output/`.

### Validazione Dati (`06_validazione_dati.py`) — nuova il 2026-07-18, **rimossa lo stesso giorno in serata**

> **Superata**: questa pagina è stata rimossa il 2026-07-18 in serata,
> contenuto redistribuito nel selettore fonte di Ondate di
> Calore/Analisi Temporale/Analisi Spaziale — vedi "Selettore fonte dati"
> più sotto per il dettaglio del perché e di dove è finito ogni pezzo.
> Sezione lasciata intatta come cronologia di quando la pagina esisteva
> davvero (coerente con la natura non-riscritta di questo log).

Nuova pagina, su richiesta esplicita dell'utente dopo aver eseguito la
validazione ARPA (vedi [Fonti dati](data-sources.md) e
[Analisi statistica](statistical-analysis.md) per il dettaglio completo dei
risultati). Non appartiene a nessuna delle 4 pagine tematiche esistenti
(temporale/spaziale/ondate/download) — è un tema a sé, la qualità del dato
stesso, quindi pagina dedicata invece di un tab dentro una pagina esistente.

- 4 metriche in alto (comuni con stazione ARPA, bias medio, correlazione
  media, % ondate di calore rilevate) + un `st.error` prominente col
  risultato più importante: solo il 31.4% delle ondate di calore reali
  (secondo ARPA) sono rilevate da Open-Meteo.
- **Tab Panoramica**: mappa dei 51 comuni colorata per bias (stessa
  colormap divergente/legenda a 5 fasce di `render_gradient_legend()` già
  usata per la mappa trend di Analisi Spaziale), scatter bias vs elevazione
  (con retta di regressione, `trendline='ols'`), istogramma della
  distribuzione del bias, tabella completa per comune.
- **Tab Dettaglio tecnico**: tabella bias per condizione (tutti i giorni /
  giorni caldi >30°C / >35°C), metriche precision/recall del confronto a
  livello di evento, tabella di confronto del trend ARPA/Open-Meteo per
  comune, nota di metodologia (fonte, matching comune↔stazione, caveat
  sulla rappresentatività della stazione).
- Nuove funzioni in `components/queries.py`: `get_arpa_validation()`,
  `get_arpa_hot_day_bias()`, `get_arpa_trend_comparison()`,
  `get_arpa_event_comparison_summary()` — stesso pattern delle altre
  (`_output_path()` + `st.cache_data`, leggono i CSV prodotti da
  `src/analysis/validate_arpa.py`).
- Verificata con `streamlit.testing.v1.AppTest` (nessuna eccezione, metriche
  coerenti coi CSV reali), poi con il server live riavviato (health check
  `/_stcore/health` → 200, routing `/validazione_dati` → 200).

## Selettore fonte dati (Open-Meteo / ARPA / Confronto) — 2026-07-18

Su richiesta esplicita dell'utente durante una discussione sulla
riorganizzazione del sito: invece di tenere ARPA confinata alla pagina
"Validazione Dati", un **selettore riusabile** che permette di scegliere,
pagina per pagina, se guardare Open-Meteo, solo ARPA (stazione reale) o un
confronto diretto tra le due. Reso possibile dall'estensione della
copertura ARPA a 218 comuni lo stesso giorno (vedi
[Fonti dati](data-sources.md#estensione-a-218-comuni-2026-07-18)).

**Nuovo componente** `components/data_source.py`
(`render_source_selector(key, has_om, has_arpa)`): mostra il radio a 3
opzioni solo se **entrambe** le fonti esistono per il comune/insieme di
comuni correntemente selezionato; se ne esiste solo una, non mostra un
radio con opzioni disabilitate ma restituisce direttamente l'unica fonte
valida con una caption esplicativa — il chiamante non deve mai gestire il
caso "fonte scelta ma dati assenti".

**Nuove funzioni dati** in `components/queries.py` (equivalenti ARPA delle
funzioni Open-Meteo già esistenti, dato che le viste/CSV precalcolati del
progetto — `kpi_annual_by_municipality`, `heatwave_events`,
`trend_analysis.csv`, `heatwave_stats_by_municipality.csv` — sono popolati
solo da Open-Meteo): `get_arpa_municipality_names_with_data()`,
`get_arpa_municipality_metadata()`, `get_arpa_daily_temperature()`,
`get_arpa_daily_temperature_multi()`, `get_arpa_municipality_geometries_wkt()`,
`get_arpa_seasonal_decomposition()` (STL calcolata al volo, come già
succedeva per l'aggregato "Piemonte"), `get_arpa_heatwave_events()` (ondate
calcolate al volo sulla soglia fissa canonica), più tre helper puri
(`compute_annual_kpi_from_daily()`, `compute_frequency_by_year()`,
`compute_stats_by_municipality()`) che replicano la semantica esatta delle
viste/CSV Open-Meteo (es. `temp_max_annual` = MASSIMO dell'anno, non media
dei massimi giornalieri — verificato contro la definizione SQL in
`sql/01_init_database.sql`).

**Nuova funzione** `identify_heatwaves_events()` in
`components/heatwave_definitions.py`: versione Python multi-comune della
definizione canonica a soglia fissa già implementata lato SQL in
`identify_heatwaves()` — necessaria perché quella funzione scrive solo in
`heatwave_events`, popolata solo da Open-Meteo. Non sostituisce la
funzione SQL (resta l'unica fonte di verità per Open-Meteo), la affianca
per i dati ARPA.

**Pagine aggiornate**:
- **Analisi Temporale** (`02_analisi_temporale.py`): il selettore comune
  ora elenca l'**unione** dei comuni Open-Meteo e ARPA (non solo i 177
  Open-Meteo), rendendo raggiungibili anche i 167 comuni solo-ARPA. In
  modalità "Solo ARPA" l'intera pagina (serie annuale, anomalie, stagioni,
  boxplot, trend Mann-Kendall/regressione, STL) è ricalcolata sulla serie
  di stazione. In modalità "Confronto" le sezioni stagioni/boxplot/STL
  restano su Open-Meteo (dichiarato esplicitamente in una caption, non
  nascosto) mentre il grafico della serie annuale riceve una traccia
  ARPA sovrapposta (tratteggiata) e compare un riquadro "Confronto
  sintetico ARPA vs Open-Meteo" con le due pendenze e il bias medio
  annuo. Il checkbox "🌍 Intero Piemonte" disattiva il selettore (resta
  solo Open-Meteo, motivato in un `st.info`): mediare comuni ARPA-only
  nell'aggregato regionale non è stato messo in scope questo giro.
- **Ondate di Calore** (`04_ondate_di_calore.py`): il selettore è
  globale (si applica a tutti i grafici/mappa/tabelle della pagina, non a
  un singolo comune, perché la pagina aggrega sempre su un insieme di
  comuni filtrati per anno/provincia). In modalità "Solo ARPA" frequenza
  per anno, mappa di concentrazione, heatmap calendario, statistiche per
  comune ed elenco ondate sono tutti ricalcolati dal vivo su
  `get_arpa_heatwave_events()`. In modalità "Confronto" i grafici restano
  su Open-Meteo e viene aggiunto un riquadro con le metriche già calcolate
  da `validate_arpa.py` (recall 31.4%, precision 62%, conteggio ondate
  ARPA vs Open-Meteo) — **stesso contenuto di cuore della pagina
  Validazione Dati**, mostrato qui invece che solo in una pagina separata.

**Scope deliberatamente lasciato fuori da questo giro** (comunicato
all'utente, non un limite scoperto in corsa):
- Pagina "Validazione Dati" **non rimossa**: la mappa/scatter bias vs
  elevazione e la tabella completa per comune non hanno una casa naturale
  in Analisi Temporale o Ondate di Calore (sono sulla qualità del dato in
  sé, non su un trend o un evento) — l'utente non ha chiesto esplicitamente
  di eliminarla, solo di non *aggiungerne* di nuove.
- Analisi Spaziale e Download Dati non hanno ricevuto il selettore: ARPA
  non ha elevazione/uso del suolo/NDVI/CSV export propri, un selettore lì
  sarebbe stato solo rumore (già discusso con l'utente prima di procedere).
- Modalità "Confronto" non duplica ogni grafico per entrambe le fonti (solo
  metriche di sintesi + una traccia sovrapposta dove sensato) — una
  duplicazione completa avrebbe raddoppiato la lunghezza di entrambe le
  pagine per un beneficio marginale rispetto ai numeri di confronto già
  disponibili.

**Verifica**: `py_compile` su tutti i file toccati; `streamlit.testing.v1.AppTest`
su entrambe le pagine con tutte e 3 le combinazioni di fonte (incluso un
comune solo-ARPA come Domodossola, che attiva il percorso "selettore
nascosto, fonte forzata"), nessuna eccezione.

**Aggiornamento stesso giorno (sera) — server riavviato e selettore esteso
ad Analisi Spaziale**: l'utente ha chiesto di riavviare il server per un
controllo visivo — trovati **3 processi Streamlit duplicati** in ascolto
sulla stessa porta (stesso bug già documentato il 2026-07-15), terminati
tutti e riavviato un solo processo pulito (verificato con
`Get-NetTCPConnection`, health check `/_stcore/health` → 200).

Nella stessa conversazione, l'utente ha fatto notare che Analisi Spaziale
era stata esclusa dal selettore senza una giustificazione solida: la
motivazione iniziale ("uso del suolo/NDVI/popolazione non dipendono dalla
fonte") era corretta solo per una parte della pagina — le mappe
coropletica per provincia, del trend per comune, il confronto per fascia
altitudinale, il clustering K-means e l'indice di Moran sono invece
**tutti calcolati sulla temperatura Open-Meteo**, quindi hanno un
equivalente ARPA legittimo (e la fascia altitudinale è proprio dove il
bias di Open-Meteo è più marcato). Selettore esteso di conseguenza:

- **Bloccante scoperto prima di procedere**: `elevation_m` era popolata
  solo per i 177 comuni Open-Meteo (`fetch_elevation.py` filtrava su
  `temperature`), quindi il confronto per fascia altitudinale sarebbe
  stato vuoto per tutti i 167 comuni solo-ARPA. Risolto ampliando la
  query a `temperature OR arpa_temperature` e rieseguendo lo script (vedi
  [Modello dati](data-model.md)) prima di scrivere il codice della
  pagina — non dopo aver scoperto il bug in dashboard.
- **Nuove funzioni** in `queries.py`: `get_arpa_kpi_annual()` (equivalente
  ARPA di `kpi_annual_by_municipality`, calcolato in SQL con `GROUP BY`
  invece che con una vista), `get_arpa_trend_analysis()` (Mann-Kendall +
  regressione per tutti i 218 comuni ARPA, mai calcolato in batch prima
  d'ora), `get_arpa_municipality_features()`/`get_arpa_spatial_clustering()`/
  `get_arpa_morans_i()` (riusano le funzioni pure già esistenti in
  `src/analysis/spatial_analysis.py` — `climate_clustering()`,
  `build_inverse_distance_weights()`, `morans_i_permutation_test()` — con
  dati aggregati da `arpa_temperature` invece che dalla vista Open-Meteo).
  `get_arpa_municipality_metadata()` estesa con `elevation_m`/`lat`/`lon`
  (prima aveva solo provincia).
- **Cosa risponde al selettore**: mappa coropletica per provincia, mappa
  del trend, confronto per fascia altitudinale, cluster K-means, indice di
  Moran, e le 4 metriche in alto (provincia più calda/trend più
  rapido/comune più in quota/comuni con dati).
- **Cosa resta sempre su Open-Meteo** (dichiarato in una caption fissa
  sotto il selettore, non un limite silenzioso): le mappe di uso del
  suolo/popolazione/NDVI (dati indipendenti dalla fonte di temperatura,
  coprono comunque tutti i 1180 comuni) e lo scatter
  temperatura/uso-del-suolo (legato al modello di regressione spaziale già
  discusso in Metodologia, calcolato solo su Open-Meteo).
- **Modalità "Confronto"**: mappe/cluster/Moran restano su Open-Meteo
  (stessa convenzione delle altre due pagine — niente duplicazione
  completa dei grafici); la fascia altitudinale riceve invece un vero
  confronto numerico (tabella con temperatura media per fascia su
  entrambe le fonti + colonna di bias), perché è il punto in cui la
  differenza tra le due fonti è più interessante da mostrare.
- **Verifica**: `py_compile`, poi `AppTest` su tutte e 3 le combinazioni di
  fonte — nessuna eccezione, ma **pagina lenta** (70-80s in modalità
  ARPA/Confronto contro pochi secondi delle altre pagine, dovuto alle
  mappe con centinaia di poligoni per uso del suolo/popolazione/NDVI su
  tutti i 1180 comuni — costo preesistente della pagina, non introdotto da
  questa modifica) e server live riavviato (vedi sopra) per la verifica
  visiva finale, richiesta esplicitamente dall'utente.

**Mappa del trend in "Confronto" — corretta dopo una domanda diretta
dell'utente**: la prima versione (sopra) mostrava, in modalità Confronto,
la mappa del trend calcolata **solo su Open-Meteo** (stessa convenzione
usata per cluster/Moran), col confronto vero relegato solo alla tabella
per fascia altitudinale. L'utente ha chiesto esplicitamente "la mappa che
vedo ha i colori di entrambi i dati?" — la risposta onesta era no, e la
scelta di scope non reggeva bene proprio per questa mappa (è il punto in
cui vorresti vedere a colpo d'occhio se le due fonti raccontano zone
diverse). Chiesto all'utente come preferiva risolvere (`AskUserQuestion`:
due mappe affiancate / mappa del bias sostitutiva / lasciare com'era) —
scelta: **due mappe affiancate**, stessa scala colore (`vmin`/`vmax`
condivisi = massimo assoluto tra le due fonti, altrimenti lo stesso rosso
potrebbe rappresentare velocità diverse da una mappa all'altra), una
colonna Open-Meteo e una ARPA, un'unica legenda condivisa sotto entrambe.
Codice di disegno mappa estratto in `render_trend_map()` (funzione locale
nella pagina) per non duplicarlo tra il ramo Confronto e quello a fonte
singola. Ri-verificato con `AppTest` (OM default + Confronto), nessuna
eccezione.

**Spiegata all'utente, non implementata in questo giro**: la differenza
concettuale tra questa mappa del trend (ogni fonte calcola la propria
pendenza in autonomia, quindi funziona anche per comuni con una sola
fonte) e la mappa del **bias** già esistente nella pagina "Validazione
Dati" (differenza diretta OM−ARPA sullo stesso comune/giorno — richiede
**entrambe** le fonti per lo stesso comune, quindi strutturalmente
limitata ai 51 comuni con copertura doppia, non estendibile ai 167
solo-ARPA finché non ci sarà più sovrapposizione tra le due fonti).

**Stesso bug trovato di nuovo in Ondate di Calore**: dopo la correzione
sopra, l'utente ha notato che anche la mappa "Dove si concentrano
geograficamente le ondate" in Ondate di Calore aveva lo stesso problema
(in Confronto mostrava solo Open-Meteo). Corretta con lo stesso pattern —
due mappe affiancate (Open-Meteo/ARPA), stessa scala colore condivisa,
codice di disegno estratto in due funzioni locali
(`render_concentration_map()`/`count_events_by_municipality()`) per non
duplicarlo tra il ramo Confronto e quello a fonte singola. Gli altri
grafici/tabelle della pagina (frequenza per anno, heatmap calendario,
statistiche/elenco ondate) restano su Open-Meteo in Confronto, dichiarato
in caption — solo le due mappe di concentrazione/trend fanno eccezione
alla convenzione "Confronto = Open-Meteo + pannello numerico", perché
sono i punti dove il confronto visivo diretto vale più di un numero.
Ri-verificato con `AppTest` (OM + Confronto), nessuna eccezione.

## Riferimenti a wiki/codice rimossi dal frontend (2026-07-18, sera)

L'utente ha fatto notare che la dashboard è potenzialmente visibile anche
a persone esterne al progetto (recruiter/tech lead, dato l'uso da
portfolio) — testo come "vedi `wiki/pages/statistical-analysis.md`" o
"esegui `python -m src.analysis.spatial_analysis`" nei caption/markdown
renderizzati non ha senso per chi non ha accesso al codice sorgente.
Cercati sistematicamente (con un sub-agent di ricerca dedicato, per non
mancarne nessuno) tutti i punti dove testo passato a `st.caption`/
`st.markdown`/`st.info`/etc. citava percorsi wiki, script Python o nomi
di funzioni interne — **13 occorrenze** in `Home.py` (3),
`03_analisi_spaziale.py` (9), `04_ondate_di_calore.py` (4). Tutte
riscritte in linguaggio semplice, senza percorsi/nomi tecnici: i
messaggi di fallback ("dati non ancora generati") non citano più il
comando da eseguire, i riferimenti a moduli di analisi diventano
descrizioni testuali ("una regressione OLS con...", non
"`src/analysis/spatial_regression.py`").

**Cosa NON è stato toccato** (deliberatamente): i commenti Python (`#`)
e le docstring nel codice (mai renderizzati a schermo, es. tutte le
funzioni di `components/queries.py`) restano pieni di riferimenti
wiki/script — sono documentazione per chi legge il codice, non per chi
guarda la dashboard nel browser, quindi fuori dallo scope di questa
richiesta. Anche la citazione di `ARPA Piemonte` come fonte dati è
rimasta (non è un riferimento al codice/wiki del progetto, ma
un'attribuzione della fonte dei dati, legittima in un portfolio).

**Non ancora fatto**: l'utente ha anche chiesto di cambiare il titolo
"Heatwave Piemonte" (giudicato poco significativo) — non ancora deciso
un nome sostitutivo (`AskUserQuestion` proposto 3 opzioni, risposta
"ci penso"). Da applicare in `config.yaml` (`dashboard.title`), in tutti
gli `st.set_page_config(page_title=...)` delle pagine, e nell'hero della
Home (`render_hero(title=...)`) una volta deciso. Se in futuro il
repository GitHub diventa pubblico, l'utente ha detto che un link ad
esso in fondo alla pagina sarebbe accettabile (non un riferimento a
wiki/codice interno, ma un invito a esplorare il progetto completo) —
non aggiunto ora perché il repository non è ancora pubblico.

**Verifica**: `py_compile` su tutti i file toccati; `AppTest` su
`Home.py` e su tutte le combinazioni di fonte di Analisi Spaziale e
Ondate di Calore, nessuna eccezione.

## Baseline delle anomalie: da configurabile a fissa (2026-07-15)

La prima versione lasciava scegliere all'utente inizio/fine della baseline
tramite due `number_input`. L'utente ha fatto notare che non aveva senso
lasciarla configurabile (aggiunge un dubbio — "che periodo scelgo?" —
senza un reale beneficio per chi guarda la pagina per capire il fenomeno,
non per esplorare scenari) e ha chiesto un parere: d'accordo con
l'osservazione, rimossi i due widget.

Baseline ora **fissa** al primo decennio disponibile per il comune
selezionato (scelta standard in climatologia quando non è disponibile il
periodo di riferimento convenzionale 1961-1990/1991-2020 — qui i dati
partono dal 2000). Il testo sopra il grafico spiega ora esplicitamente, in
linguaggio semplice: cos'è un'anomalia, come si calcola, perché quella
baseline (non le altre) e come leggere le barre rosse/blu.

## Due decisioni di merito prese durante l'ampliamento (2026-07-15)

- **Definizione di ondata di calore, canonica vs alternativa**: la
  richiesta iniziale chiedeva di "implementare una funzione per
  identificare le ondate di calore" con una soglia percentile. Il
  progetto ha già una definizione canonica, usata ovunque nel resto del
  sito (`identify_heatwaves()` nel database, soglia fissa 35°C/3gg — vedi
  [Modello Dati](data-model.md)): sostituirla avrebbe reso incoerenti
  tutti i numeri già mostrati altrove (ondate in home, statistiche per
  comune, ecc.). Scelta: la soglia percentile è implementata come
  funzione pura
  (`components/heatwave_definitions.py::identify_heatwaves_percentile()`)
  e usata **solo** nel tab "Dettaglio tecnico" della pagina Ondate di
  Calore, come confronto metodologico calcolato al volo per il comune
  selezionato — non tocca il database né gli altri numeri del sito.
- **Elevazione reale invece di un placeholder**: `municipalities.elevation_m`
  era `NULL` per tutti i comuni (mai popolato, voce aperta in
  [Stato del Progetto](project-status.md)). Necessario per il confronto
  per fascia altitudinale richiesto nella pagina Analisi Spaziale. Chiesto
  esplicitamente all'utente se scaricare il dato reale o mostrare un
  placeholder "non disponibile": scelto di scaricarlo davvero (Open-Meteo
  Elevation API, poche decine di chiamate, pochi secondi) — vedi
  [Fonti Dati](data-sources.md) e [Modello Dati](data-model.md).

Tutte le pagine continuano a mostrare avvisi/info (`st.warning`/`st.info`)
sulla granularità limitata (comuni con dati su 1180 totali) dove rilevante.

**Leggibilità per non addetti ai lavori (2026-07-15)**: aggiunto un
riquadro `st.expander("ℹ️ Come si legge questa pagina")` a inizio di ogni
pagina di analisi, con spiegazioni in linguaggio semplice dei metodi
statistici usati, più didascalie (`st.caption`) sotto ogni grafico/metrica
principale. Con l'ampliamento successivo, ogni nuovo grafico ha ricevuto
lo stesso trattamento (2-3 righe di "cosa guardare" sopra ciascuno, non
solo sui grafici preesistenti).

## Etichette leggibili per l'esito di Mann-Kendall (2026-07-15)

`pymannkendall` restituisce testualmente `'increasing'`/`'decreasing'`/
`'no trend'`. Mostrato così in dashboard, `'no trend'` viene facilmente
letto come "il clima è stabile qui", mentre significa "con i dati
disponibili non c'è abbastanza evidenza statistica per dire se c'è un
trend" — un limite del test, non un'affermazione sul clima.

Aggiunta `components/constants.py::format_mk_trend()` (dizionario
`MK_TREND_LABELS`) che traduce l'esito in etichette con icona: `📈 In
aumento` / `📉 In diminuzione` / `🔍 Nessun trend chiaro`. Applicata
ovunque compare `mk_trend`: metrica in alto e tab "Dettaglio tecnico" di
`02_analisi_temporale.py`, tabella comparativa in `Home.py`.

## Tema e rifiniture estetiche (2026-07-15)

Su segnalazione esplicita dell'utente ("estetica bruttissima", testo delle
etichette lunghe come "🔍 Nessun trend chiaro" tagliato a metà dentro
`st.metric`):

- **`.streamlit/config.toml`** (nuovo): tema nativo Streamlit invece di
  CSS sparso — palette coerente (blu `#2563eb` come colore primario,
  sfondi e bordi neutri), supporto sia chiaro che scuro
  (`[theme]`/`[theme.dark]`, con sezioni
  `[theme.sidebar]`/`[theme.dark.sidebar]` dedicate), angoli arrotondati
  (`baseRadius`), bordo sui widget (`showWidgetBorder`), e una
  `chartCategoricalColors` allineata alla palette già usata nei grafici
  (`components/constants.py`). **Le chiavi non sono state copiate a
  memoria**: verificate una per una contro
  `.venv/Lib/site-packages/streamlit/config.py` della versione
  effettivamente installata (1.58.0), perché alcune (`baseRadius`,
  `showWidgetBorder`, `chartCategoricalColors`, le sezioni
  `[theme.dark]`) sono relativamente recenti e non esistono in versioni
  più vecchie di Streamlit.
- **`components/styling.py`** (nuovo, `inject_custom_css()`): la causa
  reale del testo tagliato è che `st.metric` applica `white-space: nowrap`
  + `text-overflow: ellipsis` al valore — pensato per numeri corti, non
  per etichette testuali come "Nessun trend chiaro" o nomi di comune
  lunghi come "Verbano-Cusio-Ossola". Il tema da solo non tocca questo
  dettaglio (è CSS applicato dal componente, non un colore/font del
  tema), quindi serve un piccolo override mirato: `white-space: normal`
  sul selettore `[data-testid="stMetricValue"]` (verificato — grep nei
  bundle JS di Streamlit installati, non un selettore indovinato — che
  questo `data-testid` esiste davvero in questa versione), così il testo
  va a capo su due righe invece di sparire. Chiamata una volta per
  pagina, subito dopo `st.set_page_config()`, in `Home.py` e in tutte le
  pagine di `pages/`.
- **Claim superato il 2026-07-17**: questa sezione diceva che le card
  della home non erano stilizzabili via CSS perché Streamlit le
  renderizza con classi generate dinamicamente (`st-emotion-cache-*`).
  Streamlit 1.58 (la versione installata anche allora) espone in realtà
  `st.container(key=...)`, che aggiunge una classe **stabile**
  `st-key-<key>` al wrapper (verificato nel bundle JS installato,
  funzione `iV()` che genera `st-key-` + slug) — la limitazione non era
  nel framework ma nel non aver ancora scoperto/usato questo parametro.
  Le card della home sono state riscritte di conseguenza, vedi
  "Restyling identità visiva" sotto.

**Verifica**: tutte le pagine compilate (`py_compile`) e ri-verificate con
`AppTest` (nessuna eccezione) dopo l'aggiunta di `inject_custom_css()`;
server live riavviato (i cambi a `.streamlit/config.toml` richiedono un
riavvio completo, non bastano l'hot-reload di Streamlit) e verificato con
un solo processo in ascolto sulla porta 8501 (vedi bug dei processi
duplicati sotto).

## Restyling identità visiva "calore" (2026-07-17)

Su richiesta esplicita dell'utente ("frontend troppo minimalista e piatto,
sembra un PDF"): restyling della Home, propagato a tipografia/mappe/grafici
delle altre 4 pagine.

**Processo**: prima un **mockup HTML statico** (Artifact, non nel
repository) per validare la direzione visiva senza iterare direttamente
nel codice Streamlit — un giro di feedback ("sfondo troppo nero") ha
spostato la base da quasi-nero (`#0a0e14`) a grigio ardesia
(`#1c2130`/`#262c3d`) prima di implementare.

**Scelta chiave**: niente palette nuova — `THEME_COLD`/`THEME_MID`/
`THEME_HOT` in `components/constants.py` riusano gli stessi hex già usati
nei grafici (`NEUTRAL_COLOR`/`ALERT_COLOR` esistenti + un arancio
`#f39c12` già presente come colore letterale in più punti). L'interfaccia
eredita il linguaggio cromatico dei dati (freddo→caldo), non il contrario.

**Cosa segue il tema chiaro/scuro nativo di Streamlit, cosa no**:
`st.plotly_chart` usa di default `theme="streamlit"` (verificato in
`streamlit/elements/plotly_chart.py` del pacchetto installato), che adatta
già da solo font/colori dei grafici al tema chiaro/scuro attivo — per
questo `components/charts.py::apply_chart_theme()` tocca **solo** lo
sfondo (trasparente) e non i colori del testo: fissarli avrebbe rotto
l'adattamento automatico se l'utente passa al tema chiaro. Per lo stesso
motivo la tipografia globale (Fraunces per i titoli, Manrope per il corpo,
JetBrains Mono per le cifre di `st.metric`) cambia solo i font, mai i
colori. Hero, card di navigazione e striscia "numeri chiave" in `Home.py`
sono invece componenti **nuovi** (non widget nativi Streamlit) con
un'identità scura **fissa**, scelta deliberata come il mockup approvato,
non un tentativo di inseguire il toggle chiaro/scuro.

> **Claim superato il 2026-07-18**: "identità scura fissa" non è più vero.
> Con il tema chiaro nativo attivato, l'identità fissa produceva pannelli
> neri fuori posto su una pagina bianca (feedback utente: "cambia solo lo
> sfondo in bianco ed è brutto") — vedi "Tema chiaro adattivo per
> hero/card/stats" più sotto per il fix.

**Cosa è cambiato**:
- `components/constants.py`: nuovi token `THEME_INK/SURFACE/BORDER/TEXT/...`,
  `FONT_DISPLAY` (Fraunces), `FONT_BODY` (Manrope), `FONT_MONO` (JetBrains
  Mono), `MAP_TILES` (vedi nota sotto: tornato a `"CartoDB positron"` dopo
  un giro di feedback).
- `components/styling.py`: `@import` Google Fonts; tipografia globale
  (h1/h2/h3 → Fraunces, corpo → Manrope, `st.metric` → monospace
  tabulare); hover/attivo sulla nav della sidebar via
  `[data-testid="stSidebarNavLink"]` + `[aria-current="page"]` (API
  stabili, verificate nel bundle JS installato — non classi hashate); tre
  nuove funzioni: `render_hero()`, `render_nav_card_header()`,
  `render_stats_row()`.
- `components/charts.py` (nuovo): `apply_chart_theme(fig)`, richiamato
  prima di ogni `st.plotly_chart` in `02_analisi_temporale.py` (5
  grafici), `03_analisi_spaziale.py` (2) e `04_ondate_di_calore.py` (4).
- `Home.py`: hero termico (eyebrow + titolo in Fraunces con gradiente di
  testo + aurora di sfondo animata, `prefers-reduced-motion` rispettato);
  le 3 card di navigazione ora sono veri `st.container(key="navcard-<slug>")`
  con bordo a gradiente diverso per card (cold/mid/hot) e hover
  lift+glow, `st.page_link` nativo mantenuto dentro lo stesso container
  per non rompere la navigazione SPA con un `<a>` costruito a mano;
  striscia "numeri chiave" con sparkline SVG inline (illustrativa, non
  calcolata dalla serie storica reale — dichiarato nel docstring di
  `render_stats_row()`).

**Mappe Folium — provato e poi ripristinato**: tentativo iniziale con
`MAP_TILES = "CartoDB dark_matter"` nelle 7 mappe di `Home.py`,
`03_analisi_spaziale.py` e `04_ondate_di_calore.py`. **Respinto
dall'utente lo stesso giorno** ("mappe brutte, scure, troppi casini") — le
etichette/strade del tile scuro competevano con i poligoni colorati
sovrapposti, e non era mai stato validato su un mockup reale (quello
approvato mostrava una mappa come illustrazione SVG statica, non un vero
tile Folium). `MAP_TILES` è tornato a `"CartoDB positron"` (comportamento
pre-restyling); vedi `wiki/log.md` per il dettaglio del giro di feedback.

> **Bug reale trovato dopo il primo giro** (l'utente ha riaperto la
> dashboard e ha visto sfondo ancora nero + HTML grezzo a schermo):
> `render_hero()` e `_stat_tile_html()` costruivano l'HTML con f-string
> multi-riga indentate secondo lo stile del codice Python. CommonMark (il
> parser di `st.markdown`, anche con `unsafe_allow_html=True`) tratta una
> riga indentata di 4+ spazi come **blocco di codice letterale**, non come
> HTML — hero/card/stats non diventavano mai HTML vero, da cui il testo
> grezzo visibile e lo sfondo scuro nativo di Streamlit al posto di
> `THEME_INK`. Fix: entrambe le funzioni riscritte su una sola riga
> (nessun `\n`/indentazione nell'output), stesso pattern già usato con
> successo in `render_nav_card_header()`. Verificato con `AppTest` che
> nessuno dei blocchi markdown della Home inizi più con whitespace/newline.

**Verifica** (nessun browser disponibile in questa sessione): `py_compile`
su tutti i file toccati; `streamlit.testing.v1.AppTest` su tutte e 5 le
pagine con il database reale — nessuna eccezione; server live avviato
(`streamlit run dashboard/Home.py`), `curl` con esito 200, poi fermato
correttamente (un solo processo, verificato con `netstat` prima di
`taskkill`). La verifica visiva effettiva (hover/gradiente/font
renderizzati davvero) resta da fare in un browser reale — non è stata
affermata come completata.

## Tema chiaro adattivo per hero/card/stats (2026-07-18)

Feedback esplicito dell'utente dopo aver provato il toggle chiaro/scuro
nativo di Streamlit: "cambia solo lo sfondo in bianco ed è brutto". Causa:
l'identità scura **fissa** di hero/card di navigazione/striscia numeri
chiave (scelta deliberata del restyling 2026-07-17, vedi sopra) non seguiva
il toggle — passando a chiaro, lo sfondo nativo diventava bianco ma questi
pannelli restavano sul grigio ardesia scuro, un contrasto sbagliato e non
un vero tema chiaro disegnato.

**Fix**: `components/constants.py::THEME_TOKENS` ora è un dizionario
`{"dark": {...}, "light": {...}}` invece di costanti fisse (`THEME_INK`,
`THEME_SURFACE`, `THEME_BORDER`, `THEME_TEXT*` diventano chiavi del dict,
una coppia per modo); i colori "brand" indipendenti dal modo
(`THEME_COLD`/`THEME_MID`/`THEME_HOT`) restano costanti invariate.
`components/styling.py::inject_custom_css()` legge `st.context.theme.type`
(introdotto in Streamlit per questo scopo, vedi
`references/theme.md` dello skill Streamlit installato) e sceglie la coppia
di token corrispondente prima di costruire il CSS. Stesso principio di
design del tema scuro (validato 2026-07-17): lo sfondo del pannello si
**fonde** con lo sfondo nativo dello stesso modo (`ink` = `backgroundColor`
del tema Streamlit attivo) invece di essere un blocco di colore a sé — la
distinzione visiva viene da bordo/glow/gradiente del titolo, non da un
riquadro scuro su pagina chiara. Il gradiente del titolo hero (`hero_title_gradient`)
ha due varianti: bianco→crema→corallo su sfondo scuro (invariato), ardesia
scuro→ambra→rosso ember su sfondo chiaro (nuovo, altrimenti un testo chiaro
trasparente sarebbe illeggibile su bianco); le sfumature radiali di sfondo
(`glow_opacity`) sono più tenui in chiaro (altrimenti "sporche" sul bianco).

**Limite noto, non risolto in questo giro** (documentato esplicitamente nel
docstring di `st.context.theme.type` di Streamlit stesso): il cambio tema
dal menu Impostazioni è puro lato-client e non forza un rerun dello script,
quindi subito dopo il click i colori di questi pannelli restano quelli del
rerun precedente finché non arriva una vera esecuzione (navigazione tra
pagine, refresh, interazione con un widget). Non risolvibile senza un
componente custom che ascolti l'evento di cambio tema e forzi
`st.rerun()` — fuori scope per un fix di stile.

**Verifica visiva reale** (non solo `AppTest`/`py_compile`): server live
avviato, screenshot con Playwright + Chrome di sistema (nessun browser
Playwright scaricato, `channel="chrome"` punta a
`C:\Program Files\Google\Chrome`) prima e dopo lo switch tema dal menu
Streamlit (`data-testid="stMainMenuItem-theme-Dark"`/`-Light`). Confermato:
tema chiaro ora coerente (hero bianco fuso con la pagina, titolo in
gradiente scuro→ember, card con bordo colorato), tema scuro **invariato**
rispetto al restyling 2026-07-17 dopo un reload (nessuna regressione), e il
limite di sincronizzazione sopra riprodotto e poi verificato che si
autocorregge dopo un reload/rerun.

## Come verificare senza aprire un browser

`streamlit.testing.v1.AppTest` esegue davvero lo script Streamlit
in-process e permette di ispezionare eccezioni ed elementi renderizzati:

```python
from streamlit.testing.v1 import AppTest
at = AppTest.from_file('dashboard/Home.py', default_timeout=30)
at.run()
assert not list(at.exception)
```

Un semplice `curl http://localhost:8501` **non basta**: Streamlit è
un'app client-rendered (SPA), quindi la risposta HTTP grezza è solo il
"guscio" statico — il contenuto vero (metriche, tabelle, titoli) non è nel
markup HTML iniziale e va verificato con `AppTest` o un browser reale.

## Nessuna connessione DB live: export statico per il deploy (2026-07-18, sera, nona parte)

**Sorgenti**: `src/data_processing/export_dashboard_data.py`,
`dashboard/components/queries.py`, `requirements-dashboard.txt`.

Dopo aver discusso con l'utente dimensioni del DB (419 MB a 177 comuni,
proiezione ~1 GB a 300 comuni + 250 stazioni ARPA — poi superata: si è
arrivati a **218 stazioni ARPA e 756 MB reali lo stesso giorno**) e costi di
hosting, decisione esplicita dell'utente: **niente DB live in produzione**. I
dati cambiano solo quando l'utente rilancia la pipeline in locale, quindi una
connessione Postgres sempre aperta da un sito pubblico costerebbe (fuori dai
free tier di Supabase/Neon a queste dimensioni) senza portare benefici
percepibili, oltre ad aggiungere superficie di sicurezza (credenziali
esposte). Obiettivo: `dashboard/` deployabile su Streamlit Community Cloud
leggendo solo file statici dal repo Git.

**Scoperta che ha allargato lo scope**: `output/` (dove `src/analysis/*.py`
scrive i CSV già letti da metà delle funzioni di `queries.py`) è escluso da
Git (`.gitignore`: `output/`, `*.csv`, `*.geojson`). Quindi anche le pagine
già "file-based" non avrebbero funzionato su un deploy da GitHub — il
problema non era solo "togliere il DB live", ma unificare **tutto** l'accesso
dati della dashboard su un'unica cartella versionata.

**Ulteriore complicazione emersa a metà lavoro**: mentre questo cambio era in
corso, in parallelo l'utente ha esteso ARPA a 218 comuni e aggiunto
l'architettura "seconda fonte dati" descritta sopra (selettore
Open-Meteo/ARPA/Confronto) — per i 167 comuni solo-ARPA, trend/ondate/
cluster/Moran's I/STL sono calcolati **al volo in Python** da
`arpa_temperature` grezza, non da CSV precalcolati. `queries.py` è passato da
25 a 35 funzioni pubbliche nel frattempo. Il piano di export è stato
aggiornato di conseguenza prima di scrivere codice.

**Soluzione**: un solo export "a valle" invece di DB + CSV sparsi.
`export_dashboard_data.py` legge Postgres (Open-Meteo e ARPA) e i CSV di
`output/` (inclusi i 177 file per-comune di `output/seasonal_decomposition/`,
**consolidati in un solo Parquet** — 121 MB in CSV diventano 46 MB), e scrive
tutto come **Parquet** (via `pyarrow`) sotto `data/dashboard_export/`
(**69 MB totali**, non intercettata da nessuna regola `.gitignore`
esistente, quindi tracciata di default). File principali: `temperature_daily_all.parquet`
e `arpa_temperature_daily_all.parquet` (serie giornaliere complete, da cui
`queries.py` filtra/aggrega in pandas invece che con `WHERE`/`GROUP BY` SQL),
`municipality_metadata_all.parquet`/`all_municipality_geometries.parquet`
(unificati per tutti i 1180 comuni, invece di file separati Open-Meteo/ARPA),
`overview_stats.json`, le viste KPI, geometrie provincia, uso del
suolo/NDVI, e la copia Parquet delle CSV di analisi già esistenti.

`queries.py` riscritta: stesse ~35 funzioni pubbliche, stessa firma e stesso
valore di ritorno — **nessuna pagina in `dashboard/pages/` toccata**. Le
funzioni "calcolate al volo" per ARPA (`identify_heatwaves_events`,
`climate_clustering`, `morans_i_permutation_test`, `mann_kendall_trend`,
`decompose`, ecc.) non sono cambiate: erano già funzioni pure su DataFrame,
solo la funzione a monte che le alimentava con una query SQL live è diventata
un filtro pandas su Parquet. Rimossi gli import di `sqlalchemy`/
`src.utils.database.db_manager` da `queries.py`; nessun file sotto
`dashboard/` importa più `db_manager` (verificato con grep).

**`requirements-dashboard.txt`** (nuovo): sottoinsieme minimale di
`requirements.txt` per il deploy, esclude `psycopg2-binary`, `geoalchemy2`,
`rasterio`, `cdsapi`, `netCDF4`, `spreg`, `libpysal` (mai usate da codice
raggiungibile dalla dashboard). **Nota non ovvia**: `sqlalchemy` resta
comunque necessaria anche qui — `queries.py` importa a runtime funzioni pure
di `src/analysis/trend_analysis.py`/`seasonal_analysis.py`/`spatial_analysis.py`,
che a livello di modulo fanno `from sqlalchemy import text` e
`from src.utils.database import db_manager` (mai una connessione vera: la
classe è istanziata lazy, l'engine si crea solo alla prima query, mai
eseguita da questi percorsi) — verificato leggendo il codice di
`src/utils/database.py`, non assunto.

**Verifica**: script di export rieseguito contro il DB reale (locale, non
toccato/modificato dall'export, sola lettura); dimensione confermata con `du
-sh`; `streamlit.testing.v1.AppTest` su tutte le pagine reali della dashboard
— nessuna eccezione. Durante la verifica scoperto che la pagina dedicata
`06_validazione_dati.py` **non esiste più** (rimossa lo stesso giorno,
contenuto confluito nel selettore fonte dati di
`03_analisi_spaziale.py`/`04_ondate_di_calore.py`, vedi sezione sopra) — lo
script di verifica aggiornato di conseguenza, nessun impatto sul resto del
lavoro. Non è stato spento Postgres per una verifica "a interruttore" (altre
sessioni potrebbero dipendere dal servizio essere attivo); l'assenza di
dipendenza dal DB è comunque confermata sia dal grep sia dal fatto che
l'intero `AppTest` gira leggendo solo `data/dashboard_export/`.

**Cosa resta manuale, deliberatamente**: dopo ogni sessione di aggiornamento
dati, l'utente rilancia `python -m src.data_processing.export_dashboard_data`
e fa commit/push dei Parquet aggiornati — nessun refresh automatico. Push su
GitHub e collegamento a Streamlit Community Cloud non ancora fatti (azione
visibile su servizio esterno, da fare solo su richiesta esplicita).

### Un solo comando per rilanciare analisi + export (2026-07-19)

Su richiesta dell'utente, nuovo `src/data_processing/refresh_dashboard.py`:
concatena i 6 script di `src/analysis/*.py` (`trend_analysis`,
`heatwave_stats`, `seasonal_analysis`, `spatial_analysis`,
`spatial_regression`, `validate_arpa`) e infine `export_dashboard_data.py`,
tutti richiamati via `import_module(...).main()` (nessuno richiede
argomenti). Ogni passo gira anche se uno precedente fallisce (es. ARPA vuota
non deve bloccare le analisi Open-Meteo); riepilogo finale + exit code
diverso da zero se qualcosa è fallito.

**Deliberatamente escluso**: `TRUNCATE`/`identify_heatwaves()` e `REFRESH
MATERIALIZED VIEW` sul database. Discusso esplicitamente con l'utente (che
non capiva la differenza, spiegata così): il `TRUNCATE` cancella e ricrea
dati, va lanciato solo quando si è sicuri che i nuovi dati siano pronti
(finora sempre valutato caso per caso, a volte anche due volte nello stesso
giorno) — automatizzarlo in uno script che gira sempre rischierebbe di
svuotare la tabella nel momento sbagliato. L'export invece è sola lettura:
nel peggiore dei casi produce uno snapshot vecchio, mai un danno. Restano
quindi manuali (da lanciare **prima** di `refresh_dashboard.py`, quando i
dati nel DB sono già pronti).

**Verificato per intero, non solo per lettura del codice**: eseguito
davvero contro il DB reale (177 comuni, 218 stazioni ARPA) invece di
assumere che i `main()` funzionassero solo perché non richiedono argomenti.
Il passo più lento è la STL (`seasonal_analysis`, ~25s/comune × 177 comuni,
oltre un'ora) — durante l'esecuzione osservati **due salti di ore nei
timestamp dei log senza che il processo si fermasse o fallisse** (18:54 →
23:31 e 23:42 → 00:05), quasi certamente il PC andato in sospensione/idle
per un periodo prolungato: il processo Python è sopravvissuto e ha ripreso
da solo al ritmo normale, prova indiretta ma concreta che lo script non
dipende da uno stato che si perde tra un'esecuzione e l'altra. Esito finale:
**7/7 passi completati, nessun fallimento**, `data/dashboard_export/`
rigenerata (69 MB, invariata nelle dimensioni). Due file sono cambiati
rispetto al commit precedente (`arpa_event_comparison_summary.parquet`,
`arpa_trend_comparison.parquet` — normale, `validate_arpa.py` è stato
rieseguito su dati che nel frattempo sono leggermente cambiati).

## Bug trovati eseguendo la dashboard per la prima volta (2026-07-15)

- **`ModuleNotFoundError: No module named 'components'`**: Streamlit
  esegue gli script con `exec()`, non con l'invocazione standard `python
  script.py` — quindi la cartella dello script **non** viene aggiunta
  automaticamente a `sys.path` come farebbe l'interprete normale. Fix:
  bootstrap esplicito (`sys.path.insert(0, ...)`) in cima a `Home.py`
  (allora `app.py`) e a ogni pagina in `pages/`, prima di importare da
  `components`.
- **`folium.GeoJson()` non accetta WKT grezzo**: passargli direttamente la
  stringa WKT letta dal DB fa sì che `folium`/`branca` provino ad aprirla
  come se fosse un percorso file (`OSError: Invalid argument`). Fix:
  `components/maps.py::wkt_to_geojson()` converte WKT → dict GeoJSON via
  `shapely.wkt.loads` + `shapely.geometry.mapping` prima di passarlo a
  `folium.GeoJson`.
- **`use_container_width` deprecato**: la versione di Streamlit installata
  (1.58.0) l'ha già superato come data di rimozione annunciata —
  sostituito con `width='stretch'` in tutte le occorrenze.
- **Processi Streamlit residui dopo la rinomina `app.py` → `Home.py`**:
  dopo il rename, l'utente continuava a vedere in browser
  `FileNotFoundError: dashboard\app.py` nonostante il server fosse stato
  riavviato puntando a `Home.py`. Causa: sessioni di verifica precedenti
  avevano lasciato **4 processi Streamlit avviati in background** ancora
  vivi sulla stessa porta 8501 (due dei quali puntavano ancora al vecchio
  `app.py`, cancellato) — il tentativo di stop di un turno precedente
  aveva chiuso solo un PID, non tutti. Diagnosticato con
  `Get-CimInstance Win32_Process | Where CommandLine -match streamlit`
  (mostra la riga di comando completa per PID, non solo il nome
  immagine), non riproducibile con `AppTest` (che non avvia un vero
  server HTTP). Risolto terminando tutti i processi trovati e
  riavviandone uno solo, verificato con
  `Get-NetTCPConnection -LocalPort 8501` che un solo PID fosse in
  ascolto.

## Dipendenze

Tutte già in `requirements.txt` (`streamlit`, `streamlit-folium`,
`folium`, `plotly`). **Allineate il 2026-07-15** alle versioni
effettivamente installate nel `.venv` (streamlit 1.58.0, non più 1.29.0
pinnato — vedi [Stato del Progetto](project-status.md) per l'elenco
completo del drift risolto in tutto `requirements.txt`). Le mappe
coropletiche aggiunte il 2026-07-15 usano `branca.colormap.LinearColormap`
(già presente come dipendenza transitiva di `folium`, non serve
aggiungerla a `requirements.txt`).

**`requirements-dashboard.txt` (2026-07-18)**: file separato, minimale, per
il deploy pubblico — vedi sezione "Nessuna connessione DB live" sopra per il
dettaglio completo (cosa include/esclude e perché). `requirements.txt`
resta invariato per l'uso locale della pipeline completa; entrambi
includono ora `pyarrow` (formato dei file in `data/dashboard_export/`).

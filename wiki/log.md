# Log della wiki

Log cronologico append-only. Ogni riga: data, azione, pagine toccate.

- **2026-07-04** — INGEST INIZIALE. Creata la wiki da zero seguendo il pattern
  Karpathy (https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
  applicato al progetto Heatwave Piemonte. Letti come sorgenti grezze:
  `README.md`, `PROJECT_SUMMARY.md`, tutto `docs/*.md`, `config.yaml`,
  `sql/01_init_database.sql`, `sql/02_common_queries.sql`,
  `src/data_acquisition/download_data.py`, `src/data_processing/clean_data.py`,
  `src/database/load_to_db.py`, `src/utils/{config,database}.py`, struttura
  cartelle reale (`find`). Create 10 pagine:
  project-overview, architecture, data-sources, data-model, etl-pipeline,
  config-reference, kpi-catalog, sql-queries, concepts, gis-maps, dashboard,
  project-status. Creato `CLAUDE.md` in root come livello schema. Rilevata
  discrepanza significativa tra documenti di pianificazione (che descrivono
  uno stato molto più avanzato, es. "1.7M record", "Production Ready") e
  codice reale (solo Settimana 1 parziale implementata; `dashboard/`,
  `tests/`, `src/analysis/`, `src/visualization/`, `qgis_projects/` vuote).
  Rilevato bug di import in `download_data.py`
  (`CopernicusERA5Downloader._create_cds_client` annota `-> cdsapi.Client`
  senza importare `cdsapi` a livello di modulo) — documentato in
  `pages/data-sources.md`, non corretto (fuori scope di questo task).

- **2026-07-04** — FIX + DOWNLOAD REALE. Corretto il bug di import in
  `src/data_acquisition/download_data.py:184`
  (`_create_cds_client` ora annota `-> Optional["cdsapi.Client"]`, forward
  reference stringa invece di riferimento diretto valutato a tempo di
  definizione classe). Verificato che il modulo si importa correttamente.
  Eseguito un download reale via Open-Meteo (`--years 2000:2025 --sources
  open_meteo`, escluso 2026 perché l'API storica rifiuta date future):
  primo tentativo riuscito solo per 3/8 province (Torino, Alessandria, Asti)
  a causa di rate limit `429` non gestito dallo script, con il vero errore
  nascosto da un secondo bug scoperto in corso d'opera — `config.yaml`
  (`logging.format`) usa sintassi `%(asctime)s` da stdlib `logging` mentre
  `src/utils/logger.py` usa loguru (sintassi `{time}`), quindi ogni riga di
  log stampava la stringa di formato letterale invece del messaggio reale.
  Aggiunto retry con backoff esponenziale (rispetta `Retry-After`, max 5
  tentativi) in `WeatherDataDownloader.download_historical_data` e sleep
  tra regioni portato da 1s a 3s in `download_all_regions`. Ri-eseguito il
  download: tutte le 8 province scaricate con successo, 75.976 righe totali
  in `data/raw/temperature_data.csv`, nessun valore nullo. Pagine aggiornate:
  `data-sources.md` (bug cdsapi risolto, nuovo bug logging documentato, bug
  rate-limit documentato+risolto, dati reali scaricati), `etl-pipeline.md`
  (sezione Extract aggiornata con retry/backoff e run reale),
  `project-status.md` (righe 1-2 della roadmap segnate fatte, aggiunto punto
  minore sul fix di `logging.format` ancora da fare). Bug di logging
  **non corretto** (fuori scope: non bloccava il download, solo la
  leggibilità dei log) — resta in cima ai "prossimi passi" come voce minore.

- **2026-07-04** — POPOLAMENTO `municipalities` CON DATI ISTAT REALI + SETUP DB.
  Sessione lunga, molti bug reali scoperti perché per la prima volta lo
  schema è stato eseguito su un database Postgres/PostGIS realmente vivo.

  **Dati**: trovato (ricerca web, verificato con HEAD HTTP) l'URL ufficiale
  ISTAT dei confini comunali (`.../confini_amministrativi/generalizzati/2026/
  Limiti01012026_g.zip`, sostituiva una pagina HTML non scaricabile in
  `config.yaml`). Riscritto `IstatGeodataDownloader.download_municipalities`
  in `download_data.py` per scaricare/estrarre lo shapefile, filtrare il
  Piemonte (`COD_REG==1`, 1180 comuni), leggerlo con `encoding='cp1252'`
  (altrimenti nomi accentati corrotti), calcolare `area_km2` nel CRS
  proiettato originale prima di riproiettare in 4326, e salvare
  `data/external/municipalities.csv` + `.geojson`. Scoperto un bug nel seed
  SQL: `provinces.istat_code` di Alessandria era `'001'`, duplicato di
  Torino (corretto in `'006'` in `sql/01_init_database.sql`, verificato
  contro lo shapefile ISTAT). Scoperta anche una curiosità dati: il comune
  istat_code `001168` si chiama letteralmente "None" (va letto con
  `keep_default_na=False` per non perderlo come NaN).

  **Config/secrets**: `.env` non aveva alcun effetto — `config.py` non
  chiamava mai `load_dotenv()` nonostante `python-dotenv` fosse già
  installato, e `get_database_url()` dava comunque precedenza al placeholder
  in `config.yaml` (tracciato in git) sulla variabile d'ambiente. Fixato:
  `load_dotenv()` aggiunto, precedenza invertita (env vars vincono).

  **Database locale**: il Postgres 16+PostGIS locale (già installato per
  questo progetto) aveva una password sconosciuta. Reset password via
  metodo standard "trust temporaneo" in `pg_hba.conf` — nel farlo, un mio
  comando PowerShell (`Set-Content -Encoding utf8`) ha introdotto un BOM
  UTF-8 a inizio file, mai notato subito, che ha fatto fallire silenziosamente
  ogni successivo restart del servizio per diversi tentativi (`FATALE:
  could not load pg_hba.conf`, mascherato da timeout SCM di Windows).
  Diagnosticato leggendo i log Postgres ed Event Viewer; risolto riscrivendo
  il file senza BOM. Il servizio Windows (`postgresql-x64-16`) non si è più
  riavviato correttamente da SCM dopo i tentativi falliti — usato `pg_ctl`
  direttamente (stop/start bypassando il Service Control Manager) come
  workaround; **il servizio Windows resta "Stopped"**, Postgres gira ma non
  come servizio: da sistemare in una sessione futura (probabile bisogno di
  riavviare il servizio da una sessione admin quando comodo).

  **Bug nello schema/loader, mai emersi prima perché mai eseguiti su un DB
  vivo**: (1) `initialize_schema()` usava `exec_driver_sql`, che passa
  sempre un dict di parametri a psycopg2 anche se vuoto, facendo interpretare
  il `%` letterale di `'% of data completeness'` come segnaposto — fix:
  esecuzione via cursore DBAPI grezzo; (2) `metadata.value` era `NOT NULL`
  ma il seed inserisce `NULL` per `last_etl_run` — rimosso il vincolo;
  (3) `municipalities.geometry` era `GEOMETRY(POLYGON,4326)` ma 74/1180
  comuni reali sono `MULTIPOLYGON` (exclavi) — cambiato a `MULTIPOLYGON`,
  insert avvolto in `ST_Multi()`; (4) tutti i `CREATE INDEX` mancavano di
  `IF NOT EXISTS` (a differenza delle `CREATE TABLE`), rompendo la
  ri-esecuzione dello script su un DB parzialmente inizializzato — aggiunto
  a tutte le 24 occorrenze. Rimossa anche la chiamata a
  `insert_sample_province()` da `main()` (inseriva un record fittizio
  "Test Comune Piemonte" nella tabella `provinces` reale).

  **Risultato finale verificato nel DB**: 8 province (codici ISTAT corretti),
  1180 comuni reali, 0 geometrie invalide (`ST_IsValid`).

  Pagine aggiornate: `data-sources.md`, `data-model.md`, `etl-pipeline.md`,
  `config-reference.md`, `project-status.md` (item 3 della roadmap segnato
  fatto, aggiunta voce minore su population/elevation mancanti).

- **2026-07-04** — CARICAMENTO `temperature` (PUNTO 4, ULTIMO BUCO DELLA
  PIPELINE). `src/data_processing/clean_data.py` **non era mai stato
  eseguibile**: da `validate_temperature` in poi il file aveva newline
  letterali (`\n` testuali) invece di righe vere, un `SyntaxError`
  bloccava l'import. Riscritto da capo preservando la logica (il contenuto
  era leggibile, solo "srotolato" su una riga fisica). Prima esecuzione
  reale su `data/raw/temperature_data.csv`: sopravvivevano solo 10 righe su
  75.976 — bug trovato in `apply_quality_flags`: `quality_flag` viene
  valorizzata da `validate_temperature`/`detect_outliers` solo per le righe
  sospette *prima* che la colonna esista, quindi pandas la crea con `NaN`
  per tutte le altre; il filtro `quality_flag < 2` scarta anche quelle
  (`NaN < 2` è `False`). Fix: `df['quality_flag'] = 0` esplicito prima di
  `validate_temperature`. Ri-eseguito: 75.976/75.976 righe mantenute, 10
  flaggate (ondata di freddo febbraio 2012, non errori).

  Scritto `DatabaseLoader.insert_temperature()` in `load_to_db.py` (batch
  insert via `psycopg2.extras.execute_values`). Discussione con l'utente
  sulla granularità: i dati Open-Meteo sono per provincia (1 stazione =
  il capoluogo), ma `temperature.municipality_id` è `NOT NULL` — scelto
  (con l'utente) di associare ogni riga al **comune capoluogo di
  provincia**, lasciando gli altri 1172 comuni senza dati (alternativa
  scartata: rendere `municipality_id` nullable per un "livello
  provinciale"). Trovata un'eccezione nella mappatura nome-capoluogo:
  la provincia "Verbano-Cusio-Ossola" ha come capoluogo il comune di
  "Verbania" (nome diverso dalla provincia, a differenza delle altre 7).

  **Risultato finale verificato nel DB**: 75.976 righe in `temperature`,
  8 comuni capoluogo, range 2000-01-01/2025-12-31, `quality_flag` 0/1
  coerente, nessun record scartato. La pipeline Extract→Transform→Load è
  ora completa ed eseguita end-to-end su dati reali per la prima volta.

  Pagine aggiornate: `etl-pipeline.md` (sezioni Transform e Load, bug
  critici documentati), `project-status.md` (item 4 segnato fatto, righe
  Settimana 2 aggiornate, prossimi passi ridefiniti attorno a
  `identify_heatwaves()`/analisi ora che i dati reali ci sono).

- **2026-07-12** — `identify_heatwaves()` E VISTE KPI SU DATI REALI.
  Prima di eseguire la funzione sui 75.976 record reali, rilettura attenta
  del codice PL/pgSQL in `sql/01_init_database.sql` ha rivelato due bug di
  correttezza mai emersi (la funzione non era mai stata eseguita su dati
  veri): (1) quando la sequenza di giorni caldi si interrompeva per
  **cambio comune** (non solo buco di date), l'`INSERT` usava
  `municipality_id`/`province_id` della riga **nuova** invece che di quella
  a cui l'ondata conclusa apparteneva; (2) **nessun flush finale** — se
  l'ultimo comune elaborato terminava la serie durante un'ondata attiva,
  quell'ultima ondata non veniva mai salvata. Corretti entrambi con
  variabili di tracking dedicate (`v_municipality_id`/`v_province_id`) e un
  controllo esplicito dopo il loop.

  Il fix ha introdotto temporaneamente un terzo bug: le nuove variabili si
  chiamavano quasi come le colonne selezionate, causando
  `ERRORE: riferimento a colonna ambiguo` — risolto aggiungendo un alias di
  tabella esplicito nella query interna (`FROM temperature t`).

  Prima esecuzione "riuscita" (nessun errore) ma con **0 righe inserite**
  in `heatwave_events`, nonostante 406 giorni reali sopra i 35°C nel
  dataset. Causa: la funzione era stata invocata via
  `db_manager.execute_query()`, che usa `engine.connect()` **senza
  `commit()`** — side effect (gli `INSERT` fatti dalla funzione) annullati
  silenziosamente alla chiusura della connessione (comportamento di
  SQLAlchemy 2.0 senza transazione esplicita). Fix: invocata dentro
  `with db_manager.engine.begin() as conn: ...` (commit automatico).
  Verificato con un conteggio indipendente via SQL (window function
  `ROW_NUMBER()` per individuare i gap di date): 51 ondate reali attese, 51
  trovate — coincidenza esatta, inclusa la storica ondata dell'agosto 2003.
  Documentato il gotcha `execute_query`-non-committa in `architecture.md`
  per evitare di ripeterlo con altre funzioni PL/pgSQL in futuro.

  Rinfrescate anche le viste materializzate `kpi_annual_by_municipality` e
  `kpi_annual_by_province` (erano vuote, calcolate quando `temperature` non
  aveva ancora dati): 208 righe ciascuna (8 comuni/province × 26 anni).

  **Risultato finale verificato nel DB**: `heatwave_events` 51 righe,
  `kpi_annual_by_municipality`/`kpi_annual_by_province` 208 righe ciascuna.
  Tutta la catena dati → schema → KPI/ondate è ora reale e verificata.

  Pagine aggiornate: `data-model.md` (sezione `heatwave_events`, viste
  materializzate, bug della funzione documentati), `architecture.md`
  (gotcha `execute_query`/commit), `project-status.md` (Settimana 2
  completata, prossimi passi ridefiniti attorno a analisi/dashboard).

- **2026-07-15** — `src/analysis/` IMPLEMENTATA ED ESEGUITA SU DATI REALI
  (PUNTO 1 DELLA ROADMAP POST-ETL). Prima esecuzione mai fatta di analisi
  statistica/spaziale sui dati reali caricati nelle sessioni precedenti.
  Installate nuove dipendenze non ancora presenti (`pymannkendall`,
  `scikit-learn`, `statsmodels`), aggiunte a `requirements.txt`.

  Scritti ed eseguiti 4 moduli:
  - `trend_analysis.py` — Mann-Kendall + regressione lineare per comune su
    `temp_mean_annual`. Risultato: 7/8 comuni con trend di riscaldamento
    significativo (p<0.05), +0.4/+1.0 °C/decade; Asti borderline (p=0.098).
  - `heatwave_stats.py` — backfill di `heatwave_events.intensity_index`/
    `mean_temp` (lasciati `NULL` da `identify_heatwaves()`, mai calcolati
    finora) + statistiche aggregate per comune/anno. 2003 e 2019 emergono
    come gli anni con più ondate (11 e 9), coerente con le ondate di
    calore europee note di quegli anni.
  - `seasonal_analysis.py` — STL decomposition (statsmodels) sulla serie
    giornaliera per comune. Ampiezza stagionale reale ~28-32°C.
  - `spatial_analysis.py` — Moran's I (implementato a mano, no
    `libpysal`/`esda`, con test di significatività via permutazione) +
    clustering K-means in zone climatiche. Documentato esplicitamente il
    limite: solo 8 unità spaziali disponibili (i comuni capoluogo) è sotto
    la soglia comunemente considerata minima per un'analisi spaziale
    robusta — risultati (I=-0.096, p=0.73; 3 cluster geograficamente
    sensati) presentati come illustrativi, non conclusivi.

  Due bug minori trovati e corretti durante l'esecuzione: (1) `AVG()` di
  PostgreSQL su colonne intere restituisce `NUMERIC`/`Decimal`, in
  conflitto con le colonne `float` nelle operazioni pandas — fix: cast
  `::float` nella query SQL; (2) una bozza iniziale di
  `seasonal_analysis.py` interpolava il nome del comune in un f-string
  SQL (valore comunque fidato, da una query interna, ma pattern da
  evitare) — corretto in query parametrizzata.

  Creata nuova pagina `statistical-analysis.md` con il dettaglio di tutti
  e 4 i moduli, risultati reali e caveat statistici. Aggiornate anche
  `concepts.md` (ogni concetto ora marcato "implementato" con il
  risultato reale), `kpi-catalog.md`, `index.md`, `project-status.md`
  (Settimana 3 aggiornata, prossimi passi ridefiniti attorno a mappe
  GIS/dashboard).

- **2026-07-15** — DASHBOARD STREAMLIT IMPLEMENTATA ED ESEGUITA. Scritta
  la dashboard (`dashboard/app.py` + 4 pagine in `pages/` + componenti
  condivisi in `components/`) sui dati reali già caricati e sui risultati
  di `src/analysis/`. Scostamento deliberato dal piano
  (`PROJECT_SUMMARY.md`): niente `pages/01_home.py` separato — `app.py`
  stesso è la home (convenzione standard Streamlit); niente
  `components/charts.py` — grafici scritti direttamente nelle pagine.

  Scoperti e risolti 3 bug reali alla prima esecuzione:
  1. `ModuleNotFoundError: No module named 'components'` — Streamlit
     esegue gli script con `exec()`, non con l'invocazione standard di
     Python, quindi la cartella dello script non finisce automaticamente
     in `sys.path`. Fix: bootstrap esplicito (`sys.path.insert`) in cima a
     `app.py` e a ogni pagina.
  2. `folium.GeoJson()` non accetta WKT grezzo — tentava di aprirlo come
     percorso file (`OSError: Invalid argument`). Fix:
     `components/maps.py::wkt_to_geojson()` (shapely WKT → dict GeoJSON).
  3. `use_container_width` deprecato nella versione di Streamlit installata
     (1.58.0, già oltre la data di rimozione annunciata) — sostituito con
     `width='stretch'` in tutte le occorrenze.

  **Verifica end-to-end senza browser**: un `curl` sulla porta 8501
  restituiva 200 OK ma non prova nulla (Streamlit è un'app client-rendered,
  il markup HTML iniziale è solo il "guscio" statico). Usato invece
  `streamlit.testing.v1.AppTest`, che esegue davvero lo script in-process:
  tutte e 5 le pagine eseguite senza eccezioni, contenuto reale verificato
  (metriche home: 75.976 righe, 2000-2025, 8/1180 comuni, 51 ondate;
  tabella trend con valori coincidenti con `output/trend_analysis.csv`).
  Infine avviata live (`streamlit run dashboard/app.py --server.headless
  true --server.port 8501`), raggiungibile su `http://localhost:8501`
  (health check `/_stcore/health` → 200).

  Pagine aggiornate: `dashboard.md` (riscritta, struttura reale + bug +
  metodo di verifica via `AppTest`), `project-status.md` (Settimana 3
  completata salvo QGIS, prossimi passi ridefiniti attorno alle mappe GIS
  come ultimo pezzo pianificato mancante), `index.md`.

- **2026-07-15** — MAPPE QGIS GENERATE ED ESEGUITE (ULTIMO PEZZO DI
  SETTIMANA 3). Trovato QGIS 3.44.12 già installato
  (`C:\Program Files\QGIS 3.44.12`), con `python-qgis-ltr.bat` (Python
  bundled con PyQGIS) e `qgis_process-qgis-ltr.bat` disponibili — quindi,
  come per la dashboard, non solo scritti i file ciecamente ma costruiti e
  **verificati con render offscreen** (`QT_QPA_PLATFORM=offscreen` +
  `QgsMapRendererParallelJob` → PNG), invece di limitarsi a consegnare file
  mai aperti.

  Scritto `qgis_projects/build_maps.py` (PyQGIS) per generare i 3 progetti
  pianificati in `PROJECT_SUMMARY.md`: `temperature_heatmap.qgz`,
  `hotspot_analysis.qgz`, `evolution_animation.qgz`. Sfondo comune: tutti i
  1180 comuni in grigio (da `municipalities`), con gli 8 comuni capoluogo
  reali evidenziati a colori sopra — stessa scelta di onestà sulla
  granularità già adottata in dashboard e analisi.

  **Due bug reali trovati e risolti, entrambi con fallimento silenzioso
  (nessun errore Python visibile)**:
  1. Le prime anteprime mostravano solo lo sfondo grigio, nessun comune
     colorato: il renderer referenziava campi come
     `spatial_analysis_temp_mean_avg`, assumendo che
     `QgsVectorLayerJoinInfo` aggiungesse un prefisso — ma con
     `setPrefix('')` i campi joinati mantengono il nome originale
     (`temp_mean_avg`). Trovato ispezionando `layer.fields()` prima/dopo
     il join.
  2. Il layer temporale (mappa 3, basato su una subquery SQL passata come
     `table=` in `QgsDataSourceUri`) risultava sempre invalido, con
     `layer.error()` completamente vuoto — nessun indizio dalle normali
     API Python. Diagnosticato solo collegando un handler al message log
     di QGIS (`QgsApplication.messageLog().messageReceived`), che ha
     rivelato che QGIS mette tra virgolette l'**intera subquery** come se
     fosse un unico nome di tabella, producendo un errore Postgres
     (`la relazione "(SELECT ... non esiste`) mai esposto a Python. Fix:
     creata una vista Postgres reale (`kpi_temporal_view`, script dedicato
     `qgis_projects/create_temporal_view.py`, eseguito col venv del
     progetto) invece della subquery inline — una vista in catalogo si
     comporta come qualunque tabella, senza ambiguità di parsing.

  **Verifica del filtro temporale**: renderizzati due frame (2000 e 2025)
  e confrontati visivamente — differiscono chiaramente (2025 uniformemente
  più rosso/caldo), confermando che il time slider funziona davvero e
  riflette il riscaldamento reale già trovato in `trend_analysis.py`, non
  solo che il layer esiste.

  **Limite scoperto e non risolvibile in questa sessione**: l'ambiente Qt
  offscreen non ha alcun font di sistema registrato
  (`QFontDatabase().families()` vuoto) — le etichette dei comuni appaiono
  come rettangoli tratteggiati nelle anteprime PNG invece che testo.
  Isolato il problema con un test `QPainter` puro (stesso risultato senza
  QGIS coinvolto), quindi non è un bug della configurazione delle
  etichette nel progetto — è un limite del backend di rendering headless.
  Le etichette restano correttamente configurate nel file `.qgz`; vanno
  confermate aprendo i progetti in QGIS Desktop (unico aspetto di questa
  sessione non verificabile in automatico).

  Pagine aggiornate: `gis-maps.md` (riscritta, stato reale + entrambi i
  bug + limite del font documentati), `project-status.md` (Settimana 3
  completa su tutti e 3 i pezzi principali — analisi, dashboard, mappe —
  prossimi passi ridotti a voci minori/rifiniture), `index.md`.

- **2026-07-15** — FIX PAGINA BIANCA IN QGIS DESKTOP. L'utente ha aperto i
  3 `.qgz` in QGIS Desktop e ha segnalato una pagina bianca (il render
  offscreen delle anteprime PNG non aveva rivelato il problema, perché
  imposta l'estensione solo su `QgsMapSettings`, transiente, non su ciò
  che viene effettivamente salvato nel progetto). Causa reale: `QgsProject
  .write()` non salva alcuna estensione di vista (`DefaultViewExtent`) a
  meno di impostarla esplicitamente — verificato ispezionando l'XML dentro
  il `.qgz` (nessun `<mapcanvas>`/`DefaultViewExtent` presente). Fix:
  nuova funzione `set_project_view_extent()` in `build_maps.py`, che
  imposta `project.viewSettings().setDefaultViewExtent(...)`
  sull'estensione combinata dei layer per ciascuno dei 3 progetti, prima
  di salvarli. Rieseguito `build_maps.py`; verificato che l'XML del
  `.qgz` ora contenga `DefaultViewExtent` coi confini reali del Piemonte
  (non più assente); anteprime PNG ri-verificate, invariate/corrette.

  Pagina aggiornata: `gis-maps.md` (nuovo bug documentato nella lista).

- **2026-07-15** — FIX ETICHETTE MANCANTI IN `evolution_animation.qgz`.
  L'utente ha confermato che i nomi dei comuni si vedono correttamente in
  `temperature_heatmap.qgz` e `hotspot_analysis.qgz` (font quindi OK in
  QGIS Desktop reale, il problema visto nelle anteprime era davvero solo
  dell'ambiente offscreen), ma non nel terzo file. Causa: non un bug di
  rendering, semplicemente `add_labels()` non era mai stata chiamata sul
  layer temporale in `build_evolution_animation()` — dimenticanza in fase
  di scrittura, non un difetto di configurazione. Fix: aggiunta la
  chiamata con espressione `"name" || ' (' || round("temp_mean_annual", 1)
  || '°C)'`, così la temperatura in etichetta cambia insieme al colore a
  ogni anno dell'animazione. Rieseguito `build_maps.py`; verificato
  leggendo l'XML del `.qgz` salvato che il nodo `<labeling type="simple">`
  sia ora presente (prima assente).

  Pagina aggiornata: `gis-maps.md`.

- **2026-07-15** — DASHBOARD RESA PIÙ LEGGIBILE PER NON ADDETTI AI LAVORI.
  Richiesta esplicita dell'utente: rendere il sito comprensibile anche a
  chi non conosce il progetto, non solo a chi ha letto la wiki. Aggiunto
  a tutte e 5 le pagine un riquadro introduttivo `st.expander("ℹ️ Come si
  legge questa pagina")` con spiegazioni in linguaggio semplice dei metodi
  usati (Mann-Kendall, regressione lineare, STL, K-means, indice di Moran,
  definizione di ondata di calore), più didascalie (`st.caption`) sotto le
  metriche e i grafici principali che ne riassumono il significato pratico
  invece di lasciare solo il numero/etichetta tecnica. Nella pagina Analisi
  Spaziale, l'indice di Moran ora ha anche un'interpretazione discorsiva
  (`st.success`/`st.info` a seconda della significatività), non solo il
  valore numerico. Nella pagina Download Dati, ogni file ha una
  descrizione di cosa contiene, non solo il nome tecnico. Nessuna modifica
  a query/logica dati — solo testo esplicativo. Verificato con
  `streamlit.testing.v1.AppTest` che tutte e 5 le pagine eseguano ancora
  senza eccezioni dopo le modifiche; server live riavviato su
  `localhost:8501`.

  Pagina aggiornata: `dashboard.md`.

- **2026-07-15** — DUE RIFINITURE MINORI: FIX LOGGING + ALLINEAMENTO
  REQUIREMENTS. Su richiesta dell'utente, risolte le due voci più rapide
  rimaste nella lista dei prossimi passi:
  1. `logging.format` in `config.yaml` corretto dalla sintassi stdlib
     `%(asctime)s...` (mai compatibile con loguru, bug noto da inizio
     wiki il 2026-07-04) alla sintassi loguru corretta — lo stesso valore
     già usato come default di fallback in `src/utils/logger.py`. Log di
     console e file finalmente leggibili; verificato con un test diretto.
  2. `requirements.txt` riallineato alle versioni realmente installate nel
     `.venv` (drift esistente sin dall'inizio del progetto: pandas
     2.1.4→3.0.3, numpy 1.26→2.4, scipy, sqlalchemy, geopandas, shapely,
     pyproj, requests, cdsapi, netCDF4, xarray, matplotlib, plotly,
     seaborn, folium, streamlit 1.29→1.58, streamlit-folium, pyyaml,
     python-dotenv, tqdm, loguru, pytest, pytest-cov, black, flake8, mypy,
     pylint — praticamente ogni pacchetto). Verificato `pip check`: nessun
     conflitto nell'ambiente attuale.

  Pagine aggiornate: `data-sources.md` (bug logging segnato risolto),
  `dashboard.md` (nota sul drift dei requirements aggiornata),
  `project-status.md` (entrambe le voci rimosse dalla lista prossimi
  passi, aggiunta nota sul fix).

- **2026-07-15** — ESTENSIONE A 44 COMUNI (RENDERE MORAN'S I/CLUSTERING
  ROBUSTI). Richiesta esplicita dell'utente: il campione di 8 comuni per
  le analisi spaziali era troppo piccolo (sotto la soglia comune di 20-30
  unità). Concordato con l'utente (via domande di scoping): estendere solo
  le temperature (non i metadati demografici, rimandati), con ~30-40
  comuni extra.

  **Selezione**: nuovo script `src/data_acquisition/download_extra_municipalities.py`
  — campionamento "farthest-point" per provincia (sceglie comuni che
  massimizzano la distanza minima dai punti già presenti, per coprire zone
  diverse invece di ammassarsi), 36 comuni extra allocati proporzionalmente
  alla dimensione di ciascuna provincia (9 Torino, 7 Cuneo, 6 Alessandria,
  4 Asti, 3 Novara, 3 Vercelli, 2 Biella, 2 Verbano-Cusio-Ossola).

  **Download**: refactoring di `WeatherDataDownloader.download_historical_data()`
  in `download_data.py` — estratta la logica di retry/backoff in un nuovo
  metodo `download_for_coordinates(name, lat, lon)` che accetta coordinate
  arbitrarie, non solo gli 8 capoluoghi hardcoded. 31/36 comuni scaricati al
  primo giro; 5 falliti per `ConnectionResetError`/TLS reset (non un `429`,
  quindi non coperto dal retry esistente) — ri-scaricati con una seconda
  passata mirata. Risultato: 36/36, 341.892 righe.

  **Bug di encoding storico scoperto per caso**: durante il download, 2 nomi
  (Rorà, Cavaglià) sono usciti corrotti. Indagine ha rivelato che il fix di
  encoding del 2026-07-04 (`encoding='cp1252'` per leggere lo shapefile
  ISTAT) era **sbagliato fin dall'inizio** — verificato a livello di byte
  (`nome.encode('utf-8')`) che produceva una doppia codifica UTF-8 per
  ogni nome accentato, e che la verifica originaria (stampa a terminale)
  era stata ingannata da un mojibake che sembrava corretto per coincidenza.
  Il file `.dbf` ISTAT è in realtà UTF-8, non cp1252. Corretti: lo script
  (`encoding='utf-8'`), i 28 comuni su 1180 già corrotti nel DB (100% di
  quelli con caratteri accentati, `UPDATE` via `istat_code` come chiave
  stabile), e `data/external/municipalities.csv` (rigenerato).

  **Pulizia**: `DataCleaner` riusato senza modifiche (raggruppa per
  colonna `province`, che qui contiene il nome del comune — funziona
  perché ogni nome è univoco tra i 36 selezionati). 341.892/341.892 righe
  mantenute, 670 outlier statistici (prevalentemente comuni alpini).

  **Caricamento**: nuovo metodo `insert_temperature_for_municipalities()`
  in `load_to_db.py` (variante che usa `municipality_id` già noto, non
  serve risolvere il capoluogo per nome). Temperature totali: 417.868
  righe, 44 comuni.

  **Ricalcolo a valle**: `identify_heatwaves()` non è idempotente —
  `TRUNCATE TABLE heatwave_events` prima di rieseguirla (sicuro, dato
  interamente derivato) per evitare di duplicare le 51 ondate già trovate.
  Risultato: 145 ondate su 44 comuni. Viste materializzate rinfrescate
  (`kpi_annual_by_municipality` ora 1144 righe). Rieseguiti tutti e 4 i
  moduli di `src/analysis/` (nessuna modifica di codice necessaria, tranne
  aggiornare testo/commenti hardcoded su "8 comuni" in `spatial_analysis.py`).

  **Risultato più significativo**: Moran's I passa da **-0.096 (p=0.732,
  non significativo, n=8)** a **0.101 (p=0.002, statisticamente
  significativo, n=44)** — i comuni geograficamente vicini hanno
  temperature realmente più simili di quanto atteso per caso. Il
  clustering K-means è ora visivamente nitido: cluster alpino (3.8°C,
  margini montani nord/sud-ovest), cluster di pianura calda (12.9°C,
  centro-est), cluster intermedio (11.1°C) — confermato anche visivamente
  nella mappa QGIS rigenerata.

  **Rigenerato tutto a valle**: i 3 progetti QGIS (`build_maps.py`,
  verificati con render PNG — pattern geografico dei cluster ora molto più
  leggibile con 44 punti invece di 8) e tutte e 5 le pagine dashboard
  (testi con "8 comuni" aggiornati a "44 comuni" in `app.py`,
  `03_analisi_spaziale.py`, `04_ondate_di_calore.py`,
  `components/queries.py`; il messaggio di Moran's I ora mostra
  `st.success` invece di `st.info`, dato che il risultato è diventato
  significativo). Verificato con `AppTest`, server live riavviato.

  Bug minore incontrato e corretto: `UnicodeEncodeError` ripetuto su
  console Windows per i caratteri "✓"/"✗" nei log (cp1252 non li supporta)
  — fix in `src/utils/logger.py` con `sys.stdout.reconfigure(encoding=
  'utf-8')`.

  Pagine aggiornate: `data-sources.md`, `etl-pipeline.md`, `data-model.md`,
  `statistical-analysis.md` (riscrittura sostanziale della sezione Moran's
  I/clustering), `gis-maps.md`, `dashboard.md`, `project-status.md`.

- **2026-07-15** — TEST UNITARI (`tests/`). Su richiesta esplicita
  dell'utente, creata la prima suite di test del progetto (`tests/` era
  vuota da inizio wiki). Creati `tests/__init__.py`, `pytest.ini`
  (`testpaths = tests`), e 3 file di test: `test_data_cleaning.py` (15
  test su `DataCleaner`, `src/data_processing/clean_data.py`),
  `test_analysis.py` (11 test sulle funzioni pure di `src/analysis/*.py`:
  Mann-Kendall, regressione lineare, haversine, pesi spaziali, indice di
  Moran, clustering K-means, aggregazioni ondate di calore), `test_config.py`
  (5 test su `Config.get()`/`get_database_url()`, incluso un test di
  regressione sulla precedenza env-vars/yaml già risolta il 2026-07-04).
  Scelta deliberata: solo unit test puri, nessuno tocca DB o rete (dati
  sintetici costruiti a mano) — l'intera suite gira in ~5 secondi.

  **Bug reale trovato dalla suite alla prima esecuzione** (non un test
  scritto per confermare un comportamento noto, ma uno che ha effettivamente
  fallito): `test_bad_rows_are_dropped_good_rows_survive`, un dataset
  sintetico con una riga fuori range fisico (`temp_max=999`), falliva
  perché quella riga sopravviveva alla pipeline invece di essere scartata.
  Causa: in `DataCleaner.detect_outliers()`
  (`src/data_processing/clean_data.py`), che gira *dopo*
  `validate_temperature()` (la quale aveva già segnato la riga
  `quality_flag=2`, bad), l'assegnazione del flag IQR (`quality_flag=1`,
  suspect) era incondizionata — **declassava** a 1 anche righe già a 2,
  che poi sopravvivevano ad `apply_quality_flags()` (scarta solo `>= 2`).
  Fix: `df.loc[is_outlier & (df['quality_flag'] < 2), 'quality_flag'] = 1`
  (declassa solo se il flag attuale è ancora `< 2`). Verificato che il bug
  non ha mai avuto impatto sui dati reali già caricati (0 righe fuori range
  fisico sia in `temperature_data.csv` che in `temperature_data_extra.csv`,
  quindi la precondizione del bug — riga contemporaneamente bad e outlier
  IQR — non si è mai verificata finora), ma resta un bug di correttezza
  reale ora corretto e coperto da test di regressione.

  Ri-eseguita l'intera suite dopo il fix: 31/31 test passati. Eseguita
  anche con `--cov=src.data_processing --cov=src.analysis
  --cov=src.utils.config --cov-report=term-missing`: 86% di copertura su
  `clean_data.py`, 57% complessivo sui moduli inclusi nel report (atteso,
  dato che le funzioni che leggono da DB/rete non sono testate per scelta).

  Creata nuova pagina `testing.md` (cosa è coperto, il bug trovato/corretto
  in dettaglio, limiti espliciti — nessun test per `load_to_db.py`,
  `download_data.py`, `seasonal_analysis.py`, `src/visualization/`).
  Aggiornate `etl-pipeline.md` (sezione Transform, nota su ordine
  validate/detect_outliers e bug corretto), `index.md` (nuova sezione
  "Qualità del codice"), `project-status.md` (riga "Test unitari" in
  Settimana 3 segnata fatta con dettaglio, punto 6 dei prossimi passi
  segnato fatto).

- **2026-07-15** — AMPLIAMENTO CONTENUTO DELLE 3 PAGINE DI ANALISI DELLA
  DASHBOARD + FILTRI GLOBALI. Su richiesta esplicita e dettagliata
  dell'utente (specifica puntuale per ciascuna pagina + requisiti
  trasversali di UI/UX), ampliato sostanzialmente il contenuto di
  `02_analisi_temporale.py`, `03_analisi_spaziale.py`,
  `04_ondate_di_calore.py`, oltre a `app.py` (home) e a due nuovi moduli
  condivisi.

  **Nuovi componenti condivisi**:
  - `components/constants.py` — palette coerente (scala sequenziale
    `RdYlBu_r` per temperature assolute, divergente `RdBu_r` centrata sullo
    zero per trend/anomalie, da non confondere tra loro), soglie fasce
    altitudinali (300/700 m), set dei capoluoghi, valori di riferimento
    nazionale/globale (IPCC AR6, ISPRA — dichiarati come letteratura, non
    calcolati dal progetto).
  - `components/filters.py` — sidebar comune (intervallo anni + provincia),
    persistita tra le pagine via `st.session_state` (Streamlit esegue ogni
    pagina come script indipendente, i widget non sono condivisi
    automaticamente).
  - `components/heatwave_definitions.py` — `identify_heatwaves_percentile()`,
    definizione alternativa di ondata di calore a soglia percentile
    (relativa al singolo comune), usata solo a scopo di confronto
    metodologico (vedi decisione sotto).

  **Decisione di scoping 1 — elevazione reale**: la richiesta di un
  confronto per fascia altitudinale (pianura/collina/montagna) richiedeva
  `municipalities.elevation_m`, mai popolato (sempre `NULL`, voce aperta in
  `project-status.md` da settimane). Chiesto esplicitamente all'utente se
  scaricare il dato reale o mostrare un placeholder "non disponibile" —
  scelto il dato reale. Scritto `src/data_acquisition/fetch_elevation.py`:
  centroide di ciascun comune via PostGIS (`ST_Centroid`), interrogata la
  Open-Meteo Elevation API (stessa piattaforma delle temperature, nessuna
  chiave, endpoint diverso: `api.open-meteo.com/v1/elevation`) in
  un'unica richiesta batch per i 44 comuni con dati, risultati scritti in
  `municipalities.elevation_m`. Eseguito realmente: da Torino (256 m) a
  Formazza (2250 m), coerente con la geografia nota del Piemonte.

  **Decisione di scoping 2 — definizione di ondata di calore**: la
  richiesta chiedeva di "implementare una funzione per identificare le
  ondate di calore" con soglia percentile. Il progetto ha già una
  definizione canonica (`identify_heatwaves()` nel DB, soglia fissa
  35°C/3gg) usata ovunque nel resto del sito (145 ondate in home,
  statistiche per comune, mappe QGIS) — sostituirla avrebbe reso
  incoerenti tutti quei numeri. Scelta: la soglia percentile è
  implementata come funzione pura, usata **solo** nel tab "Dettaglio
  tecnico" della pagina Ondate di Calore come confronto illustrativo per
  il comune selezionato, senza toccare il database.

  **Estensione a `heatwave_stats.py`**: `frequency_by_year()` ora include
  anche `avg_duration_days`/`avg_intensity` per anno (prima solo il
  conteggio), necessario per il grafico a barre a doppio asse richiesto
  nella pagina Ondate di Calore. Rieseguito, CSV rigenerato.

  **Contenuto aggiunto per pagina** (dettaglio completo in
  `wiki/pages/dashboard.md`): Analisi Temporale — anomalie con baseline
  configurabile, confronto stagionale (4 stagioni meteorologiche), boxplot
  per quinquennio, widget di confronto con letteratura, tab
  Panoramica/Dettaglio tecnico; Analisi Spaziale — mappa coropletica per
  provincia (confine reale via `ST_Union` PostGIS su tutti i 1180 comuni),
  mappa del trend per comune (colormap divergente), fasce altitudinali,
  isola di calore urbana (Torino vs comuni rurali della sua provincia),
  tab Panoramica/Dettaglio tecnico (cluster K-means e Moran's I spostati
  qui); Ondate di Calore — conteggio cumulato, mappa di concentrazione
  geografica, heatmap "calendario" (anno × giorno dell'anno), confronto
  soglia percentile; Home — 3 card di navigazione (`st.page_link`) al
  posto dei link testuali, sidebar filtri applicata anche a mappa e
  tabella trend esistenti.

  **Verifica**: tutte le pagine compilate (`py_compile`) e verificate con
  `streamlit.testing.v1.AppTest`, incluse esecuzioni con stati non
  di default (provincia Torino esclusa dal filtro → ramo isola di calore
  "dati insufficienti"; intervallo di un solo anno → ramo pendenza "n/d";
  comune di montagna con soglia percentile diversa) — nessuna eccezione in
  nessun caso. Server live riavviato e verificato (`/_stcore/health` → 200).

  Pagine aggiornate: `dashboard.md` (riscrittura sostanziale), `data-model.md`
  (`elevation_m` popolato per i 44 comuni), `data-sources.md` (nuovo
  endpoint Open-Meteo Elevation API), `statistical-analysis.md`
  (`frequency_by_year()` estesa), `project-status.md`.

- **2026-07-15** — RINOMINATA LA PAGINA PRINCIPALE `app.py` → `Home.py`.
  Richiesta esplicita dell'utente: "dobbiamo trovare un altro nome per la
  pagina principale, non si può chiamare app". Rinominato con `git mv`
  (storia Git preservata) `dashboard/app.py` → `dashboard/Home.py`, che è
  anche la convenzione più diffusa nelle app Streamlit multipage (più
  descrittivo di un generico "app"). Aggiornati i riferimenti nel
  docstring del file stesso e in `dashboard/components/__init__.py`.

  **Non toccati** `README.md`/`PROJECT_SUMMARY.md`/`docs/*.md`: per
  `CLAUDE.md` sono sorgenti di pianificazione immutabili, quindi citano
  ancora `streamlit run dashboard/app.py` — ora stale, comando corretto
  `streamlit run dashboard/Home.py`. Le voci storiche di questo stesso log
  che citano `app.py` (2026-07-15, sessioni precedenti) non sono state
  riscritte: erano corrette nel momento in cui sono state scritte (il file
  si chiamava davvero così), coerente con la natura append-only di questo
  log.

  Verificato con `streamlit.testing.v1.AppTest` sul nuovo path (nessuna
  eccezione), server live riavviato su `dashboard/Home.py`
  (`/_stcore/health` → 200).

  Pagina aggiornata: `dashboard.md` (percorsi, nota sulla rinomina,
  chiarimento sulla staleness dei documenti di pianificazione).

- **2026-07-15** — PULIZIA PROCESSI STREAMLIT RESIDUI. Dopo il rename
  `app.py` → `Home.py`, l'utente segnalava di vedere ancora in browser
  `FileNotFoundError: dashboard\app.py` nonostante il server fosse stato
  riavviato. Diagnosticato con `Get-CimInstance Win32_Process | Where
  CommandLine -match streamlit` (mostra la command line completa per PID):
  **4 processi Streamlit** erano rimasti vivi sulla porta 8501 da sessioni
  di verifica precedenti, due dei quali puntavano ancora al vecchio
  `app.py` — un tentativo di stop precedente ne aveva chiuso solo uno.
  Windows permetteva a più processi di restare "in ascolto" sulla stessa
  porta contemporaneamente (visibile con più righe `LISTENING` in
  `netstat`), quindi il browser si collegava a caso a uno dei quattro.
  Risolto terminando tutti i PID trovati e avviandone uno solo pulito,
  verificato con `Get-NetTCPConnection -LocalPort 8501` (un solo
  `OwningProcess`).

  Pagina aggiornata: `dashboard.md` (nuovo bug documentato nella lista).

- **2026-07-15** — ETICHETTE MANN-KENDALL LEGGIBILI + TEMA/RIFINITURE
  ESTETICHE. Due richieste in sequenza dell'utente sulla stessa area:
  prima "perché no trend?" (la stringa grezza `'no trend'` di
  `pymannkendall` si legge come "clima stabile", mentre significa "il test
  non trova abbastanza evidenza di un trend con 26 anni di dati" — un
  limite del test, non un fatto sul clima), poi "estetica bruttissima,
  non si vede nemmeno per intero 'nessun trend chiaro', viene tagliato".

  **Etichette leggibili**: aggiunta `format_mk_trend()` +
  `MK_TREND_LABELS` in `components/constants.py`
  (`increasing`→"📈 In aumento", `decreasing`→"📉 In diminuzione",
  `no trend`→"🔍 Nessun trend chiaro"), applicata ovunque appare
  `mk_trend`: metrica in alto e tab Dettaglio tecnico di
  `02_analisi_temporale.py`, tabella comparativa in `Home.py`. Bug in
  corso d'opera: dimenticato l'import di `format_mk_trend` in `Home.py`
  (`NameError` alla prima esecuzione, segnalato dall'IDE) — l'utente ha
  chiesto di fermarsi per capire cosa stessi facendo (interruzione
  legittima, non un errore da correggere silenziosamente); spiegato lo
  stato e, con l'ok esplicito a continuare, sistemato l'import mancante.

  **Causa reale del testo tagliato**: non un limite delle etichette
  scelte, ma CSS di `st.metric` (`white-space: nowrap` + `text-overflow:
  ellipsis` sul valore, pensato per numeri corti) che troncava qualunque
  valore testuale più lungo della colonna — capitava anche a nomi di
  comune come "Verbano-Cusio-Ossola" nelle metriche della pagina Analisi
  Spaziale, non solo alle nuove etichette. Fix mirato in nuovo
  `components/styling.py::inject_custom_css()`: `white-space: normal` sul
  selettore `[data-testid="stMetricValue"]`, così il testo va a capo
  invece di sparire. Il selettore è stato **verificato esistere davvero**
  in Streamlit 1.58.0 (grep nei bundle JS installati in
  `.venv/Lib/site-packages/streamlit/static/`), non indovinato dalla
  documentazione generica.

  **Tema**: creato `.streamlit/config.toml` (nuovo, prima assente) con un
  tema Streamlit nativo invece di CSS sparso — palette coerente (blu
  `#2563eb` primario), supporto chiaro/scuro, angoli arrotondati
  (`baseRadius`), bordo sui widget, `chartCategoricalColors` allineata a
  `components/constants.py`. Tutte le chiavi usate sono state verificate
  una per una contro `.venv/Lib/site-packages/streamlit/config.py`
  dell'installazione reale (alcune, come `baseRadius`/`showWidgetBorder`/
  `chartCategoricalColors`/`[theme.dark]`, sono relativamente recenti e
  non garantite in versioni più vecchie di Streamlit). Deliberatamente
  **non** cercati selettori CSS per le card della home
  (`st.container(border=True)`): Streamlit le renderizza con classi
  generate dinamicamente (`st-emotion-cache-*`), non un `data-testid`
  stabile — il loro stile arriva comunque dal tema (`baseRadius`/
  `borderColor`), senza bisogno di CSS fragile.

  **Verifica**: `py_compile` + `AppTest` su tutte le pagine (nessuna
  eccezione); server riavviato per far effetto (i cambi a
  `config.toml` richiedono un riavvio completo, non li applica l'hot
  reload di Streamlit) e verificato un solo processo in ascolto sulla
  porta 8501.

  Pagina aggiornata: `dashboard.md` (nuove sezioni "Etichette leggibili
  per l'esito di Mann-Kendall" e "Tema e rifiniture estetiche", struttura
  cartelle aggiornata con `styling.py` e `.streamlit/config.toml`).

- **2026-07-15** — BASELINE DELLE ANOMALIE: DA CONFIGURABILE A FISSA +
  TESTO ESPLICATIVO. L'utente ha chiesto a cosa servissero i due
  `number_input` "Inizio baseline"/"Fine baseline" nella pagina Analisi
  Temporale; dopo la spiegazione, ha fatto notare che lasciarla
  configurabile non ha senso per lo scopo della pagina (capire il
  fenomeno, non esplorare scenari) e ha chiesto un parere esplicito prima
  di procedere. Confermato d'accordo con l'osservazione: rimossi i due
  widget in `02_analisi_temporale.py`, baseline ora fissa al primo
  decennio disponibile per il comune selezionato (non varia più per
  scelta dell'utente, resta scelta di continuità coi commenti nel codice
  già presenti). Sostituita la breve didascalia con un paragrafo esplicito
  che copre, nell'ordine: cos'è un'anomalia, come si calcola, perché
  quella baseline e non un'altra (dato che 1961-1990/1991-2020 — i
  riferimenti convenzionali in climatologia — non sono disponibili, dato
  che la serie parte dal 2000), come leggere le barre rosse/blu.
  Aggiornata anche la nota di metodologia nel tab Dettaglio tecnico dello
  stesso file (non più "modificabile a mano").

  Verificato con `py_compile` + `AppTest` (nessuna eccezione); il server
  live ha ricaricato la modifica da solo (a differenza del tema, un
  cambio a un file `.py` non richiede riavvio).

  Pagina aggiornata: `dashboard.md` (nuova sezione "Baseline delle
  anomalie: da configurabile a fissa").

- **2026-07-15** — TORINO COME COMUNE DI DEFAULT + FIX `NameError` DA
  MODIFICA MANUALE. Due interventi rapidi in sequenza sulla pagina Analisi
  Temporale. (1) L'utente ha chiesto che alla prima apertura della pagina
  il comune preselezionato fosse Torino invece del primo in ordine
  alfabetico (Acceglio): aggiunto `index=names.index('Torino')` (con
  fallback a `0` se assente dal filtro provincia attivo) allo `st.selectbox`
  — verificato con `AppTest` che `sb.value == 'Torino'`. (2) L'utente ha
  poi modificato di sua iniziativa il testo esplicativo della baseline
  (espandendolo, in modo migliore), ma introducendo per errore tre nomi di
  variabili mai definiti nel file (`anno_inizio_baseline`,
  `anno_fine_baseline`, `anno_corrente` — copiati probabilmente da una
  bozza con nomi diversi da quelli usati nel codice reale,
  `baseline_years_available`/`baseline_end`/`last_year`), causando un
  `NameError` che impediva l'esecuzione dell'intera pagina. Diagnosticato
  in un secondo con `AppTest` (traceback completo con numero di riga
  esatto), corretto sostituendo i tre nomi con quelli reali senza toccare
  il testo. Verificato che l'intera pagina esegua di nuovo senza eccezioni.

- **2026-07-15** — OPZIONE AGGREGATA "PIEMONTE" NELLA PAGINA ANALISI
  TEMPORALE. Richiesta esplicita dell'utente: poter calcolare l'intero
  Piemonte (non solo un comune alla volta) sulla base dei dati già
  disponibili. Aggiunta una voce in cima al selettore "Comune":
  `🌍 Piemonte — media di N comuni filtrati` (N riflette il filtro
  provincia della sidebar, non è fisso a 44) — selezionandola, ogni
  grafico/metrica della pagina si ricalcola sulla **media aritmetica non
  pesata** dei comuni filtrati invece che su un singolo comune, con un
  `st.info` che chiarisce esplicitamente non essere una stima ufficiale
  della temperatura regionale (mancano pesi per area/popolazione e la
  copertura è solo 44/1180 comuni).

  **Nuove query** in `components/queries.py`: `get_daily_temperature_aggregate()`
  (media giornaliera via `AVG()` SQL su `temperature`, filtrata per lista
  di comuni con `IN` a parametro espandibile — `bindparam(..., expanding=True)`,
  necessario perché SQLAlchemy non accetta di default una lista Python come
  singolo parametro `:names` in una clausola `IN`) e
  `get_seasonal_decomposition_aggregate()` (STL calcolata al volo con la
  stessa funzione pura `decompose()` di `src/analysis/seasonal_analysis.py`,
  dato che non esiste un CSV precalcolato per un aggregato che non
  corrisponde a un singolo comune).

  **Trend canonico per l'aggregato**: `trend_analysis.csv` ha una riga per
  comune, non per un aggregato arbitrario — per l'opzione Piemonte,
  Mann-Kendall e regressione sull'intero periodo sono ricalcolati al volo
  importando direttamente `mann_kendall_trend()`/`linear_trend()` da
  `src/analysis/trend_analysis.py` (stesse funzioni pure usate per
  generare il CSV), non reimplementati da capo — garantisce identica
  metodologia tra CSV precalcolato e calcolo al volo. Introdotto un dict
  `trend_info`/flag `has_trend_info` che unifica l'accesso ai risultati
  (proveniente da una riga di CSV o da un calcolo fresco) in tutto il
  resto della pagina, senza duplicare la logica delle metriche/tab.

  **Verifica**: `AppTest` sia con selezione di default (Torino) sia con
  l'aggregato Piemonte selezionato (nessuna eccezione in entrambi i casi),
  ripetuto anche con il filtro provincia sidebar ristretto a una sola
  provincia (Cuneo, 8 comuni) per controllare che l'aggregato si adatti
  correttamente al sottoinsieme filtrato (trend Mann-Kendall "in aumento",
  p=0.0011, pendenza periodo selezionato +0.50°C/decade — risultato
  plausibile, non verificato però contro un calcolo indipendente esterno).

  Pagina aggiornata: `dashboard.md` (nuova sezione "Opzione aggregata
  'Piemonte'" dentro la descrizione della pagina Analisi Temporale).

- **2026-07-15** — OPZIONE "PIEMONTE" SPOSTATA IN UNA CHECKBOX SEPARATA.
  L'utente ha chiesto una casella a parte per selezionare l'intero
  Piemonte, invece che una voce in cima allo stesso menu a tendina dei
  comuni. Rimossa la voce `🌍 Piemonte — media di N comuni filtrati` dalle
  opzioni di `st.selectbox`; aggiunta una `st.checkbox("🌍 Intero
  Piemonte")` in una colonna a fianco, che quando attiva disabilita (non
  nasconde) lo `st.selectbox` del comune — scelta per rendere visibile
  che le due scelte sono mutuamente esclusive, senza far scomparire un
  controllo che l'utente potrebbe cercare. `is_aggregate` ora viene
  direttamente dalla checkbox invece che da un confronto testuale con
  un'etichetta placeholder nella lista. Aggiustato un riferimento residuo
  alla vecchia costante `AGGREGATE_LABEL` (rimossa) in favore di
  `subject_label`. Verificato con `AppTest`: selectbox abilitato/Torino
  selezionato di default, disabilitato e pagina ricalcolata sull'aggregato
  quando la checkbox viene attivata, nessuna eccezione in nessuno dei due
  stati.

  Pagina aggiornata: `dashboard.md` (sezione "Opzione aggregata
  'Piemonte'" corretta per riflettere la checkbox invece della voce nel
  menu a tendina).

- **2026-07-15** — FILTRI: DA SIDEBAR GLOBALE A WIDGET INLINE PER PAGINA.
  L'utente ha segnalato che i filtri nella sidebar sembravano inutili
  ("non so cosa possiamo aggiungere a lato") e ha chiesto di rimuoverli,
  mettendoli solo nelle sezioni dove servono davvero. Rimossa
  `render_sidebar_filters()` da `components/filters.py` e da ogni pagina;
  sostituita con due funzioni pensate per essere richiamate inline, con
  una `key` univoca per pagina (non serve più gestire `st.session_state` a
  mano: senza uno stato condiviso tra pagine, Streamlit persiste da solo
  il valore di un widget tramite `key` per tutta la sessione):
  `render_year_range_filter(key)` e `render_province_filter(key)`.

  **Decisioni pagina per pagina** (non un'applicazione meccanica a tutte):
  - `Home.py`: nessun filtro — rimossi `provinces`/`year_start`/`year_end`
    e i due `.isin(provinces)` che filtravano mappa e tabella trend;
    mostra sempre tutti i 44 comuni (una pagina di overview non trae
    beneficio da un filtro).
  - `02_analisi_temporale.py`: tenuto solo l'intervallo anni (l'unico
    usato davvero: regressione, anomalie, stagioni, boxplot), spostato
    sotto la riga comune/checkbox Piemonte, con didascalia che chiarisce
    cosa filtra e cosa no (Mann-Kendall/STL restano sull'intero periodo).
    Rimosso il filtro provincia: serviva solo a restringere la lista dei
    44 comuni nel menu a tendina, beneficio marginale — la lista ora è
    sempre completa (`get_municipality_names_with_data()`).
  - `03_analisi_spaziale.py` e `04_ondate_di_calore.py`: tenuti entrambi i
    filtri (anni e provincia), spostati inline in due colonne in cima alla
    pagina — qui hanno un uso reale e diretto (mappe coropletiche, fasce
    altitudinali, isola di calore, mappa di concentrazione ondate,
    frequenza/intensità per periodo).
  - `05_download_dati.py`: invariata, nessun filtro (i CSV scaricabili
    sono completi, un filtro non avrebbe effetto).

  Verificato con `AppTest` su tutte le pagine (nessuna eccezione), incluso
  con stati non di default (provincia ristretta a "Torino" e intervallo
  anni ridotto a un solo anno su Analisi Spaziale/Ondate di Calore).
  Server live verificato ancora in salute dopo le modifiche.

  Pagina aggiornata: `dashboard.md` (sezione "Filtri: da sidebar globale a
  inline per pagina" riscritta, struttura cartelle e descrizioni delle
  singole pagine aggiornate per rimuovere i riferimenti alla sidebar).

- **2026-07-16** — LEGENDA A FASCE PER LE MAPPE DI ANALISI SPAZIALE.
  Richiesta esplicita dell'utente: per ogni colore delle mappe, indicare
  range numerico e gravità. Le due mappe (temperatura media per provincia,
  velocità di riscaldamento per comune) usavano `branca.colormap.LinearColormap`
  senza alcuna legenda visibile — l'utente doveva indovinare cosa
  rappresentasse una sfumatura di colore. Aggiunta
  `components/maps.py::render_gradient_legend()`: non la legenda
  automatica di branca (`colormap.add_to(m)`, un gradiente continuo con
  solo min/max etichettati), ma una legenda testuale a 5 fasce discrete —
  per ciascuna, uno swatch con il colore realmente restituito dalla
  colormap al centro della fascia, il range numerico e un'etichetta di
  gravità esplicita:
  - Mappa temperatura: "Più fresco" → "Più caldo" (°C).
  - Mappa trend: "Raffreddamento" → "Riscaldamento rapido" (°C/decade,
    centrata sullo zero come la mappa).

  Le etichette non sono generiche: riusano esattamente la stessa istanza
  di colormap già creata per colorare la mappa (`cmap_temp`/`cmap_trend`),
  quindi il colore dello swatch in legenda è garantito identico a quello
  visto sulla mappa, non un'approssimazione a parte.

  Verificato con `py_compile` + `AppTest` (nessuna eccezione); server live
  riavviato per applicare le modifiche.

  Pagina aggiornata: `dashboard.md` (descrizione Analisi Spaziale, nuova
  frase sulla legenda a fasce).

- **2026-07-16** — MAPPA HOME COLORATA PER TREND (NON PIÙ TUTTA ROSSA).
  L'utente ha notato che la mappa della home aveva tutte le aree dello
  stesso colore e ha chiesto se non fosse meglio dividerle per gravità
  come le altre mappe. La mappa in effetti coloriva tutti i 44 comuni con
  lo stesso rosso fisso (`style_function` con colore costante) — serviva
  solo a localizzarli, senza trasmettere alcuna informazione. Ricolorata
  per `lr_slope_per_decade` (lo stesso `trend_analysis.csv` già letto per
  la tabella accanto, spostato prima dello split in colonne così entrambe
  le colonne possono usarlo), con la stessa colormap divergente centrata
  sullo zero e la stessa legenda a 5 fasce
  (`components/maps.py::render_gradient_legend()`) già introdotta poco
  prima per la mappa trend di Analisi Spaziale — stessa rappresentazione
  per lo stesso tipo di dato in due pagine diverse, invece di due
  convenzioni visive diverse per lo stesso concetto.

  Sottotitolo/didascalia della sezione aggiornati di conseguenza
  ("Comuni con dati di temperatura reali" → "Velocità di riscaldamento per
  comune"). Mantenuto un ramo di fallback (mappa tutta rossa col messaggio
  "esegui trend_analysis.py") nel caso improbabile in cui
  `trend_analysis.csv` non esista ancora.

  Verificato con `py_compile` + `AppTest` (nessuna eccezione); server live
  riavviato per applicare le modifiche.

  Pagina aggiornata: `dashboard.md` (sezione Home, nuovo paragrafo sulla
  mappa colorata per trend).

- **2026-07-16** — LEGENDA ANCHE SULLA MAPPA DI ONDATE DI CALORE. Richiesta
  ambigua dell'utente ("metti una legenda anche sotto le tabelle nella
  pagina ondate di calore") — la pagina ha 2 tabelle testuali senza colori
  (Statistiche per comune, Elenco ondate) e una mappa colorata (Dove si
  concentrano geograficamente le ondate) senza legenda. Chiesto
  esplicitamente all'utente quale delle due intendesse: confermato che
  serviva la legenda colori sulla mappa, non un'interpretazione delle
  tabelle testuali.

  Estesa `components/maps.py::render_gradient_legend()` con un parametro
  `integer: bool = False`: la mappa di concentrazione colora per un
  **conteggio** di ondate (`n_heatwaves_filtro`), non una grandezza
  continua come temperatura/trend — senza questo, la legenda avrebbe
  mostrato range come "3.4 – 6.8 ondate", non sensati per un numero
  intero. Aggiunta la legenda sotto la mappa in `04_ondate_di_calore.py`,
  5 fasce "Poche" → "Molto alto".

  Verificato con `py_compile` + `AppTest` su tutte e 3 le pagine che usano
  `render_gradient_legend()` (Home, Analisi Spaziale, Ondate di Calore) per
  assicurarsi che il nuovo parametro non rompesse le chiamate esistenti;
  server live riavviato.

  Pagina aggiornata: `dashboard.md` (descrizione Ondate di Calore, nota
  sulla legenda a fasce intere).

- **2026-07-16** — LEGENDA COLORI ANCHE SUL GRAFICO A BARRE "INTENSITÀ
  MEDIA PER ANNO". Richiesta esplicita dell'utente. A differenza delle
  mappe (Folium, colorate con `branca.colormap.LinearColormap`), questo è
  un grafico Plotly (`px.bar` con `color_continuous_scale`) — la sua
  colorscale era già disabilitata (`coloraxis_showscale=False`, scelta
  della sessione precedente per evitare una colorbar verticale ingombrante
  su un grafico dove il colore è già ridondante con l'altezza delle
  barre). `render_gradient_legend()` si aspetta una colormap "callable"
  (branca), non compatibile direttamente con una colorscale Plotly —
  invece di introdurre una seconda colormap branca che avrebbe rischiato
  di non corrispondere esattamente ai colori disegnati da Plotly, usato
  `plotly.colors.sample_colorscale()` per campionare **la stessa identica
  colorscale** (`TEMPERATURE_COLORSCALE`) del grafico, garantendo che lo
  swatch in legenda sia sempre coerente con la barra reale. Aggiunto anche
  `range_color=(0, vmax_intensity)` esplicito al grafico, per evitare che
  Plotly scegliesse un range colore leggermente diverso da quello usato
  per calcolare la legenda. Etichette di gravità: "Bassa" → "Estrema".

  Verificato con `py_compile` + `AppTest` (nessuna eccezione); server live
  riavviato.

  Pagina aggiornata: `dashboard.md` (descrizione Ondate di Calore, nota
  sulla legenda del grafico intensità).

- **2026-07-16** — FILTRO PROVINCIA: DEFAULT VUOTO INVECE DI TUTTO
  PRESELEZIONATO. L'utente ha segnalato (chiamandolo "la legenda", ma
  descrivendo in realtà il multiselect provincia di Analisi Spaziale/Ondate
  di Calore) che il riquadro filtro non era "facilmente capibile": all'
  apertura della pagina mostrava già 8 tag preselezionati (tutte le
  province), un riquadro pieno e poco immediato da leggere al primo
  sguardo. Richiesta esplicita: di default deve prendere tutti i comuni
  con dati, con la possibilità di restringere scegliendo dal menu (mai
  digitando a mano).

  Causa: `render_province_filter()` in `components/filters.py` aveva
  `default=all_provinces` — precompilava il box con tutti gli 8 tag.
  Fix: `default=[]` (box vuoto all'apertura) +
  `placeholder="Tutte le province con dati"` per comunicare comunque cosa
  succede di default senza riempire il box di tag. Il comportamento
  sostanziale **non cambia**: la funzione già ritornava
  `provinces or all_provinces`, quindi "nessuna selezione" equivaleva già
  a "tutti i 44 comuni" — il fix è puramente di leggibilità
  dell'interfaccia, non di logica di filtro. La selezione resta comunque
  solo per click dal menu a tendina, mai testo libero.

  Verificato con `AppTest` su entrambe le pagine: box vuoto di default,
  nessuna eccezione. Server live riavviato.

  Pagina aggiornata: `dashboard.md` (sezione "Filtri", nota sul default
  vuoto del multiselect provincia).

- **2026-07-16** — SPOSTATA LA SPIEGAZIONE "COS'È UN'ONDATA DI CALORE" +
  BILANCIATE LE 3 CARD DELLA HOME. Due richieste dell'utente in un solo
  messaggio.

  (1) Rimosso da `Home.py` il riquadro `st.expander("ℹ️ Cos'è un'ondata di
  calore?")`: la home è overview, non il posto giusto per una spiegazione
  di metodologia specifica di una sola sotto-analisi. Integrato il
  contenuto nel riquadro "ℹ️ Come si legge questa pagina" già esistente in
  `04_ondate_di_calore.py`, aggiungendo la sfumatura presente solo nella
  versione della home e mancante in quella della pagina Ondate ("una
  scelta semplificata: i climatologi usano spesso soglie che variano da
  località a località, non un valore fisso"), invece di perderla.

  (2) La card "🔥 Ondate di Calore" tra le 3 di navigazione risultava più
  bassa delle altre due: Streamlit non equalizza automaticamente l'altezza
  di `st.container(border=True)` tra colonne, ogni card si dimensiona sul
  proprio contenuto — la sua didascalia era semplicemente più corta (~113
  caratteri contro i ~124-136 delle altre due), quindi andava a capo su
  meno righe. Fix: allungata la didascalia per portarla a un numero di
  righe comparabile alle altre due, aggiungendo dettaglio reale già
  presente in pagina (frequenza, durata, concentrazione geografica) invece
  di riempitivo senza contenuto.

  Verificato con `py_compile` + `AppTest` su `Home.py` e
  `04_ondate_di_calore.py` (nessuna eccezione); server live riavviato.

  Pagina aggiornata: `dashboard.md` (sezione Home, rimosso riferimento
  all'expander spostato, aggiunta nota sullo spostamento).

- **2026-07-16** — CARD HOME: ALTEZZA FISSA INVECE DI TESTO "A OCCHIO".
  Il fix precedente (allungare la didascalia della card "Ondate di
  Calore" per farla combaciare con le altre due) ha overcorretto: la
  card è diventata più grande delle altre due. Individuata la causa
  strutturale: `st.container(border=True)` senza un'altezza esplicita si
  dimensiona sul proprio contenuto, quindi far combaciare l'altezza di 3
  card tarando manualmente la lunghezza del testo è intrinsecamente
  fragile (dipende da dove il testo va a capo, che a sua volta dipende
  dalla larghezza reale della colonna a schermo, non dal numero di
  caratteri). Fix strutturale: `st.container(border=True, height=160)` su
  tutte e 3 le card (`CARD_HEIGHT` come costante condivisa) — Streamlit
  supporta un'altezza fissa in pixel per `st.container()` dalla versione
  installata (1.58.0). Ripristinata la didascalia originale, più concisa,
  della card Ondate di Calore: con l'altezza ora fissa non serve più
  allungarla artificialmente per farla combaciare.

  Verificato con `py_compile` + `AppTest` (nessuna eccezione, il parametro
  `height` è supportato); server live riavviato.

  Pagina aggiornata: `dashboard.md` (nota nella sezione Home sostituita:
  non più "didascalie allungate per bilanciare", ma "altezza fissa
  esplicita").

- **2026-07-16** — CARD HOME: ALTEZZA AUMENTATA (160 → 220px, poi → 280px).
  L'utente ha segnalato che con `height=160` il testo delle card veniva
  tagliato. Aumentato `CARD_HEIGHT` a 220px; l'utente ha poi chiesto di
  aumentarlo ancora perché anche il link "Vai alla pagina" non si vedeva
  per intero — portato a 280px, abbastanza per titolo + didascalia su più
  righe + link sempre visibili. Mantenuto il vantaggio del fix precedente
  (le 3 card restano sempre della stessa altezza, indipendentemente dalla
  lunghezza del testo). Verificato con `AppTest` a ogni passaggio (nessuna
  eccezione); server live riavviato.

- **2026-07-16** — TESTO ESPLICATIVO ESTESO NEL TAB "DETTAGLIO TECNICO" DI
  ANALISI TEMPORALE. Richiesta esplicita dell'utente: le 4 metriche
  (Mann-Kendall, MK p-value, Sen's slope, Regressione °C/decade) e la
  scomposizione STL avevano solo didascalie molto brevi — "non capisco
  cosa c'è scritto, è poco chiara". Chiesto di spiegarle in linguaggio
  umano e discorsivo, senza riferimenti alle funzioni del codice.

  Scritto un blocco esplicativo per ciascuna delle 4 metriche statistiche:
  Mann-Kendall descritto come confronto di ogni possibile coppia di anni
  (quante volte il più recente è più caldo del più vecchio vs il
  contrario), MK p-value come "probabilità che il risultato sia solo
  caso, se non ci fosse alcun trend reale", Sen's slope come mediana delle
  pendenze tra tutte le coppie di punti (perché la mediana invece della
  media: resistenza a un singolo anno anomalo), Regressione °C/decade come
  la classica retta di tendenza (più sensibile agli estremi ma standard
  nei report climatici) — chiusura con una frase che lega i 4 numeri tra
  loro (Mann-Kendall+p-value dicono se fidarsi, Sen's slope+regressione
  dicono quanto è ripido).

  Per la STL: aggiunta una premessa sul *perché* si scompone una serie
  giornaliera (il segnale di riscaldamento è lento e nascosto sotto
  oscillazioni stagionali/giornaliere molto più grandi), poi una
  spiegazione per ciascuno dei 3 grafici (trend, stagionalità, residuo) su
  cosa mostra e cosa guardare, non solo una definizione di una riga come
  prima.

  Riscritta anche la sezione "Metodologia" da elenco puntato terso a
  domande e risposte esplicite (perché due pendenze diverse tra tab
  Panoramica e Dettaglio tecnico, perché le stagioni sono meteorologiche e
  non astronomiche, perché la baseline delle anomalie è fissa, cosa sono i
  riferimenti nazionale/globale) — stessa informazione della versione
  precedente, ma nella forma di domanda che l'utente si farebbe
  realmente guardando la pagina, invece di un bullet secco.

  Verificato con `py_compile` + `AppTest`, sia sul comune di default
  (Torino) sia con l'aggregato "Piemonte" attivo (nessuna eccezione in
  entrambi i casi); server live riavviato.

  Pagina aggiornata: `dashboard.md` (descrizione Analisi Temporale, nuovo
  paragrafo sul testo esplicativo esteso).

- **2026-07-16** — TESTO ESPLICATIVO ESTESO NEL TAB "DETTAGLIO TECNICO" DI
  ANALISI SPAZIALE. Stessa richiesta esplicita già fatta per Analisi
  Temporale, applicata qui a K-means e indice di Moran: "non capisco cosa
  c'è scritto, è poco chiara", con la richiesta aggiuntiva di spiegare
  bene i cluster climatici, suddividere i 3 gruppi trovati e spiegare
  perché sono stati divisi così.

  **K-means**: spiegato passo per passo l'algoritmo (si fissa in anticipo
  il numero di gruppi desiderato — qui k=3, scelta pratica per avere zone
  descrivibili a parole, **non** derivata da un metodo tipo elbow/silhouette
  — poi si assegna ogni comune al centro più vicino guardando temperatura
  media e giorni sopra 30°C/35°C **standardizzati**, si ricalcolano i
  centri sulla media dei comuni assegnati, si ripete finché i gruppi non
  cambiano più) e perché servono i valori standardizzati (senza,
  "giorni sopra 30°C" con range 0-60+ peserebbe molto più della
  temperatura media che varia di pochi gradi). Chiarito esplicitamente che
  l'algoritmo **non guarda la posizione geografica dei comuni** — se i
  gruppi risultano compatti sulla mappa (zone alpine, di pianura, ecc.) è
  un risultato dell'analisi, non un'ipotesi di partenza incorporata
  nell'algoritmo.

  **Suddivisione dinamica dei 3 cluster** (non hardcoded): la richiesta
  era di "suddividere i tre cluster e spiegare perché sono stati divisi in
  questo modo" — invece di scrivere testo fisso tipo "Cluster 0 = zona
  alpina" (fragile: se si ri-esegue `spatial_analysis.py`, K-means può
  assegnare id diversi agli stessi gruppi, o persino trovare un'altra
  soluzione), il codice ora **ordina i 3 gruppi trovati dal più fresco al
  più caldo** in base alla temperatura media effettiva e genera la
  descrizione (temperatura media, giorni sopra 30°C, elenco comuni,
  etichetta "il più fresco"/"un profilo intermedio"/"il più caldo") al
  volo dai dati correnti — resta corretta anche se l'analisi viene
  ri-eseguita e l'assegnazione numerica dei cluster cambia.

  **Indice di Moran**: aggiunta la distinzione esplicita dai cluster
  K-means (Moran guarda la geografia — comuni vicini con temperature
  simili — K-means no, raggruppa solo per somiglianza climatica), spiegato
  il calcolo (peso inversamente proporzionale alla distanza tra i centri
  comunali, combinato con quanto ciascun comune si discosta dalla
  temperatura media generale) e perché il p-value viene da una
  permutazione (si mescolano le temperature a caso tra i comuni migliaia
  di volte, tenendo ferma la geografia, e si confronta il valore osservato
  con quelli ottenuti a caso) invece che da una formula diretta.

  **Metodologia** riscritta in domande e risposte (perché proprio 3 fasce
  altitudinali con quelle soglie, perché il confronto isola di calore è
  solo illustrativo, perché la mappa del trend non si aggiorna col filtro
  anni), stesso trattamento già applicato ad Analisi Temporale.

  Verificato con `py_compile` + `AppTest` (nessuna eccezione); server live
  riavviato.

  Pagina aggiornata: `dashboard.md` (descrizione Analisi Spaziale, nuovo
  paragrafo sul testo esplicativo esteso e sulla suddivisione dinamica dei
  cluster).

- **2026-07-16** — ETICHETTE CLUSTER RINUMERATE ALLA FONTE (0=FRESCO,
  1=INTERMEDIO, 2=CALDO). L'utente ha notato che l'assegnazione dei 3
  cluster non seguiva "una logica di ordinamento" e ha chiesto di
  imporre esplicitamente: cluster 0 il più fresco, 1 intermedio, 2 il più
  caldo. Causa: sklearn's `KMeans.fit_predict()` assegna le etichette
  grezze (0, 1, 2) in un ordine **arbitrario**, deciso dall'inizializzazione
  interna dell'algoritmo, senza alcun legame con quanto è caldo o freddo
  il gruppo — la sessione precedente aveva già ordinato dinamicamente la
  *descrizione testuale* per temperatura nella dashboard, ma il dato
  grezzo sottostante (`climate_cluster` in `spatial_analysis.csv`, i
  colori sulla mappa, il numero mostrato nei tooltip) restava nell'ordine
  arbitrario originale.

  Fix alla fonte, non solo nel testo: `climate_clustering()` in
  `src/analysis/spatial_analysis.py` ora calcola la temperatura media di
  ciascuna etichetta grezza, le ordina in modo crescente, e costruisce una
  mappa {etichetta grezza → rank} per rinumerare i risultati prima di
  restituirli — cluster 0 diventa sempre il più fresco, l'ultimo sempre il
  più caldo, indipendentemente da come sklearn li aveva numerati
  internamente.

  **Rieseguito** `python -m src.analysis.spatial_analysis`: risultato
  verificato — cluster 0 = Acceglio/Aisone/Alagna Valsesia/Bardonecchia/
  Ceresole Reale/Formazza/Macugnaga/Rorà (3.8°C, alpino), cluster 1 = 17
  comuni pedemontani/collinari (11.1°C), cluster 2 = 19 comuni di pianura
  (12.9°C) — stessa identica composizione di gruppi di prima (l'algoritmo
  non è cambiato, solo la numerazione), confermato anche dal test unitario
  `test_separates_two_clearly_distinct_groups` (ancora verde).

  **Colori aggiornati di conseguenza**: `CLUSTER_COLORS` in
  `dashboard/components/constants.py` passa da {0: blu, 1: rosso, 2: verde}
  (arbitrario) a {0: blu, 1: arancio, 2: rosso} (stessa logica blu→rosso
  della colormap di temperatura usata nel resto del sito, ora coerente
  anche qui: cluster freddo = blu, cluster caldo = rosso). Stesso
  aggiornamento fatto nella mappa QGIS `hotspot_analysis.qgz`
  (`qgis_projects/build_maps.py`), **rigenerata** con
  `python-qgis-ltr.bat build_maps.py` per riflettere sia il nuovo
  `spatial_analysis.csv` sia i nuovi colori.

  Verificato con `pytest` (cluster test ancora verde), `py_compile` +
  `AppTest` sulla pagina Analisi Spaziale (nessuna eccezione); server live
  riavviato.

  Pagine aggiornate: `statistical-analysis.md` (etichette cluster
  rinumerate, composizione con id 0/1/2 espliciti), `gis-maps.md` (nota su
  `hotspot_analysis.qgz` rigenerata), `dashboard.md` (nuovo paragrafo sul
  fix alla fonte).

- **2026-07-16** — TESTO ESPLICATIVO ESTESO NEL TAB "DETTAGLIO TECNICO" DI
  ONDATE DI CALORE (stesso pattern di Analisi Temporale e Analisi
  Spaziale). Richiesta esplicita dell'utente di applicare lo stesso
  trattamento fatto per le altre due pagine anche qui.

  **Confronto con la definizione a soglia percentile**: aggiunta una
  premessa sul *perché* esiste un'alternativa alla soglia fissa (35°C
  tratta tutti i comuni allo stesso modo, penalizzando i comuni di
  montagna che quasi non la raggiungono mai anche in estati eccezionali
  per i loro standard locali), poi una spiegazione concreta di cosa sia un
  percentile e come si calcola (ordinare tutte le temperature massime
  storiche di un comune dal 2000 a oggi; il 90° percentile è il valore
  sotto il quale sta il 90% dei giorni — un numero diverso per ogni
  comune, non fisso come 35°C).

  **Metodologia** riscritta in domande e risposte, stesso trattamento
  delle altre due pagine: perché il resto del sito usa comunque la soglia
  fissa (un solo criterio semplice e uguale per tutti, i numeri percentile
  qui sono solo un confronto illustrativo e non sostituiscono mai quelli
  ufficiali mostrati altrove), perché la durata minima resta 3 giorni
  anche con la soglia percentile (per confrontare le due definizioni a
  parità di condizioni), cosa aggrega esattamente la heatmap "calendario"
  (per ogni combinazione anno/giorno-dell'anno, quanti comuni avevano
  un'ondata attiva quel giorno preciso).

  Verificato con `py_compile` + `AppTest` (nessuna eccezione); server live
  riavviato.

  Pagina aggiornata: `dashboard.md` (descrizione Ondate di Calore, nuovo
  paragrafo sul testo esplicativo esteso — chiude il giro di tutte e 3 le
  pagine di analisi con lo stesso trattamento).

- **2026-07-16** — PIANO ARTICOLO SCIENTIFICO: NUOVA PAGINA + RICOGNIZIONE
  FONTI ESTERNE MANCANTI. L'utente ha deciso di trasformare il progetto in
  un articolo scientifico (descrittivo + esplicativo sulle cause
  città/industria/riscaldamento delle differenze di temperatura), target
  una rivista/conferenza peer-reviewed vera, non solo portfolio. Creata
  `wiki/pages/paper-scientifico.md` (nuova pagina di pianificazione, non di
  codice esistente) con le 5 fasi concordate (validazione ARPA, estensione
  campione comuni, acquisizione uso del suolo/popolazione, modellazione
  spaziale, percorso di pubblicazione) e la letteratura raccolta via
  ricerca web (Garzena et al. 2019 su UHI Torino, Perkins & Alexander 2013
  su definizione ondate di calore, studio SUHI/impervious surface città
  italiane, ecc.). Aggiornato `index.md`.

  **Ricognizione di fattibilità delle fonti esterne mancanti** (uso del
  suolo, popolazione, validazione stazioni): nessuna delle tre è un
  semplice "attiva e scarica".
  - `ArpaPiemonteDownloader` esiste già nel codice ma **l'URL in
    `config.yaml` (`arpa_piemonte.url`) risponde 404** (verificato con
    richiesta HTTP diretta) — stesso tipo di bug placeholder mai eseguito
    già trovato per l'URL ISTAT dei confini comunali il 2026-07-04. I dati
    veri stanno dietro un'interfaccia a mappa o una richiesta manuale, non
    un endpoint diretto.
  - CORINE Land Cover (Copernicus) ha un'API di download reale ma richiede
    un account CLMS con credenziali, come già il caso di
    `CopernicusERA5Downloader`/`CDS_KEY`.
  - Popolazione ISTAT (`dati.istat.it`, dataset SDMX `DCIS_POPORESBIL1`)
    non richiede account, ma l'endpoint/query esatti restano da verificare.

  Nessun codice scritto in questa sessione per queste fonti (solo
  ricognizione); documentato in `paper-scientifico.md` per evitare di
  ripartire da zero nella prossima sessione. Non toccato
  `download_extra_municipalities.py`/DB: l'utente sta eseguendo in parallelo
  l'estensione della copertura temperature da 44 a 300 comuni.

  Pagine aggiornate: `paper-scientifico.md` (nuova), `index.md`.

  **Scheletro del manoscritto**: su richiesta dell'utente, creato
  `paper/manoscritto.md` (nuova cartella, fuori da `wiki/` — è il contenuto
  del paper stesso, non meta-pianificazione). Struttura completa
  Abstract/Introduzione/Dati e Metodi/Risultati/Discussione/Conclusioni/
  Bibliografia/Appendice di tracciabilità, con marcatori **[FATTO]**/
  **[DA FARE]** su ogni sottosezione. Le sezioni **[FATTO]** riportano i
  numeri reali già verificati (38/44 comuni con trend significativo,
  145 ondate, Moran's I=0.101 p=0.002, cluster 3.8/11.1/12.9°C, ampiezza
  STL 27-34°C) con riferimento diretto ai CSV in `output/` (tabella di
  tracciabilità in Appendice A). Le sezioni **[DA FARE]** (uso del
  suolo/popolazione, validazione ARPA, modello a errore spaziale)
  restano vuote/segnaposto finché il lavoro sottostante non è concluso —
  deliberato, per non scrivere conclusioni prima di avere i dati.
  Aggiornata `paper-scientifico.md` con un rimando al nuovo file.

  **Approfondimento popolazione ISTAT (stessa sessione, su richiesta
  esplicita dell'utente di lavorare in parallelo al download dei 300
  comuni)**: investigata l'API SDMX `esploradati.istat.it/SDMXWS` per il
  dataset `DCIS_POPORESBIL1` (popolazione residente-bilancio). Confermato
  via richieste HTTP dirette: (1) i codici territorio nel codelist
  `CL_ITTER107` coincidono esattamente con `municipalities.istat_code` già
  in DB (`001272` = Torino, verificato leggendo il codelist completo, 9MB);
  (2) esiste un dataflow specifico per il Piemonte
  (`22_315_DF_DCIS_POPORESBIL1_3`, identificato tra ~450 dataflow cercando
  l'annotazione `FILTER__ITC1`), distinto dal dataflow padre `22_315`.
  **Nessuna query dati ha però restituito osservazioni reali**: sia sul
  flow padre che su quello Piemonte-specifico, con diverse combinazioni di
  `DATA_TYPE` (`JAN`, `DEC_CP_P`, wildcard) e anche con `REF_AREA`
  completamente jolly, la risposta è sempre `NoRecordsFound` o serie con
  tutte le osservazioni `null` — sembra un dataset con struttura/DSD
  popolata ma dati non esposti (o non ancora migrati) su questo endpoint
  REST specifico. Non risolto in questa sessione: il passo successivo
  probabile è l'export CSV manuale della query legacy `.Stat`
  (`dati.istat.it/Index.aspx?QueryId=19101`), sistema diverso dal nuovo
  SDMX REST, mai tentato. File temporanei di indagine (codelist 9MB, lista
  dataflow 13.5MB) salvati solo nello scratchpad di sessione, non nel
  repository.

- **2026-07-16** — POPOLAZIONE ISTAT: TROVATA LA FONTE GIUSTA E CARICATA
  PER TUTTI I 1180 COMUNI. Continuazione della stessa indagine, stessa
  sessione: tentato l'export della query legacy `dati.istat.it` (QueryId
  19101) come prossimo passo previsto — il portale e' dismesso (redirect
  con certificato scaduto verso un avviso di decommissioning). Trovato
  invece `demo.istat.it`, sistema attivo e separato ("Popolazione
  residente per eta' e sesso"), con un file ZIP per provincia
  (`https://demo.istat.it/data/posas/POSAS_{anno}_it_{codice}_{nome}.zip`,
  nessun account), CSV con una riga per comune/eta'/sesso (eta'=999 e' il
  totale per comune). Verificato scaricando ed ispezionando a mano il file
  di Torino prima di scrivere codice: i codici comune coincidono
  esattamente con `istat_code` gia' in DB.

  Scritto `src/data_acquisition/download_population.py`. Bug trovato in
  fase di test manuale (prima di lanciare lo script sulle 8 province): la
  colonna eta' viene letta da pandas come stringa, non intero — un filtro
  numerico (`== 999`) restituiva sempre 0 righe; corretto confrontando con
  la stringa `'999'`. Eseguito sulle 8 province reali: **1180/1180 comuni
  aggiornati** (`municipalities.population`), coincidenza esatta per
  provincia con l'allocazione gia' usata in
  `download_extra_municipalities.py` (312 Torino, 247 Cuneo, 187
  Alessandria, 117 Asti, 87 Novara, 82 Vercelli, 74 Biella, 74
  Verbano-Cusio-Ossola). Valori verificati a campione via query SQL
  diretta: Torino 855.654 ab. (densita' 6580 ab/km2, usando `area_km2` gia'
  presente), Alessandria 93.409, Cuneo 55.747, Bardonecchia 2.853 (densita'
  21.6 ab/km2), Formazza 410 (densita' 3.1 ab/km2) — gradiente
  pianura/alpino coerente col clustering climatico gia' trovato.

  Aggiornato anche `paper/manoscritto.md` (§2.4 passata da "DA FARE" a
  "PARZIALMENTE FATTO" per la parte popolazione).

  Pagine aggiornate: `data-sources.md` (nuova sezione), `data-model.md`
  (`population` non piu' `NULL`), `paper-scientifico.md`.

- **2026-07-16** — CORINE LAND COVER: TERZA COVARIATA ESPLICATIVA FATTA,
  PER TUTTI I 1180 COMUNI. Su richiesta esplicita dell'utente ("spiegami
  come procedere con Copernicus"), spiegato il percorso CLMS (account EU
  Login gratuito, poi "Download by area" invece dell'API con token JWT —
  quest'ultima scartata di comune accordo perche' CORINE si aggiorna ogni
  ~6 anni, non serve automazione). L'utente ha creato l'account e provato a
  scaricare da solo.

  **Primo tentativo dell'utente**: cartella `U2018_CLC2018_V2020_20u1_doc/`
  aggiunta al progetto — ispezionata e risultata **solo documentazione**
  (42 file: PDF, metadata XML, legenda), nessuna geometria. Salvato
  `data/external/clc_legend.csv` (tabella codici CLC -> classi, utile per
  dopo), poi cancellata la cartella su richiesta dell'utente.

  **Secondo tentativo, quello giusto**: file `U2018_CLC2018_V2020_20u1.gpkg`
  (136 MB) aggiunto alla root del progetto. Ispezionato prima di scrivere
  codice (`pyogrio.read_info`): EPSG:3035 (proiezione equal-area di CLC),
  52.794 poligoni, campo `Code_18` = codice CLC a 3 cifre, dimensione ed
  estensione coerenti con un ritaglio sul Piemonte (non tutta Europa).

  Creata `sql/03_land_cover.sql` — nuova tabella `municipality_land_cover`
  (satellite 1:1 con `municipalities`, non nuove colonne li' per non
  appesantirla): % urbano/agricolo/forestale-seminaturale/zone umide/acqua
  + classe dominante, per comune.

  Scritto `src/data_acquisition/process_land_cover.py`: overlay geopandas
  tra le geometrie comunali (riproiettate in EPSG:3035 per coerenza con
  CLC) e i poligoni CLC, categorie aggregate al primo carattere del codice
  a 3 cifre (1=urbano...5=acqua; i codici speciali 990/995/999 in "other",
  vedi `clc_legend.csv`). Testato prima su 3 comuni campione
  (Torino/Alessandria/Formazza, ~8 secondi) prima di lanciare sui 1180
  reali — risultati gia' plausibili nel test (Torino 75% urbano, Formazza
  0% urbano/dominante forestale). Overlay completo sui 1180 comuni:
  **~16 secondi**, nessun problema di performance.

  **Risultato reale, 1180/1180 comuni**: distribuzione classe dominante
  690 agricultural, 466 forest_seminatural, 12 urban, 12 water. Valori
  verificati a campione: Torino 75.45% urbano (dominante urbano); Verbania
  40.70% acqua (dominante acqua — sul Lago Maggiore, coerente con
  l'ampiezza stagionale minima gia' trovata in
  [Analisi statistica](statistical-analysis.md)); Vercelli 75.94% agricolo,
  Alessandria 84.18%, Cuneo 82.37%, Asti 67.59% (tutte dominante
  agricolo, coerente con la vocazione risicola/cerealicola della pianura
  piemontese); Bardonecchia 95.46% e Formazza 94.64% forest_seminatural
  (dominante forestale, comuni alpini).

  Aggiornato `paper/manoscritto.md` (§2.4 uso del suolo passata a
  **[FATTO]**; nota esplicita sul disallineamento temporale CLC2018 vs
  temperature 2000-2025/popolazione 2026, da dichiarare come limite non da
  nascondere). Con questo, tutti e tre gli ingredienti del modello
  esplicativo di §3.5 (elevazione, popolazione, uso del suolo) sono ora
  disponibili per i comuni con temperatura — il modello statistico vero e
  proprio (§2.4/§3.5) resta pero' ancora da costruire.

  Pagine aggiornate: `data-model.md` (nuova tabella
  `municipality_land_cover`), `data-sources.md` (nuova sezione, inclusi i
  due tentativi), `paper-scientifico.md`.

- **2026-07-16** — SCOMPOSIZIONE DI "URBANO" IN SOTTO-CLASSI (RESIDENZIALE
  VS INDUSTRIALE). Su richiesta esplicita dell'utente, che ha scelto questa
  opzione tra tre proposte (le altre: aggiungere subito i dati a dashboard,
  o fermarsi ad aspettare) perche' quasi gratis (dato gia' scaricato) e
  perche' risponde direttamente all'ipotesi originale del paper su
  citta'/industria come cause delle differenze di temperatura — un unico
  `pct_urban` aggregato non distingueva residenziale da industriale.

  Aggiunte 5 colonne a `municipality_land_cover` (`sql/03_land_cover.sql`,
  via `ALTER TABLE ADD COLUMN IF NOT EXISTS`): `pct_residential` (codici
  CLC 111/112), `pct_industrial_commercial` (121), `pct_transport`
  (122-124), `pct_urban_green` (141-142), `pct_extraction_construction`
  (131-133) — sommano a `pct_urban`. Esteso
  `src/data_acquisition/process_land_cover.py` per calcolarle riusando lo
  stesso overlay geopandas gia' fatto (nessun overlay aggiuntivo, solo un
  secondo `groupby` sulle sole righe con `level1=='urban'`).

  **Bug trovato e corretto rieseguendo lo script**: prima esecuzione,
  0 righe con errori evidenti ma valori `NaN` silenziosi per
  `pct_industrial_commercial` (e le altre sotto-classi) in tutti i comuni
  con **zero** intersezione urbana (nessuna riga in `overlay` con
  `level1=='urban'` per quel comune) — scoperto ordinando per
  `pct_industrial_commercial DESC` e vedendo `NaN` in cima invece che 0.
  Causa: `DataFrame.div(Series, axis=0)` allinea gli indici e produce
  `NaN` per le righe assenti da un lato; il successivo
  `.reindex(fill_value=0.0)` **non** sostituisce questi `NaN` (riempie solo
  le righe del tutto assenti dall'indice, non quelle gia' presenti ma
  `NaN`) — serviva un `.fillna(0.0)` esplicito dopo la divisione, aggiunto
  sia per le sotto-classi urbane sia per le categorie di Livello 1 (stesso
  rischio in linea di principio, anche se non si era manifestato).
  Rieseguito: 0 righe `NULL`/`NaN` su 1180.

  **Risultato reale**: Grugliasco 34.20% industriale/commerciale (64.24%
  urbano totale), Beinasco 33.40% (67.26% totale), Settimo Torinese 26.07%
  — le vere zone a vocazione industriale della cintura torinese (non
  Torino stessa, che ha piu' residenziale: 45.47% vs 20.56% industriale),
  coerente con la geografia industriale nota dell'area metropolitana.

  Pagine aggiornate: `data-model.md` (nuove colonne + bug documentato),
  `paper/manoscritto.md` (§2.4, nuovo punto sulle sotto-classi urbane).

- **2026-07-16** — TO-DO AGGIUNTI ALLA WIKI (dashboard + altri dati
  esplicativi), su richiesta esplicita dell'utente. Non implementati in
  questa sessione, solo tracciati in
  [Articolo scientifico](paper-scientifico.md) sotto "Idee da esplorare":
  (1) aggiungere popolazione/uso del suolo alla dashboard (mappa classe
  dominante o % urbana, mappa densita' di popolazione, sostituire il
  confronto isola di calore "solo illustrativo" con uno basato su dati
  reali); (2) altre covariate candidate in ordine di sforzo crescente:
  NDVI da satellite, pendenza/esposizione da un DEM, distanza dal Po/dai
  laghi, densita' stradale/edificato da OpenStreetMap (downloader gia'
  presente nel codice, mai attivato).

- **2026-07-16** — DASHBOARD: USO DEL SUOLO E POPOLAZIONE IN ANALISI
  SPAZIALE, SOSTITUITO IL CONFRONTO ISOLA DI CALORE ILLUSTRATIVO. Su
  richiesta esplicita dell'utente ("procedi con Aggiungere popolazione/uso
  del suolo alla dashboard"), primo dei due to-do tracciati poco prima.

  Aggiunte a `components/constants.py`: `LAND_COVER_COLORS`/
  `LAND_COVER_LABELS`, colori vicini alla palette ufficiale CORINE (presi
  da `data/external/clc_legend.csv`, non inventati) per le 5 categorie di
  Livello 1. Aggiunte a `components/queries.py`: `get_land_cover_all()` e
  `get_all_municipality_geometries_wkt()` (tutti i 1180 comuni, non solo i
  44 con temperatura - uso del suolo/popolazione coprono l'intero
  territorio) e `get_land_cover_with_population()` (solo i comuni con
  temperatura, per lo scatter).

  In `03_analisi_spaziale.py`, dopo la sezione fasce altitudinali:
  - **Mappa uso del suolo dominante** (1180 comuni).
  - **Mappa densita' di popolazione** (1180 comuni, scala logaritmica -
    altrimenti Torino schiaccia la scala).
  - **Scatter temperatura vs uso del suolo/popolazione** (solo i comuni con
    temperatura): sostituisce il vecchio confronto "Torino vs comuni
    rurali della provincia" (dichiarato "solo illustrativo"). Selettore
    `st.radio` tra % urbano/% industriale-commerciale/densita' di
    popolazione; colore = fascia altitudinale, per poter valutare a occhio
    se l'effetto regge a parita' di quota; metrica di correlazione di
    Pearson con caveat esplicito ("non controllata per quota", il modello
    vero resta pianificato in `paper/manoscritto.md` §3.5).

  **Bug trovato e corretto con `AppTest` prima di qualunque verifica
  manuale**: `geo_all.merge(land_cover_all, on='municipality_name')` -
  entrambe le tabelle hanno una colonna `province_name`, non parte della
  chiave di join, quindi pandas la rinominava in `province_name_x`/
  `province_name_y` invece di lasciarla con il nome atteso - `KeyError:
  'province_name'` al primo `AppTest.run()`. Fix: colonna duplicata esclusa
  da un lato del merge prima di unire.

  **Verificato con `AppTest`**: run di default (nessuna eccezione), radio
  su `pop_density` (scala log sull'asse x) e su
  `pct_industrial_commercial` (nessuna eccezione in entrambi i casi),
  filtro provincia ristretto a una sola provincia piccola (Biella, nessuna
  eccezione). Valori reali sensati: correlazione Pearson +0.30 (%urbano vs
  temperatura, tutti i comuni nel filtro di default) - plausibile, non
  sospetta data la confusione nota con la quota.

  Pagine aggiornate: `dashboard.md` (nuova sezione + bug documentato),
  `paper-scientifico.md` (to-do 1 segnato fatto).

- **2026-07-17** — ESTENSIONE A 63 COMUNI + DATI FINO AD OGGI (obiettivo
  iniziale: tutti i 1180 comuni). Richiesta esplicita dell'utente:
  "coprimi i 1180 comuni piemontesi, e aggiorna la data fino ad oggi".
  Sessione lunga e accidentata, con un vero e proprio processo di
  scoperta empirica del rate limit di Open-Meteo. Cronologia:

  1. **Stima iniziale ottimista**: spiegato all'utente il costo reale di
     1180 comuni (~11M righe, ma soprattutto ore di download per il rate
     limit già noto). Consigliata una via di mezzo (200-300 comuni),
     accettata. Chiesto anche un parere su leggibilità delle mappe con
     300 punti: convertita la mappa del trend in Analisi Spaziale da
     marker a cerchio a poligoni colorati (stesso trattamento delle altre
     3 mappe), eliminando il rischio di sovrapposizione visiva.
  2. **Tentativo 1 (256 comuni extra, obiettivo 300 totali)**: lanciato in
     background. Dopo **~5h40** di download continuo (monitorato a
     intervalli), solo 37/256 comuni riusciti, 123 falliti
     definitivamente. Interrotto — e siccome
     `download_extra_municipalities.py::download_all()` collezionava
     tutto in una lista Python scrivendo il CSV **solo a fine
     esecuzione**, l'interruzione ha fatto perdere **tutto** il progresso
     (nessun file scritto). Lezione durissima ma chiara.
  3. **Tentativo 2 (56 comuni, obiettivo ridotto a 100)**: bloccato
     **immediatamente**, anche su una singola richiesta di test isolata
     (429). Il corpo della risposta ha rivelato la causa: `"Daily API
     request limit exceeded. Please try again tomorrow."` — un limite
     **giornaliero**, non solo "al minuto" come già documentato. La
     finestra di 5h40 sprecata aveva già esaurito la quota di giornata.
  4. **Fix strutturale** (prima di riprovare, non dopo): salvataggio
     **incrementale** in `download_extra_municipalities.py` (ogni comune
     scaricato subito appeso al CSV, `mode='a'`) — così un'interruzione
     futura non fa più perdere lavoro.
  5. **Discussione sulle alternative**: l'utente ha chiesto se non ci
     fossero altri modi per scaricare i dati (manualmente, altre fonti).
     Risposta onesta: Copernicus CDS ha un'interfaccia web per download
     manuali (bypassa Open-Meteo, ma richiede account, è un dataset
     diverso — ERA5 a griglia, non per stazione — e la pipeline di
     parsing NetCDF non è mai stata testata); ARPA Piemonte copre solo le
     poche stazioni reali, non abbastanza comuni. Nessuna alternativa
     chiaramente migliore dell'aspettare; l'utente ha scelto di aspettare
     e riprovare il giorno dopo con lotti più piccoli.
  6. **Giorno successivo (2026-07-17)**: quota resettata (verificato con
     un test leggero). Reso `download_extra_municipalities.py`
     **parametrico** (`--count`, allocazione per provincia calcolata dal
     vivo con `compute_target_per_province()` invece di pesi fissi nel
     codice) su richiesta dell'utente di provare lotti da 10 per volta
     per scoprire la soglia esatta. Un lotto di 50 ha **rivelato
     empiricamente**: si blocca sempre intorno a **19-20 richieste
     "pesanti"** (26 anni di storico ciascuna) — dal 20° comune in poi,
     ogni tentativo falliva dopo 5 retry. Fermato subito (zero perdita,
     grazie al fix del punto 4): **19 comuni aggiuntivi** salvati con
     successo (44 → 63 comuni). Chiesto conferma all'utente se procedere
     subito con la pipeline sui 63 disponibili o aspettare altri giorni
     per arrivare a 94: scelto di procedere subito.
  7. **Delta a oggi per tutti i 63 comuni**: scritto nuovo script
     `src/data_acquisition/update_recent_data.py` (stesso fix di
     salvataggio incrementale fin dall'inizio, lezione già imparata).
     Scoperta interessante: le richieste piccole (~198 giorni ciascuna,
     invece di 26 anni) **non hanno mai incontrato il rate limit** —
     tutti e 63 i comuni aggiornati con successo in un solo lotto, zero
     errori. La quota sembra legata al volume di dati per richiesta, non
     a un conteggio piatto (osservazione empirica, non verificata contro
     documentazione ufficiale).
  8. **Caricamento nel DB**: filtrato il CSV pulito ai soli
     `municipality_id` non ancora presenti prima di caricarlo (nessun
     vincolo di unicità `(municipality_id, date)` in `temperature`: un
     caricamento ingenuo dell'intero file avrebbe duplicato i 36 comuni
     già presenti dalla sessione precedente). Elevazione ricalcolata per
     tutti i 63 comuni (query batch singola, economica).
  9. **Ricalcolo di tutta la catena a valle**: `TRUNCATE` +
     `identify_heatwaves()` (190 ondate, +16 rispetto a prima grazie al
     2026), refresh viste materializzate (1701 righe), tutti e 4 i moduli
     `src/analysis/` (STL ~30 minuti data la mole, eseguita in
     background), mappe QGIS rigenerate.
  10. **2 bug reali trovati grazie al dato 2026** (mai emersi prima
      perché la serie storica non aveva mai superato il 2025): (a)
      `frequency_by_year()` in `heatwave_stats.py` aveva un
      `reindex(range(2000, 2026))` fisso che scartava in silenzio le 16
      ondate del 2026 dal grafico della dashboard — nessun errore, solo
      dati mancanti; scoperto confrontando il conteggio diretto da
      `heatwave_events` con l'output della funzione. Fix: range dinamico
      dal min/max anno realmente presente. (b) Stesso identico tipo di
      bug in `dashboard/components/filters.py`
      (`YEAR_MIN, YEAR_MAX = 2000, 2025` fissi) — avrebbe reso
      impossibile selezionare il 2026 nello slider. Fix: dinamico da
      `get_overview_stats()`.
  11. **Aggiornamento testi dashboard**: `Home.py` reso completamente
      dinamico (nessun numero di comuni/anno più hardcoded, tutto da
      `get_overview_stats()`), stesso trattamento parziale sulle altre
      pagine per gli help text/caption più visibili; le narrazioni
      storiche di log/dashboard.md che descrivono sessioni precedenti
      **non sono state riscritte** (coerente con la natura append-only
      della documentazione).

  **Risultato finale**: 44 → **63 comuni** (8 capoluoghi + 55 extra),
  **610.785 righe**, dal 2000 **fino a oggi** — non i 1180 comuni
  richiesti inizialmente, ma un incremento reale, verificato, e ottenuto
  senza perdite nonostante due tentativi fintiti falliti. Moran's I
  migliora ulteriormente (0.132, p=0.001). Trend: 54/63 comuni
  significativi; scoperto un caso controcorrente (Briga Alta, unico
  raffreddamento significativo, -0.63°C/decade) segnalato onestamente
  invece che ignorato.

  Verificato con `py_compile` + `AppTest` su tutte le pagine dopo ogni
  round di modifiche (nessuna eccezione); server live riavviato con i
  dati aggiornati.

  Pagine aggiornate: `data-sources.md` (racconto completo della scoperta
  del rate limit, 2 nuovi script documentati), `etl-pipeline.md`
  (sezione estensione + bug), `data-model.md` (conteggi righe/comuni/anni
  aggiornati), `statistical-analysis.md` (nuova sezione risultati
  ricalcolati + bug), `gis-maps.md` (mappe rigenerate), `dashboard.md`
  (nota di aggiornamento + bug), `project-status.md` (nuova sezione
  cronologica con tutti i dettagli).

- **2026-07-17** — NDVI (VERDE DA SATELLITE): PREDISPOSIZIONE TABELLA +
  SCRIPT, DOWNLOAD ANCORA DA FARE. Su richiesta dell'utente, avviata la
  terza covariata esplicativa per il paper scientifico (dopo popolazione e
  CORINE Land Cover, entrambe fatte il 2026-07-16) — vedi
  [Articolo scientifico](paper-scientifico.md), "Idee da esplorare".

  **Decisione di scoping presa con l'utente** (stessa logica costi/
  benefici gia' applicata a CORINE): tre opzioni presentate — Sentinel-2
  vero via Google Earth Engine (10m, richiede account GEE), Sentinel-2 vero
  via Copernicus Data Space Ecosystem Statistical API (10m, OAuth,
  rischio di friction gia' visto con le altre API Copernicus/ISTAT del
  progetto), o Copernicus Global Land Service NDVI 300m V3 (prodotto gia'
  calcolato, download manuale, nessun account nuovo oltre a quello CDSE per
  il solo download). Scelta: **CGLS NDVI 300m V3**, stesso pattern
  low-effort che ha funzionato per CORINE.

  **Ricerca tecnica** (via web, per evitare di indovinare la formula come
  gia' successo in passato con bug di encoding/scaling): il prodotto e' un
  GeoTIFF a 8 bit, EPSG:4326 (nessuna riproiezione necessaria, a
  differenza di CLC/EPSG:3035). DN 0-250 -> NDVI reale via
  `NDVI = DN * 0.004 - 0.08`; DN 251-255 sono flag dedicati (251=missing,
  252=cloud, 253=snow/ice, 254=sea, 255=background) — confermato da PDF
  ufficiale Copernicus (parzialmente, il rendering testuale del PDF era
  degradato) e da documentazione Sentinel Hub/CDSE leggibile. **Non ancora
  verificato empiricamente su un file scaricato per il Piemonte** — stesso
  tipo di rischio gia' incontrato con CLC (i due tentativi prima del file
  giusto), da tenere d'occhio alla prima esecuzione reale.

  Anche il *dove* si scarica e' cambiato rispetto a CLC: l'accesso ai dati
  NDVI globali e' migrato dal portale CLC (`land.copernicus.eu`, tool
  "Download by area" gia' usato per CORINE) al Copernicus Data Space
  Ecosystem (`dataspace.copernicus.eu`, Copernicus Browser) — richiede un
  account gratuito separato da quello EU Login usato per CLC. Il percorso
  esatto di ritaglio sul Piemonte non e' ancora stato verificato
  praticamente (va documentato dopo il primo download reale, come gia'
  fatto per CORINE con i suoi due tentativi).

  **Predisposto in questa sessione** (codice, non ancora eseguito su dati
  reali): `sql/04_ndvi.sql` (tabella `municipality_ndvi`, satellite 1:1
  con `municipalities` come `municipality_land_cover`), `src/data_acquisition/process_ndvi.py`
  (zonal stats via `rasterstats` invece dell'overlay vettoriale di CLC,
  dato che qui la sorgente e' un raster; `all_touched=True` per i comuni
  piccoli rispetto ai 300m di pixel), `rasterio`/`rasterstats` aggiunti a
  `requirements.txt` (non ancora installati/verificati nel venv).

  **Eseguito realmente in questa sessione** (non solo scritto): `rasterio`/
  `rasterstats` installati nel `.venv` (verificato `pip install`, nessun
  conflitto), `python -m src.data_acquisition.process_ndvi --help` eseguito
  con successo (import puliti, argparse funzionante), e
  `sql/04_ndvi.sql` **applicato per davvero** al database locale (via
  cursore DBAPI grezzo, stesso pattern gia' documentato per
  `initialize_schema()` — `exec_driver_sql` con dict di parametri vuoto
  fallisce su script multi-statement) — tabella `municipality_ndvi`
  verificata esistente con lo schema atteso via
  `information_schema.columns`.

  **Non fatto in questa sessione**: il download manuale del GeoTIFF
  (compito dell'utente) e l'esecuzione dello script su un file reale, quindi
  **`municipality_ndvi` esiste ma e' vuota** (0 righe) — a differenza delle
  sessioni CLC/popolazione, qui il dato non e' ancora arrivato perche' il
  download richiede un account e un'interazione con un portale esterno che
  l'utente deve fare in prima persona.

  Pagine aggiornate: `data-sources.md` (nuova sezione "NDVI (Copernicus
  Global Land Service)"), `data-model.md` (nuova tabella
  `municipality_ndvi`), `paper-scientifico.md` (voce "NDVI" in "Idee da
  esplorare" segnata "in corso"), `project-status.md`.

- **2026-07-17** — INGEST. Restyling identità visiva "calore" della
  dashboard Streamlit, su richiesta esplicita dell'utente ("frontend troppo
  minimalista e piatto, sembra un PDF"). Processo: analisi della struttura
  reale (`dashboard/`), mockup HTML statico (Artifact) per validare la
  direzione visiva prima di toccare il codice — un giro di feedback
  dell'utente ("sfondo troppo nero") ha spostato la base da quasi-nero a
  grigio ardesia prima dell'implementazione. Palette derivata dai colori
  già usati nei grafici (non introdotta ex novo). Toccati: `constants.py`
  (nuovi token `THEME_*`/`FONT_*`/`MAP_TILES`), `styling.py` (tipografia
  Fraunces/Manrope/JetBrains Mono, hero, card di navigazione via
  `st.container(key=...)`, striscia "numeri chiave"), nuovo `charts.py`
  (sfondo trasparente per Plotly, deliberatamente senza toccare i colori
  del testo per non rompere l'adattamento automatico chiaro/scuro di
  `st.plotly_chart(theme="streamlit")`), `Home.py` (hero/card/stats),
  tile Folium passate da chiare a scure (`CartoDB dark_matter`) in tutte
  le 7 mappe di `Home.py`/`03_analisi_spaziale.py`/`04_ondate_di_calore.py`.
  Corretto un claim non più valido nella wiki: una nota del 2026-07-15
  diceva che le card non erano stilizzabili via CSS per mancanza di un
  selettore stabile — falso, `st.container(key=...)` (già disponibile
  nella versione installata) espone la classe stabile `st-key-<key>`.
  Verificato con `py_compile` + `AppTest` su tutte e 5 le pagine (nessuna
  eccezione, database reale) e un avvio/arresto di server live; verifica
  visiva in browser reale non eseguita in questa sessione (nessun tool di
  automazione browser disponibile) — dichiarato esplicitamente come tale,
  non spacciato per completo.

  Pagine aggiornate: `dashboard.md` (nuova sezione "Restyling identità
  visiva", struttura cartelle aggiornata, claim obsoleto corretto),
  `index.md` (riga di sintesi dashboard).

- **2026-07-17** — LINT/FIX urgente. L'utente ha riaperto la dashboard dopo
  il restyling sopra e ha segnalato tre problemi: sfondo ancora nero (non
  il grigio ardesia atteso), **codice HTML grezzo visibile a schermo**,
  mappe scure giudicate "brutte, troppi casini". Diagnosi:
  - **Bug reale**: `render_hero()` e `_stat_tile_html()` in `styling.py`
    costruivano l'HTML con f-string multi-riga indentate secondo lo stile
    del codice Python (8 spazi). CommonMark (il parser usato da
    `st.markdown`, anche con `unsafe_allow_html=True`) tratta una riga
    indentata di 4+ spazi come **blocco di codice letterale**, non come
    HTML da renderizzare — da qui il codice visibile a schermo. Di
    conseguenza hero/card/stats non diventavano mai HTML vero: lo sfondo
    "nero" visto dall'utente era semplicemente il tema scuro nativo di
    Streamlit (`#0e1117` da `.streamlit/config.toml`), non il token
    `THEME_INK` che non veniva mai applicato. Fix: entrambe le funzioni
    riscritte come singola riga (nessun `\n`/indentazione nell'HTML
    prodotto), stesso pattern già usato (e funzionante) in
    `render_nav_card_header()`. Verificato con `AppTest` che nessuno dei
    7 blocchi markdown della Home inizi più con whitespace/newline.
  - **Regressione non approvata**: le tile Folium scure
    (`CartoDB dark_matter`) non erano mai state validate su un mockup reale
    (quello approvato mostrava una mappa come illustrazione SVG statica,
    non un vero tile Folium) — le etichette/strade del tile scuro
    competevano visivamente con i poligoni colorati sovrapposti.
    **`MAP_TILES` riportato a `"CartoDB positron"`** su richiesta esplicita
    dell'utente, con commento nel codice per non riprovare senza
    rivalidazione.
  - Causa separata già risolta in questa stessa giornata (vedi voce
    precedente più `dashboard.md`): un processo Streamlit rimasto vivo da
    *prima* delle modifiche aveva ancora in cache la vecchia
    `components/constants.py` (`ImportError: MAP_TILES`) — non lo stesso
    bug, ma ha reso la diagnosi iniziale più confusa. Terminato l'intero
    albero di processi e riavviato pulito.

  Pagine aggiornate: `dashboard.md` (correzione nella sezione "Restyling
  identità visiva").

- **2026-07-17** — FIX. Dopo il fix del bug HTML sopra, l'utente ha
  confermato le card corrette ma segnalato che **lo sfondo resta piatto e
  nero**, con un accenno di blu isolato "a lato". Causa root, distinta dal
  bug precedente: `.streamlit/config.toml` → `[theme.dark]` usava ancora
  `backgroundColor = "#0e1117"` / `secondaryBackgroundColor = "#161a23"`,
  i valori quasi-neri della sessione 2026-07-15, **mai aggiornati** quando
  sono stati introdotti i token `THEME_INK`/`THEME_SURFACE` (grigio
  ardesia) in `constants.py` più sopra in questa stessa giornata. L'utente
  usa il tema **scuro** di Streamlit (il default dichiarato in
  `[theme]` è `base = "light"`, ma l'esperienza riportata — sfondo nero,
  non bianco — implica che l'abbia selezionato manualmente dal menu
  Streamlit): quindi vedeva lo sfondo nativo quasi-nero ovunque, con hero e
  card (di poco più chiari) che vi galleggiavano sopra senza fondersi —
  letto come "sfondo sempre nero" nonostante il restyling. Fix: allineati
  `[theme.dark]` e `[theme.dark.sidebar]` ai token `THEME_INK` (`#1c2130`),
  `THEME_SURFACE` (`#262c3d`), `THEME_TEXT` (`#f1f3f8`) e `primaryColor`
  portato a `THEME_COLD` (`#3498db`, invece del blu `#60a5fa` scollegato
  dalla palette) — così lo sfondo nativo di **tutte e 5 le pagine** (non
  solo gli elementi custom della Home) coincide con l'identità "calore".
  Verificato con `AppTest` (nessuna eccezione) e riavvio completo del
  server (i cambi a `config.toml` non si applicano con l'hot-reload,
  richiedono restart — nota già presente in `dashboard.md` dalla sessione
  2026-07-15). Tema chiaro (`[theme]`) non toccato: il problema segnalato
  riguardava solo il tema scuro.

  Pagine aggiornate: nessuna ancora — sezione dedicata da aggiungere a
  `dashboard.md` se l'utente conferma che il fix risolve.

  **Seguito, stesso giorno**: l'utente ha confermato lo sfondo corretto ma
  chiesto un colore diverso per la sidebar (prima identica al contenuto
  principale). Aggiunto `THEME_INK_SIDEBAR = "#161a26"` (leggermente più
  scuro di `THEME_INK`) in `constants.py`, applicato a
  `[theme.dark.sidebar].backgroundColor` in `config.toml`. Restart completo
  del server (richiesto per i cambi a `config.toml`).

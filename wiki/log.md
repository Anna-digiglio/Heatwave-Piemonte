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

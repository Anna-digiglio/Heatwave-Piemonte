# Pipeline ETL

**Sorgenti**: `src/data_acquisition/download_data.py`,
`src/data_acquisition/download_extra_municipalities.py`,
`src/data_processing/clean_data.py`, `src/database/load_to_db.py`, `docs/ETL.md`

## Extract — `download_data.py`

CLI: `python src/data_acquisition/download_data.py --years 2000:2026 --regions all --sources open_meteo,copernicus`

- `WeatherDataDownloader.download_all_regions()` itera le 8 province, chiama
  Open-Meteo per ciascuna con 3s di sleep tra una richiesta e l'altra,
  concatena in un unico DataFrame, salva in `data/raw/temperature_data.csv`.
- `download_historical_data()` gestisce i `429` (rate limit) con retry e
  backoff esponenziale (rispetta `Retry-After`, max 5 tentativi) — se anche
  dopo i retry una provincia fallisce, viene loggata e saltata (`continue`
  nel loop di `download_all_regions`), non persa silenziosamente come prima.
- Downloader analoghi per Copernicus ERA5, ARPA, ISTAT, OSM (vedi
  [Fonti Dati](data-sources.md) per stato/bug di ciascuno).
- **Eseguito realmente il 2026-07-04**: `data/raw/temperature_data.csv`
  popolato con 75.976 righe (8 province, 2000-2025, nessun nullo).

### Estensione a 44 comuni — `download_extra_municipalities.py` (2026-07-15)

Per rendere Moran's I e il clustering K-means (vedi
[Analisi Statistica](statistical-analysis.md)) statisticamente robusti
(n=8 era sotto la soglia comune di 20-30), aggiunto un secondo script:

- `select_extra_municipalities()` — campionamento "farthest-point" per
  provincia: sceglie comuni che massimizzano la distanza minima dai punti
  già scelti (partendo dal capoluogo), per coprire zone diverse (montagna,
  pianura, confini) invece di ammassarsi vicino a ciò che già c'è. 36 comuni
  extra, allocati proporzionalmente alla dimensione di ciascuna provincia.
- `WeatherDataDownloader.download_for_coordinates()` — refactoring di
  `download_historical_data()`: la logica di retry/backoff sui `429` è stata
  estratta in un metodo che accetta coordinate arbitrarie, non solo gli 8
  capoluoghi hardcoded in `PIEMONTE_REGIONS`.
- Output: `data/raw/temperature_data_extra.csv` (341.892 righe, 36 comuni).

**Bug reale scoperto in esecuzione**: 5 comuni su 36 sono falliti al primo
giro per `ConnectionResetError` (TLS reset, non un `429`) — il retry
esistente copre solo il rate limit, non errori di connessione generici.
Diagnosticato confrontando `municipality_id` scaricati vs selezionati;
risolto ri-scaricando miratamente solo i 5 mancanti.

## Transform — `clean_data.py`

CLI: `python -m src.data_processing.clean_data --input data/raw/temperature_data.csv`

Pipeline dentro `DataCleaner.clean_data()`, in ordine:

1. `load_data` — legge il CSV, conta record iniziali
2. `remove_duplicates` — dedup su `(date, province)`
3. `handle_missing_values` — interpolazione lineare (max 2 gap) su
   `temp_mean` per provincia, `precipitation` NaN → 0, drop righe senza
   `temp_max`/`temp_min`
4. inizializzazione `quality_flag = 0` per tutte le righe (vedi bug risolto
   sotto)
5. `validate_temperature` — flag `quality_flag=2` per valori fuori
   `[-50, 60]`, flag `quality_flag=1` per `temp_min > temp_max`
6. `detect_outliers` — IQR method (1.5×IQR) su `temp_max`, `temp_min`,
   `temp_mean`, flag `quality_flag=1`
7. `convert_dtypes` — cast a `float32`/`category`/`uint8` per efficienza
   memoria
8. `apply_quality_flags` — scarta righe con `quality_flag >= 2`
9. `generate_report` — log riassuntivo (record iniziali/finali, %completezza)

Output: `data/processed/temperature_clean.csv`.

**Nota di ordine + bug risolto (trovato da un unit test il 2026-07-15)**:
`validate_temperature` gira *prima* di `detect_outliers` — un valore fuori
range viene quindi usato per calcolare i quantili IQR prima di essere
eventualmente ri-flaggato. Peggio: `detect_outliers` sovrascriveva
**incondizionatamente** il flag a `1` (suspect) per qualunque outlier IQR,
**declassando** una riga già `quality_flag=2` (bad, fuori range fisico) a
`1` — che poi sopravviveva ad `apply_quality_flags` (scarta solo `>= 2`).
Scoperto da un test di regressione sintetico (vedi
[Test Unitari](testing.md)), non manifestato nei dati reali finora usati
(0 righe mai fuori range fisico né su `temperature_data.csv` né su
`temperature_data_extra.csv`) ma un bug di correttezza reale, ora corretto:
`detect_outliers` declassa a `1` solo se il flag attuale è `< 2`.

**Bug critici risolti il 2026-07-04, scoperti alla prima esecuzione reale
(il file non era mai stato eseguito prima d'ora):**
- **Il file non si importava affatto**: da `validate_temperature` in poi,
  gran parte del codice aveva newline letterali (`\n` come testo, non veri
  a capo) invece di righe vere — un `SyntaxError` bloccava l'import del
  modulo. Il file è stato riscritto da capo preservando la logica originale
  (visibile comunque leggendo il file, dato che il contenuto era corretto,
  solo "srotolato" su un'unica riga fisica).
- **Perdita quasi totale dei dati**: `validate_temperature`/`detect_outliers`
  valorizzano `quality_flag` solo per le righe sospette *prima* che la
  colonna esista — pandas la crea con `NaN` per tutte le altre righe.
  `apply_quality_flags` filtra con `quality_flag < 2`, e `NaN < 2` è `False`
  in pandas: **tutte le righe mai flaggate (la stragrande maggioranza)
  venivano scartate**. Su 75.976 righe di input sopravvivevano solo le 10
  esplicitamente flaggate come sospette. Fix: `df['quality_flag'] = 0`
  aggiunto esplicitamente in `clean_data()` prima di `validate_temperature`.
- Risultato dopo il fix: 75.976/75.976 righe mantenute, 10 flaggate
  `quality_flag=1` (giorni statisticamente estremi dell'ondata di freddo
  del febbraio 2012, non errori — `temp_min <= temp_mean <= temp_max`
  sempre rispettato).

**Riusato invariato il 2026-07-15** per `data/raw/temperature_data_extra.csv`
(i 36 comuni extra): `DataCleaner` raggruppa per la colonna `province`, che
in questo file contiene il nome del comune (non della provincia) — poiché
ogni nome è univoco tra i 36 selezionati, il raggruppamento funziona
correttamente come "per comune" senza modifiche al codice. 341.892/341.892
righe mantenute, 670 outlier statistici flaggati (prevalentemente nei comuni
alpini come Formazza/Macugnaga).

## Load — `load_to_db.py`

CLI: `python -m src.database.load_to_db` → `DatabaseLoader`

- `initialize_schema()` — esegue l'intero `sql/01_init_database.sql` sul
  cursore DBAPI grezzo (non via `exec_driver_sql`, vedi bug risolto sotto);
  idempotente grazie a `IF NOT EXISTS` (tabelle **e** indici) / `ON CONFLICT`
- `verify_schema()` — controlla che `provinces`, `municipalities`,
  `temperature` esistano
- `insert_municipalities()` — **carica i 1180 comuni reali** da
  `data/external/municipalities.csv` in `municipalities`, risolvendo
  `province_id` dal codice ISTAT di provincia (eseguito il 2026-07-04)
- ~~`insert_sample_province()`~~ — rimossa da `main()` (inseriva un record
  fittizio "Test Comune Piemonte" nella tabella `provinces` reale; il metodo
  resta disponibile ma non viene più chiamato automaticamente)
- `insert_temperature()` — **carica `data/processed/temperature_clean.csv`
  nella tabella `temperature`** a batch (`psycopg2.extras.execute_values`,
  `page_size=5000`), eseguito il 2026-07-04. I dati Open-Meteo sono per
  provincia (1 stazione = il capoluogo), non per comune: ogni riga viene
  associata al **comune capoluogo di provincia** (unico comune per cui
  esiste davvero una misura — scelta confermata con l'utente, alternativa
  scartata era rendere `municipality_id` nullable e trattare i dati come
  "di livello provinciale"). Mappatura nome-capoluogo per provincia
  coincide col nome provincia in 7 casi su 8; eccezione:
  "Verbano-Cusio-Ossola" (nome dell'ente) ha come capoluogo il comune di
  "Verbania".
- `insert_temperature_for_municipalities()` (2026-07-15) — variante per
  CSV che hanno già `municipality_id` per riga (non serve risolvere il
  capoluogo per nome): usata per caricare i 36 comuni extra da
  `data/processed/temperature_clean_extra.csv`. **Copertura totale ora: 44
  comuni, 417.868 righe** in `temperature`.

**Bug risolti il 2026-07-04, scoperti eseguendo il caricamento reale:**
- `exec_driver_sql` passa sempre un dict di parametri (anche vuoto) a
  psycopg2, che quindi interpreta ogni `%` letterale nello script SQL come
  segnaposto di parametro (paramstyle pyformat) — falliva su
  `'% of data completeness'` in `01_init_database.sql`. Fix: esecuzione
  tramite cursore DBAPI grezzo (`conn.connection.cursor()`).
- `metadata.value` era `NOT NULL` ma il seed inserisce `NULL` per
  `last_etl_run` — rimosso il vincolo (vedi [Modello Dati](data-model.md)).
- `municipalities.geometry` era `GEOMETRY(POLYGON, 4326)` ma 74/1180 comuni
  reali hanno confini `MULTIPOLYGON` (exclavi) — colonna cambiata a
  `MULTIPOLYGON`, insert avvolto in `ST_Multi(...)`.
- Tutti i `CREATE INDEX` nello script DDL non avevano `IF NOT EXISTS`
  (a differenza delle `CREATE TABLE`), rompendo la ri-esecuzione dello
  script su un DB parzialmente inizializzato — aggiunto `IF NOT EXISTS`
  a tutti (24 occorrenze).

**Stato attuale (2026-07-15)**: pipeline Extract → Transform → Load
completa ed eseguita end-to-end su dati reali. Non esiste ancora un
orchestratore unico `etl_pipeline.py` (si lanciano gli script separatamente,
in ordine); i `models.py` menzionati in `PROJECT_SUMMARY.md` non esistono.
Il "Load" reale oggi copre: schema + 8 province + 1180 comuni + 417.868
righe di temperatura per **44 comuni** (8 capoluoghi + 36 extra selezionati
per copertura spaziale, 2000-2025).

## Passaggi pianificati ma non ancora scritti

- Calcolo KPI giornalieri/annuali lato Python (oggi solo le viste
  materializzate SQL calcolano aggregati, vedi [Modello Dati](data-model.md))
- Trigger di `identify_heatwaves()` dopo il caricamento (mai eseguita su
  dati reali — ora possibile, `temperature` è popolata)
- Refresh delle viste materializzate post-load
- Un orchestratore unico che concatena i 3 script (oggi lanciati a mano in
  sequenza: `download_data.py` → `clean_data.py` → `load_to_db.py`)

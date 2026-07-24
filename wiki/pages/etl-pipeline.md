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

> **Nota di ordine + bug risolto** (trovato da un unit test il
> 2026-07-15): `validate_temperature` gira *prima* di `detect_outliers` —
> un valore fuori range viene quindi usato per calcolare i quantili IQR
> prima di essere eventualmente ri-flaggato. Peggio: `detect_outliers`
> sovrascriveva **incondizionatamente** il flag a `1` (suspect) per
> qualunque outlier IQR, **declassando** una riga già `quality_flag=2`
> (bad, fuori range fisico) a `1` — che poi sopravviveva ad
> `apply_quality_flags` (scarta solo `>= 2`). Scoperto da un test di
> regressione sintetico (vedi [Test Unitari](testing.md)), non
> manifestato nei dati reali finora usati (0 righe mai fuori range fisico
> né su `temperature_data.csv` né su `temperature_data_extra.csv`) ma un
> bug di correttezza reale, ora corretto: `detect_outliers` declassa a
> `1` solo se il flag attuale è `< 2`.

**Bug critici risolti il 2026-07-04**, scoperti alla prima esecuzione
reale (il file non era mai stato eseguito prima d'ora):

- **Il file non si importava affatto**: da `validate_temperature` in poi,
  gran parte del codice aveva newline letterali (`\n` come testo, non
  veri a capo) invece di righe vere — un `SyntaxError` bloccava l'import
  del modulo. Il file è stato riscritto da capo preservando la logica
  originale (visibile comunque leggendo il file, dato che il contenuto
  era corretto, solo "srotolato" su un'unica riga fisica).
- **Perdita quasi totale dei dati**: `validate_temperature`/
  `detect_outliers` valorizzano `quality_flag` solo per le righe sospette
  *prima* che la colonna esista — pandas la crea con `NaN` per tutte le
  altre righe. `apply_quality_flags` filtra con `quality_flag < 2`, e
  `NaN < 2` è `False` in pandas: **tutte le righe mai flaggate (la
  stragrande maggioranza) venivano scartate**. Su 75.976 righe di input
  sopravvivevano solo le 10 esplicitamente flaggate come sospette. Fix:
  `df['quality_flag'] = 0` aggiunto esplicitamente in `clean_data()`
  prima di `validate_temperature`.
- Risultato dopo il fix: 75.976/75.976 righe mantenute, 10 flaggate
  `quality_flag=1` (giorni statisticamente estremi dell'ondata di freddo
  del febbraio 2012, non errori — `temp_min <= temp_mean <= temp_max`
  sempre rispettato).

**Riusato invariato il 2026-07-15** per
`data/raw/temperature_data_extra.csv` (i 36 comuni extra): `DataCleaner`
raggruppa per la colonna `province`, che in questo file contiene il nome
del comune (non della provincia) — poiché ogni nome è univoco tra i 36
selezionati, il raggruppamento funziona correttamente come "per comune"
senza modifiche al codice. 341.892/341.892 righe mantenute, 670 outlier
statistici flaggati (prevalentemente nei comuni alpini come
Formazza/Macugnaga).

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

**Bug risolti il 2026-07-04**, scoperti eseguendo il caricamento reale:
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

**Stato attuale (2026-07-17)**: pipeline Extract → Transform → Load
completa ed eseguita end-to-end su dati reali. Non esiste ancora un
orchestratore unico `etl_pipeline.py` (si lanciano gli script separatamente,
in ordine); i `models.py` menzionati in `PROJECT_SUMMARY.md` non esistono.
Il "Load" reale oggi copre: schema + 8 province + 1180 comuni + 1.716.094
righe di temperatura per **177 comuni** (8 capoluoghi + 169 extra
selezionati per copertura spaziale), dal 2000 **fino a oggi** (non più
fermo al 31/12/2025).

### Estensione a 63 comuni + dati fino ad oggi (2026-07-17)

Su richiesta dell'utente di coprire tutti i 1180 comuni e portare i dati
fino ad oggi, scoperto un **limite giornaliero** delle richieste
Open-Meteo (oltre a quello "al minuto" già noto) — vedi
[Fonti Dati](data-sources.md) per il racconto completo (due tentativi
falliti, ~5h40 di download perso perché il primo script salvava solo a
fine esecuzione). Obiettivo ridimensionato da 1180 a un incremento
sostenibile: **+19 comuni** (44→63), scaricati a lotti piccoli con
salvataggio incrementale (fix strutturale: ogni comune scaricato viene
subito scritto su disco, non solo alla fine).

Nuovo script `src/data_acquisition/update_recent_data.py`: estende **tutti
i comuni già presenti** (non solo i nuovi) fino alla data più recente
disponibile, scaricando solo il **delta** (dal giorno dopo l'ultima data
nota) per ciascuno — evita di ri-scaricare 26 anni di storico già
presenti, e soprattutto evita duplicati (`temperature` non ha un vincolo
di unicità `(municipality_id, date)`).

`download_extra_municipalities.py` reso **parametrico** (`--count`,
allocazione proporzionale per provincia calcolata dal vivo via
`compute_target_per_province()`, non più pesi fissi tarati per un numero
specifico di comuni) — permette lotti piccoli (anche 10) per scoprire
empiricamente la soglia del rate limit senza dover editare il codice ogni
volta.

**Bug reale trovato grazie ai dati 2026**: `frequency_by_year()` in
`src/analysis/heatwave_stats.py` aveva un `reindex(range(2000, 2026))`
fisso — scartava in silenzio le ondate rilevate nel 2026 (16 ondate
nascoste) ora che la serie storica arriva oltre il 2025 per la prima
volta. Fix: range dinamico dal min/max anno realmente presente nei dati.
Stesso bug, stessa causa (limite fisso scritto quando "andava bene così",
mai più rivisitato), trovato anche in `dashboard/components/filters.py`
(`YEAR_MIN, YEAR_MAX = 2000, 2025` fisso) — reso dinamico dalla data reale
in `temperature`.

## Import dei 35 comuni extra dalla seconda macchina (2026-07-17)

Vedi [Fonti Dati](data-sources.md#download-collaborativo-da-una-seconda-macchina--35-comuni-extra-2026-07-17)
per il racconto completo di come sono stati ottenuti (sessione da una
seconda macchina, senza accesso diretto al DB del titolare, comuni
mancanti dedotti dalle preview PNG dei progetti QGIS).

**File consegnati** (fuori da Git, `data/raw/` — recuperati dal canale
usato per la consegna, non da `git pull`), **poi uniti e rimossi come file
separati** (vedi in fondo alla sezione):

- `data/raw/temperature_data_extra_helper_35comuni.csv` — 339.325 righe,
  35 comuni, 2000-01-01 → 2026-07-17. Colonne:
  `date, temp_max, temp_min, temp_mean, precipitation, province, data_source,
  istat_code, province_name`. `istat_code` già zero-paddato a 6 cifre come
  stringa nel file.
- `data/raw/riepilogo_35_comuni_extra.csv` — tabella di sintesi rapida
  (comune, provincia, `istat_code`, n. righe, data min/max).

Il file non era ancora nel formato atteso da
`insert_temperature_for_municipalities()` (aveva `istat_code`, non
`municipality_id` — chi l'ha scaricato da un'altra macchina non aveva
accesso alla tabella `municipalities` del titolare). Import eseguito con
uno script una tantum (non aggiunto al repo, operazione non ripetibile
allo stesso modo): letto il CSV con `dtype={'istat_code': str}` (leggerlo
con `DataCleaner.load_data()`/`pd.read_csv()` senza specificare il dtype
avrebbe fatto interpretare la colonna come intera, perdendo gli zeri
iniziali — stessa classe di problema già vista con l'encoding ISTAT),
passato manualmente attraverso gli stessi passi di `DataCleaner.clean_data()`
(0 righe scartate, 666 outlier IQR flaggati), poi risolto `istat_code` →
`municipality_id` via join contro `municipalities` (tutti e 35 i codici
trovati, nessuna sovrapposizione con i 63 comuni già caricati) prima di
chiamare `insert_temperature_for_municipalities()`.

**Risultato verificato nel DB**: 950.110 righe in `temperature`
(+339.325), **63 → 98 comuni**, range invariato 2000-01-01 → 2026-07-17.

**Ricalcolo a valle** (stesso giro delle estensioni precedenti, vedi
[Stato del Progetto](project-status.md)):
- Elevazione ri-scaricata per tutti i comuni con temperatura
  (`fetch_elevation.py`, query per costruzione limitata ai comuni con dati
  — copre automaticamente anche i 35 nuovi): 98/98 popolati.
- `TRUNCATE heatwave_events` + `identify_heatwaves()`: **331 ondate**
  (+141 rispetto a 190).
- Refresh viste materializzate: `kpi_annual_by_municipality` 2.646 righe
  (98 comuni × 27 anni), `kpi_annual_by_province` 216 righe (8 × 27).
- Tutti e 5 i moduli di `src/analysis/` (inclusa la prima iterazione del
  modello di regressione spaziale) rieseguiti su 98 comuni — vedi
  [Analisi Statistica](statistical-analysis.md) per i risultati.
- Mappe QGIS rigenerate (`python-qgis-ltr.bat build_maps.py`).

**Pulizia dei file consegnati (stessa sessione, su richiesta dell'utente)**:
una volta importati i dati nel DB, i due file consegnati dalla
collaboratrice erano ridondanti (il loro contenuto vive già in
`temperature` e in questa pagina). Uniti invece di lasciarli come file
separati: le 339.325 righe di `temperature_data_extra_helper_35comuni.csv`
sono state riformattate allo schema di `data/raw/temperature_data_extra.csv`
(`istat_code` → `municipality_id`, stessa risoluzione già fatta per
l'import) e appese in coda (526.078 → **865.403 righe**). `temperature_data_extra.csv`
resta quindi l'unico file raw per i comuni "extra" (oltre agli 8
capoluoghi in `temperature_data.csv`), a prescindere da quale sessione o
macchina abbia scaricato quali righe. `riepilogo_35_comuni_extra.csv`
eliminato senza sostituto: era solo una tabella di comodo per ispezionare
il file senza aprirlo, resa inutile dall'import. Entrambi i file
originali della collaboratrice **non esistono più** in `data/raw/` —
questa sezione ne descrive il contenuto e il flusso per intero, dato che
la wiki resta la sola documentazione di come sono stati ottenuti e
importati. **Consolidamento anche di `data/processed/`** (stessa sessione, richiesta
esplicita dell'utente subito dopo l'unione dei raw): la cartella aveva
accumulato 5 file da sessioni diverse — `temperature_clean.csv` (8
capoluoghi, fermo al 2025-12-31), `temperature_clean_extra.csv` (55
comuni, già esteso fino al 2026-07-16), `temperature_clean_extra_delta.csv`
(19 comuni, **sottoinsieme già interamente contenuto** in
`temperature_clean_extra.csv` — verificato confrontando gli ID comune
prima di toccare nulla), `temperature_clean_recent.csv` (delta
2026-01-01→2026-07-17 per tutti i 63 comuni preesistenti, **zero righe in
comune** con gli altri file, verificato su `(municipality_id, date)` prima
di unire) e il neonato `temperature_extra_35_clean.csv`. Consolidati in
due soli file, replicando esattamente la stessa distinzione già presente
nei loader (`insert_temperature()` per nome vs
`insert_temperature_for_municipalities()` per ID):

- `temperature_clean.csv` — **solo 8 capoluoghi**: aggiunta la quota
  2026 dei capoluoghi estratta da `temperature_clean_recent.csv` (1.584
  righe). Attenzione alla colonna `province`: nel file di `update_recent_data.py`
  usa il **nome del comune** (`"Verbania"`), mentre lo schema storico di
  questo file usa il **nome della provincia** (`"Verbano-Cusio-Ossola"`) —
  rinominato per coerenza interna prima di appendere, altrimenti un
  futuro `insert_temperature()` non avrebbe trovato la provincia. 75.976
  → **77.560 righe**.
- `temperature_clean_extra.csv` — **tutti i comuni non-capoluogo (90)**:
  unite le 339.325 righe di `temperature_extra_35_clean.csv` (tolta la
  colonna `istat_code`, non più necessaria dato che il file ha già
  `municipality_id`) e le 7.147 righe extra di
  `temperature_clean_recent.csv` (aggiunta `province_name`, assente in
  quel file, via join `municipality_id` → `provinces.name`). 526.078 →
  **872.550 righe**.
- Eliminati (contenuto assorbito, nessuna perdita):
  `temperature_clean_extra_delta.csv`, `temperature_clean_recent.csv`,
  `temperature_extra_35_clean.csv`.

**Verificato prima di eliminare nulla**: zero righe duplicate su
`(municipality_id, date)` nel file extra consolidato e su `(province,
date)` nel file capoluoghi; **77.560 + 872.550 = 950.110**, combacia
esattamente col totale in `temperature` nel DB. `data/processed/` ora
contiene solo questi 2 file.

## Comuni extra — 57 dalla collaboratrice + 22 scaricati direttamente (2026-07-18)

Seconda sessione della stessa collaboratrice, stessa macchina esterna
senza accesso al DB. A differenza della sessione del giorno prima, questa
volta **non è servita nessuna ricostruzione dai PNG QGIS**: dopo il
`git pull`, la nuova pagina [Comuni già coperti](comuni-coperti.md)
(creata dal titolare apposta dopo l'import dei 35 comuni) elencava i 98
comuni già in `temperature` con nome e codice ISTAT esatti — presa come
fonte diretta per il campionamento "farthest-point" (stesso algoritmo di
`download_extra_municipalities.py`, rieseguito localmente sui 1082 comuni
rimanenti).

**Download della collaboratrice**: `WeatherDataDownloader.download_for_coordinates()`,
lotti da 20 con salvataggio incrementale, stesso pattern collaudato. Il
rate limit giornaliero è scattato dopo **57 comuni riusciti** (bloccato
su "Cannobio" dopo 5 tentativi con backoff fino a 80s) — nessun doppione
stavolta (verificato: 552.672 righe = 57 comuni × 9.696 giorni esatti,
zero righe duplicate su `(comune, data)`), a differenza della sessione
precedente dove un bug di confronto `int`/`str` aveva causato download
ripetuti.

**File consegnati** (fuori da Git, `data/raw/` — stesso canale della
volta precedente): `temperature_data_extra_helper_batch2.csv` (552.672
righe, 57 comuni, stesse colonne del lotto precedente, `istat_code` già
zero-paddato) e `riepilogo_57_comuni_batch2.csv`.

> **File stantio ricevuto per errore, scartato senza importarlo**:
> insieme al lotto nuovo era presente anche
> `temperature_data_extra_helper_35comuni.csv` — **stesso nome, stesso
> numero di righe (339.325), stessi 35 codici ISTAT** del file già
> importato ed eliminato il giorno prima. Verificato prima di toccarlo:
> tutti e 35 quei comuni erano già in `temperature`, e la voce di log
> della collaboratrice stessa (sopra) menziona solo `batch2` come file
> prodotto in questa sessione — quasi certamente una copia locale non
> aggiornata dopo il `git pull` precedente, ricomparsa per errore nella
> stessa consegna. Cancellato senza importarlo: importarlo avrebbe
> duplicato 339mila righe già presenti, corrompendo silenziosamente
> ondate/KPI/analisi (nessun vincolo di unicità `(municipality_id,
> date)` in `temperature`).

**Import di `batch2`**: pulizia via `DataCleaner.clean_data()` (0 righe
scartate), risoluzione `istat_code` → `municipality_id` via join su
`municipalities` (57/57 trovati), caricamento con
`insert_temperature_for_municipalities()`. **98 → 155 comuni**.

**Download aggiuntivo, eseguito direttamente** (`--count 40`): la
selezione automatica di `download_extra_municipalities.py` esclude per
costruzione i comuni già in `temperature` (query live), quindi non poteva
sovrapporsi né ai 155 già presenti né a quelli appena importati dalla
collaboratrice. Il rate limit giornaliero (già in parte consumato dalla
collaboratrice nella stessa giornata) è scattato dopo **22 comuni
riusciti** su 40 richiesti. **Comportamento diverso dai blocchi
precedenti**: nessun errore `429` esplicito osservato — il processo è
rimasto "vivo" ma **fermo per oltre 12 minuti senza scrivere righe
nuove** e con tempo CPU sostanzialmente piatto, un pattern più simile a
un blocco nei retry silenzioso che a un fallimento pulito. Interrotto
manualmente dopo aver verificato che i 22 comuni già scaricati erano
completi (9.696 righe ciascuno, nessuna riga parziale — il salvataggio
incrementale scrive un comune alla volta, quindi l'interruzione non ha
corrotto nulla) e importati normalmente. **155 → 177 comuni**.

**Bug reale trovato e corretto durante il ricalcolo a valle**:
`fetch_elevation.py` interrogava l'Elevation API di Open-Meteo in
un'unica richiesta con tutte le coordinate — funzionava fino a 100
comuni, ma con 177 ha restituito `400 Bad Request`
(`"Parameter 'latitude' and 'longitude' must not exceed 100
coordinates"`, letto direttamente dal corpo della risposta). Fix:
`fetch_elevations()` ora spezza le richieste in lotti da
`MAX_COORDS_PER_REQUEST = 100`, unendo i risultati — nessun impatto sul
resto della pipeline, il limite tornerà rilevante ogni volta che il
campione di comuni supererà un multiplo di 100.

**Ricalcolo a valle completo**: elevazione ri-scaricata per tutti i 177
comuni (col fix sopra), `TRUNCATE heatwave_events` + `identify_heatwaves()`
(**640 ondate**, da 331), `REFRESH MATERIALIZED VIEW` su entrambe le
viste KPI (`kpi_annual_by_municipality` 4.779 righe, `kpi_annual_by_province`
216), tutti e 5 i moduli di `src/analysis/` rieseguiti, mappe QGIS
rigenerate.

**Consolidamento file** (stesso pattern del giorno prima, richiesta
esplicita dell'utente): in `data/raw/`, `batch2` unito in
`temperature_data_extra.csv` (istat_code → municipality_id) ed eliminato
insieme al file stantio dei 35 comuni e al riepilogo, ormai ridondanti —
`data/raw/` torna a 4 file. In `data/processed/`, i due file puliti di
oggi (`temperature_extra_batch2_clean.csv`,
`temperature_extra_newbatch_clean.csv`) uniti in
`temperature_clean_extra.csv` dopo aver verificato zero sovrapposizioni
su `(municipality_id, date)` — `data/processed/` resta a 2 file.
Verificato **77.560 + 1.638.534 = 1.716.094**, combacia esattamente col
totale reale in `temperature`.

**Pagina [Comuni già coperti](comuni-coperti.md) aggiornata** con
l'elenco completo dei 177 comuni e una nota rivista sul limite
giornaliero di Open-Meteo: non un numero fisso (19-20 la prima volta, 57
per la collaboratrice e 22 per il titolare lo stesso giorno) — l'ipotesi
di un limite legato al volume di dati più che al conteggio delle
richieste resta non confermata ma coerente con le osservazioni.

## Validazione ARPA — nuova pipeline parallela (2026-07-18)

Fase 1 del piano paper ([Articolo scientifico](paper-scientifico.md)),
priorità più alta, mai risolta prima (l'URL configurato in `config.yaml`
per `arpa_piemonte` risponde 404 da sempre). Trovata via ricerca web
un'API REST pubblica reale di ARPA Piemonte — vedi
[Fonti dati](data-sources.md#arpa-piemonte--integrata-e-scaricata-2026-07-18)
per il dettaglio completo della scoperta e dei due gotcha di comportamento
dell'API (filtri di data silenziosamente ignorati, paginazione fissa).

Nuova pipeline **indipendente** da quella Open-Meteo (fonte diversa, nessuna
sovrapposizione di codice):

1. **Extract**: `src/data_acquisition/download_arpa.py` — scarica
   l'anagrafica stazioni ARPA, seleziona la stazione con sensore di
   temperatura attivo più vicina (per quota) a ciascuno dei 177 comuni già
   coperti da Open-Meteo (51 match trovati), scarica i giornalieri per
   ciascuna stazione con salvataggio incrementale (stessa lezione imparata
   con Open-Meteo — un'interruzione a metà non deve far perdere il
   progresso). Eseguito realmente: 51/51 comuni, 451.502 righe
   (`data/raw/arpa_temperature.csv`), un solo fallimento transitorio
   (`Remote end closed connection`, non un limite di rate) risolto
   ri-scaricando la singola stazione.
2. **Load**: nuovo metodo `DatabaseLoader.insert_arpa_temperature()` in
   `load_to_db.py` (stesso pattern di `insert_temperature_for_municipalities`,
   `ON CONFLICT (station_code, date) DO NOTHING`), tabella
   `arpa_temperature` (`sql/05_arpa_temperature.sql`, applicato manualmente
   come per `03_land_cover.sql`/`04_ndvi.sql` — non fa parte di
   `01_init_database.sql`). Nessun passaggio `clean_data.py`: i dati ARPA
   non passano dal `DataCleaner` (pensato per il formato Open-Meteo), i
   valori nulli nei sensori più vecchi restano tali, gestiti a valle nel
   confronto (`dropna()` per coppia di osservazioni).
3. **Confronto**: `src/analysis/validate_arpa.py` — join
   `temperature`/`arpa_temperature` su `(municipality_id, date)`, bias/MAE/
   RMSE/correlazione di Pearson per comune su `temp_max`/`temp_min`/
   `temp_mean`. Risultati in `output/arpa_validation.csv` — vedi
   [Analisi statistica](statistical-analysis.md) per i numeri reali.

## Comuni extra mirati alla validazione ARPA — 158 comuni target (2026-07-19)

> **Nota importante sull'obiettivo reale di questi download** (vedi anche
> [Comuni già coperti](comuni-coperti.md#correzione-stessa-giornata)):
> **l'obiettivo reale della richiesta dell'utente non era "estendere la
> copertura spaziale genericamente", ma scaricare Open-Meteo per i comuni
> che hanno già una stazione ARPA attiva ma non hanno ancora dati
> Open-Meteo, per completare la mappa Bias Open-Meteo↔ARPA per comune**
> (vedi [Validazione ARPA](#validazione-arpa--nuova-pipeline-parallela-2026-07-18)
> sopra). Un primo tentativo del 2026-07-19, partito da un fraintendimento,
> aveva scaricato 18 comuni della sola provincia di Torino con un
> campionamento spaziale generico (`farthest_point_sample`, lo stesso
> criterio delle sessioni precedenti) — corretto in giornata dal titolare
> non appena chiarito l'obiettivo reale (9 di quei 18 comuni si sono
> rivelati utili per puro caso, avendo anche una stazione ARPA attiva).
> Questa sessione riparte **da qui**: target esplicito, non un
> campionamento.

**Fonte del target**: la sezione
["I 167 comuni ARPA senza Open-Meteo"](comuni-coperti.md#obiettivo-reale-completare-la-mappa-bias-open-meteoarpa)
di `comuni-coperti.md`, scritta dal titolare — lista esatta con nome e
codice ISTAT, non un criterio geometrico da ricalcolare. Di questi 167,
9 erano già stati scaricati (per caso) nel tentativo mal indirizzato
della mattina, non ancora importati: **158 comuni restanti**, presi come
target diretto di questa sessione (parsing della tabella markdown, non
trascrizione a mano, per evitare errori su 158 righe).

**Ordine di download**: interlacciato per provincia (round-robin, un
comune a testa per provincia a turno) invece che nell'ordine della
tabella — se la quota giornaliera si esaurisce a metà, questo garantisce
comunque un contributo distribuito su tutte le 8 province invece di
finire, ad esempio, tutta la provincia di Cuneo (47 comuni, la più
numerosa nella lista) e nessun altro.

**Download**: stesso `WeatherDataDownloader.download_for_coordinates()`,
storico completo 2000-01-01 → oggi (non un delta: il confronto di bias
richiede serie storiche complete, non un giorno), salvataggio incrementale
comune per comune, ripresa automatica dei comuni già scaricati se il
CSV di output esiste già da un run precedente interrotto.

**Risultato reale**: bloccato dalla quota giornaliera dopo **57/158 comuni**
riusciti (su "Candia Canavese", stesso pattern di backoff crescente già
visto — 5s→10s→20s→40s→80s), 1 solo fallimento. Verificato senza
doppioni: 552.729 righe = 57 comuni × 9.697 giorni esatti, zero righe
duplicate su `(comune, data)`. Distribuzione ottenuta grazie
all'interlacciamento per provincia: tutte e 8 le province rappresentate
(Alessandria 8, Asti 8, Biella 7, Cuneo 8, Novara 5, Torino 7,
Verbano-Cusio-Ossola 7, Vercelli 7) invece di esaurire prima le più
numerose. **Restano 101 dei 158 comuni target** per le prossime sessioni
(dopo il reset quota).

**File consegnato** (fuori Git, `data/raw/`, stesso canale delle sessioni
precedenti):

- `data/raw/temperature_data_extra_helper_arpa_target.csv` — 552.729
  righe, 57 comuni, 2000-01-01 → 2026-07-19. Colonne identiche ai lotti
  precedenti (`date, temp_max, temp_min, temp_mean, precipitation,
  province, data_source, istat_code, province_name`).
- `data/raw/riepilogo_57_comuni_arpa_target.csv` — tabella di sintesi.

**Non ancora importato**: stessi passaggi delle sessioni precedenti —
pulizia + risoluzione `istat_code` → `municipality_id`, poi
`insert_temperature_for_municipalities()`. **Passaggio aggiuntivo
specifico a questo lotto**: dopo l'import in `temperature`, rilanciare
anche `download_arpa.py --only-uncovered` (o senza il flag, dato che
questi comuni ora avranno Open-Meteo) per far crescere di conseguenza
anche `arpa_temperature` e quindi il numero di comuni utilizzabili nel
confronto di bias — l'obiettivo reale di questo lotto non è il numero di
comuni in `temperature` di per sé, ma il numero di comuni con **entrambe**
le fonti.

## Comuni extra mirati alla validazione ARPA — terza tranche, 57/101 (2026-07-20)

Terza sessione consecutiva della stessa collaboratrice, stesso obiettivo
(vedi nota sopra: completare la mappa Bias Open-Meteo↔ARPA, non
un'estensione spaziale generica). Target ricalcolato da zero all'inizio
sessione: dei 167 comuni ARPA-senza-Open-Meteo originali, sottratti sia i
9 già scaricati dal titolare (Torino, 2026-07-19 mattina) sia i 57 di
questa stessa collaboratrice del giorno prima (ormai importati, **234
comuni** confermati in `temperature` da
[Comuni già coperti](comuni-coperti.md#stato-al-2026-07-19-import-comuni-arpa-target-dalla-collaboratrice)) —
**101 comuni target** residui, calcolati incrociando la tabella dei 167
con `data/raw/riepilogo_57_comuni_arpa_target.csv` (il proprio riepilogo
del giorno prima, fonte più affidabile dei marcatori ✅ nella tabella
wiki, che non erano stati aggiornati dopo l'import). Stesso ordine
interlacciato per provincia delle sessioni precedenti.

**Risultato**: bloccato dalla quota giornaliera dopo **57/101 comuni**
(su "Monastero di Lanzo", stesso pattern di backoff 5s→10s→20s→40s→80s)
— **terza volta di fila che il blocco arriva esattamente a 57 comuni**,
possibile indizio che la quota giornaliera reale sia più stabile di
quanto ipotizzato in precedenza (non confermato, resta un'osservazione
empirica su 3 sessioni). Verificato senza doppioni: 552.786 righe = 57 ×
9.698 giorni esatti, zero righe duplicate. **Restano 44 dei 101 comuni**
di questa tranche (= 44 dei 167 originali) per le prossime sessioni.

**File consegnato** (fuori Git, `data/raw/`, stesso canale):
- `data/raw/temperature_data_extra_helper_arpa_target_day3.csv` — 552.786
  righe, 57 comuni, 2000-01-01 → 2026-07-20. Stesse colonne dei lotti
  precedenti.
- `data/raw/riepilogo_57_comuni_arpa_target_day3.csv` — tabella di
  sintesi.

**Non ancora importato**: stessi passaggi delle sessioni precedenti.

## Estensione generale ripresa dopo l'obiettivo ARPA — 85 comuni (2026-07-21)

Con i 167 comuni ARPA-target completati (vedi sezione sotto), la
collaboratrice è tornata al criterio di estensione **generale** della
copertura (non più mirato ad ARPA) — stesso algoritmo delle sessioni
originarie (`compute_target_per_province()` + `farthest_point_sample()`
per provincia), sui **331 comuni già coperti** (fonte:
[Comuni già coperti](comuni-coperti.md), tabella per provincia
rigenerata dal titolare il 2026-07-20, che include sia i comuni in
`temperature` sia quelli su file raw pendenti — vedi sotto).

**Risultato**: **85 comuni** scaricati con successo (il lotto singolo più
numeroso di tutta questa serie di sessioni, oltre il 50% in più del
massimo precedente di 57), bloccato dalla quota giornaliera su "Benna"
dopo 1 solo fallimento. Distribuzione su tutte e 8 le province
(Alessandria 15, Asti 10, Biella 4, Cuneo 16, Novara 8, Torino 20,
Verbano-Cusio-Ossola 4, Vercelli 8). Verificato senza doppioni: 824.415
righe = 85 × 9.699 giorni esatti.

**File consegnato** (fuori Git, `data/raw/`, stesso canale):
- `data/raw/temperature_data_extra_helper_general_20260722.csv` —
  824.415 righe, 85 comuni, 2000-01-01 → 2026-07-21. Stesse colonne di
  sempre.
- `data/raw/riepilogo_85_comuni_generale.csv` — tabella di sintesi.

**Non ancora importato**: resta in coda con gli altri lotti pendenti
(vedi nota del titolare del 2026-07-20 su accumulo senza import/ricalcolo
a ogni sessione). Se importato insieme al resto del backlog: **331 → 416
comuni** in `temperature`.

## Comuni extra mirati alla validazione ARPA — ultimo lotto, obiettivo completato (2026-07-21)

Quinta e ultima sessione della stessa collaboratrice su questo obiettivo.
Dopo `git pull`, la wiki (`comuni-coperti.md`) elencava per nome i **22
comuni rimasti** su tutti i 167 originari (167 - 9 Torino - 57 - 57 - 22
del titolare/IA il 2026-07-20) — presi direttamente senza bisogno di
ricalcolare/interlacciare nulla, essendo un lotto piccolo (22 comuni,
quasi tutti in provincia di Torino).

**Risultato**: **22/22 riusciti, nessun fallimento, quota non toccata**
— primo lotto di questa serie a completarsi interamente in una sola
sessione senza bloccarsi. **La lista dei 167 comuni ARPA-target è ora
scaricata al 100%** (storico completo 2000-01-01 → oggi per tutti).
Verificato senza doppioni: 213.378 righe = 22 × 9.699 giorni esatti.

**File consegnato** (fuori Git, `data/raw/`, stesso canale):
- `data/raw/temperature_data_extra_helper_arpa_final22.csv` — 213.378
  righe, 22 comuni, 2000-01-01 → 2026-07-21. Stesse colonne di sempre.
- `data/raw/riepilogo_22_comuni_arpa_final.csv` — tabella di sintesi.

**Non ancora importato** — stessi passaggi delle sessioni precedenti,
ma qui con una nota in più: il titolare ha deciso (2026-07-20) di
**accumulare senza importare/ricalcolare a ogni sessione** (il ricalcolo
completo richiede ore), quindi questo file resta in coda insieme agli
altri lotti pendenti (day1/day3 della collaboratrice, il lotto Torino,
il lotto da 22 del titolare/IA del 2026-07-20) fino al prossimo giro di
import unico. **Con questo lotto, tutti i comuni necessari per
completare la mappa Bias Open-Meteo↔ARPA sono stati scaricati** — al
prossimo import/ricalcolo, la mappa potrà usare la copertura ARPA
completa (218/218 comuni con stazione attiva, invece dei 108 attuali).

## Estensione generale, metodo DB-free — 57 comuni (2026-07-22)

Su richiesta dell'utente, nuovo lotto di estensione generale, stesso
algoritmo delle sessioni precedenti (`compute_target_per_province()` +
`farthest_point_sample()` per provincia) ma eseguito da una macchina
**senza accesso al database Postgres/PostGIS** (nessun `.env`, solo
`config.yaml` con placeholder) — stesso vincolo della collaboratrice
delle sessioni precedenti, qui pero' senza nemmeno il canale per farsi
mandare i dati da lei. Le due funzioni che in
`download_extra_municipalities.py` interrogano il DB
(`load_all_municipalities()`, `already_downloaded_ids()`) sono state
sostituite con fonti locali equivalenti (script separato, non nel
repository — vedi nota sotto sul perche'):

- **1180 comuni + coordinate**: join tra lo shapefile ufficiale ISTAT
  (`data/external/istat_confini/Com01012026_g/`, filtrato `COD_REG==1`) e
  `data/dashboard_export/municipality_metadata_all.parquet` (lat/lon
  gia' esportati per la dashboard, vedi [Dashboard](dashboard.md)).
  **Bug scoperto**: il `.dbf` dello shapefile ha i nomi con lettere
  accentate corrotti (bytes UTF-8 decodificati come Latin-1, "Agliè"
  letto come "AgliÃ¨") — 28/1180 comuni non si univano per nome finche'
  non corretto con `nome.encode('latin-1').decode('utf-8')` prima del
  join. Verificato dopo il fix: tutti e 1180 i comuni si abbinano.
- **Comuni gia' coperti**: parsati dalla tabella
  [Comuni già coperti](comuni-coperti.md) (455 codici ISTAT), non da una
  query DB.

**Risultato**: **57 comuni** scaricati con successo, zero falliti per
motivi diversi dalla quota, bloccato dalla quota dopo 57 (backoff
crescente su "Capriglio", confermato sul successivo "Pollone" prima di
fermarsi). Distribuzione: Alessandria 8, Asti 7, Biella 7, Cuneo 7,
Novara 7, Torino 7, Verbano-Cusio-Ossola 7, Vercelli 7 (selezione
round-robin per provincia, non raggruppata, cosi' il blocco a meta'
lascia comunque copertura distribuita). Verificato senza doppioni e
senza sovrapposizioni con i 455 gia' coperti: 552.900 righe = 57 ×
9.700 giorni esatti.

**File prodotti** (fuori Git, `data/raw/`, da consegnare al collega
fuori canale, stesse colonne di sempre):
- `data/raw/temperature_data_extra_helper_general_20260722b.csv` —
  552.900 righe, 57 comuni, 2000-01-01 → 2026-07-22.
- `data/raw/riepilogo_generale_20260722b.csv` — tabella di sintesi.

Suffisso "b" per non confondersi con
`temperature_data_extra_helper_general_20260722.csv`, gia' presente da
una sessione precedente (85 comuni, nome scelto quel giorno per un
delta mai eseguito con quel nome — coincidenza di date, non un errore di
questa sessione).

**Non ancora importato** — stessa decisione del 2026-07-20 (accumulo
senza import/ricalcolo a ogni sessione): resta in coda con gli altri
lotti pendenti. **Script DB-free non salvato nel repository**: e' una
soluzione ad-hoc per questa sessione specifica (nessun accesso DB), non
un'alternativa generale a `download_extra_municipalities.py` — se
un'altra sessione futura si trova nella stessa condizione, questa
sezione ne descrive il metodo per poterlo ricostruire.

## Estensione generale, metodo DB-free — 93 comuni, record (2026-07-24)

Quinta giornata consecutiva della stessa richiesta. Stesso metodo
DB-free delle due sessioni precedenti — shapefile ISTAT +
`municipality_metadata_all.parquet` + tabella "Comuni già coperti" di
[Comuni già coperti](comuni-coperti.md), stessa base dei **599 comuni**
già coperti dopo il giro di import + ricalcolo eseguito dal titolare il
2026-07-23 pomeriggio (234 → 599 comuni in `temperature`, vedi sezione
dedicata sotto).

**Risultato**: **93 comuni**, il lotto più numeroso di tutta la serie
DB-free (quasi il doppio del solito 57) — un blocco transitorio su
"Altavilla Monferrato" recuperato dopo un solo fallimento (il comune
successivo è andato a buon fine), poi blocco persistente confermato su
"Caramagna Piemonte" e "Villar Perosa". Zero falliti per motivi diversi
dalla quota. Distribuzione: Asti 14, Alessandria 13, Cuneo 13, Torino 13,
Novara 11, Vercelli 11, Biella 9, Verbano-Cusio-Ossola 9. Verificato
senza doppioni né sovrapposizioni con i 599 già coperti: 902.286 righe =
93 × 9.702 giorni esatti.

**File prodotti** (fuori Git, `data/raw/`):
- `data/raw/temperature_data_extra_helper_general_20260724.csv` —
  902.286 righe, 93 comuni, 2000-01-01 → 2026-07-24.
- `data/raw/riepilogo_generale_20260724.csv` — tabella di sintesi.

**Non ancora importato**: resta in coda per il prossimo giro di import.

## Estensione generale, metodo DB-free — altri 57 comuni (2026-07-23)

Quarta giornata consecutiva della stessa richiesta ("come gli altri
giorni"). Stesso metodo DB-free descritto nella sezione precedente
(2026-07-22): shapefile ISTAT + `municipality_metadata_all.parquet` per
l'elenco comuni/coordinate, tabella "Comuni già coperti" di
[Comuni già coperti](comuni-coperti.md) per il filtro di esclusione. Lo
script stesso non è salvato nel repository (vive in una cartella
temporanea di sessione) e va ricreato da zero a ogni sessione — non un
problema, dato che è comunque descritto per intero qui.

**Risultato**: **57 comuni**, zero falliti per motivi diversi dalla
quota, bloccato dopo 57 (backoff crescente su "Grana Monferrato",
confermato su "Sostegno"). Distribuzione: Alessandria 8, Asti 7, Biella
7, Cuneo 7, Novara 7, Torino 7, Verbano-Cusio-Ossola 7, Vercelli 7 —
identica a quella del 2026-07-22 (stessa proporzione tra province, dato
che il numero di comuni già coperti per provincia non cambia
sostanzialmente la ripartizione). Verificato senza doppioni ne'
sovrapposizioni con i 512 gia' coperti: 552.957 righe = 57 × 9.701
giorni esatti (un giorno in piu' di ieri, la serie storica si allunga
ogni giorno che passa).

**File prodotti** (fuori Git, `data/raw/`):
- `data/raw/temperature_data_extra_helper_general_20260723.csv` —
  552.957 righe, 57 comuni, 2000-01-01 → 2026-07-23.
- `data/raw/riepilogo_generale_20260723.csv` — tabella di sintesi.

**Osservazione**: all'inizio di questa sessione `data/raw/` non
conteneva più nessuno dei file della sessione del 2026-07-22 — segno
che erano già stati presi in consegna e importati/archiviati dal
collega, coerente con la convenzione "file eliminati dopo l'unione"
usata in tutte le sessioni precedenti di questo tipo.

## Import dei 57 comuni ARPA-target e ricalcolo completo (2026-07-19)

Import del lotto descritto nella sezione precedente, eseguito dal titolare
nella stessa giornata dopo la consegna dei due file (`temperature_data_extra_helper_arpa_target.csv`,
`riepilogo_57_comuni_arpa_target.csv`).

**Pulizia e join**: caricamento con `dtype={'istat_code': str}` (stesso
accorgimento delle sessioni precedenti, altrimenti si perdono gli zeri
iniziali), passaggio manuale attraverso i metodi di `DataCleaner` (0 righe
scartate, 881 outlier IQR flaggati, nessuno fuori range fisico), join
`istat_code` → `municipality_id` (57/57 risolti, nessuna sovrapposizione
con i 177 comuni già presenti né con i 18 di Torino ancora in sospeso).
Caricato con `insert_temperature_for_municipalities()`: **552.729 righe
inserite, 177 → 234 comuni**.

**Ricalcolo a valle completo**: elevazione ri-scaricata (234/234
popolati), `TRUNCATE heatwave_events` + `identify_heatwaves()` (**640 →
770 ondate**), refresh viste KPI (`kpi_annual_by_municipality` 6.318
righe, 234×27 anni). **Nota tecnica**: il refresh è stato eseguito
**senza `CONCURRENTLY`** — `REFRESH MATERIALIZED VIEW CONCURRENTLY` ha
fallito con `ObjectNotInPrerequisiteState` perché la vista non ha nessun
indice **univoco** (solo i due btree non-unique su `(municipality_id,
year)` e `(province_id, year)` da `01_init_database.sql`), requisito
tecnico di Postgres per il refresh concorrente. Sessioni precedenti
citano refresh "concorrenti" riusciti — non verificato se lo fossero
davvero o se la wiki generalizzasse; con lo schema attuale non è
possibile. Segnalato come miglioria futura, non applicato in questa
sessione (fuori scope).

**Crescita della copertura ARPA di conseguenza** (richiesta esplicita
dell'utente dopo un primo fraintendimento — inizialmente avviata come
iniziativa del titolare/IA senza chiederlo, poi fermata su richiesta
dell'utente e ripresa solo dopo conferma): rilanciato `download_arpa.py`
(default, non `--only-uncovered` — join su `temperature`, che ora include
i 57 nuovi). 108/234 comuni Open-Meteo hanno una stazione ARPA attiva
(51 preesistenti + tutti i 57 nuovi, **100% di corrispondenza** — conferma
che la lista target in `comuni-coperti.md` era corretta). Download
interrotto una volta (limite ambientale del task in background, non un
errore Python — nessun traceback, nessun salto temporale sospetto) dopo
13 comuni, ripreso automaticamente sfruttando la logica di resume basata
sul CSV di output già esistente (`arpa_temperature_after_57import.csv`),
completato sui restanti 95 (1 fallimento singolo transitorio,
`ConnectionResetError`). **830.408 righe nuove**, importate con
`insert_arpa_temperature()` (`ON CONFLICT (station_code, date) DO
NOTHING`, quindi sicuro anche in caso di sovrapposizione) — **946.938
righe processate**, `arpa_temperature` a 1.979.158 righe totali (218
comuni, invariato: i 57 nuovi erano già stazioni note, solo senza
controparte Open-Meteo prima d'ora).

**Rieseguita l'intera pipeline di analisi** (`refresh_dashboard.py`: trend,
ondate, STL stagionale, spaziale, regressione, validazione ARPA, export
dashboard). **Primo tentativo interrotto** dopo ~106 minuti (208/234
comuni STL completati) da un'interruzione esterna del processo in
background, stesso tipo di anomalia del download ARPA sopra — nessun
errore applicativo, il rilancio successivo è ripartito da zero (ogni
modulo sovrascrive i propri output, quindi sicuro) e questa volta ha
completato tutti e 7 gli step, STL compresa (**127 minuti**, il passo
di gran lunga più lento: ~36s/comune × 234). Risultati finali della
validazione ARPA sul campione a 108 comuni: vedi [Analisi
statistica](statistical-analysis.md#validazione-contro-arpa-piemonte-2026-07-18-estesa-il-2026-07-19)
per il dettaglio completo (bias -1.59°C, correlazione col recall delle
ondate crollata a 16.4% dal 31.4% dei 51 comuni originali — non ancora
spiegato, segnalato come domanda aperta).

**Consolidamento file** (stesso pattern delle due sessioni precedenti,
richiesto esplicitamente dall'utente): in `data/raw/`,
`temperature_data_extra_helper_arpa_target.csv` unito in
`temperature_data_extra.csv` (istat_code → municipality_id, zero
sovrapposizioni verificate) ed eliminato insieme al riepilogo — **non**
toccato invece `temperature_data_extra_torino_2026-07-19.csv` (i 18
comuni di Torino restano non importati, quindi tenuti separati per non
rompere la corrispondenza file↔DB). In `data/processed/`, il file pulito
di oggi (`temperature_extra_arpa_target_57_clean.csv`) unito in
`temperature_clean_extra.csv` dopo verifica di zero sovrapposizioni.
Verificato **77.560 + 2.191.263 = 2.268.823**, combacia esattamente col
totale reale in `temperature`.

**Mappe QGIS rigenerate** (dimenticate nel primo giro di ricalcolo,
lanciate solo dopo che l'utente ha chiesto esplicitamente "le cartine"):
`python-qgis-ltr.bat qgis_projects/build_maps.py`, tutti e 3 i progetti
(`temperature_heatmap`, `hotspot_analysis`, `evolution_animation`) e le
preview PNG rigenerati con i 234 comuni. Verificato visivamente: la
preview mostra molte più aree colorate rispetto alle versioni precedenti
(177/98 comuni). Le righe tratteggiate sulle preview sono l'artefatto già
noto di rendering etichette senza font nell'ambiente headless (vedi [Mappe
GIS](gis-maps.md)), non un problema introdotto da questa sessione.

## Passaggi pianificati ma non ancora scritti

- Calcolo KPI giornalieri/annuali lato Python (oggi solo le viste
  materializzate SQL calcolano aggregati, vedi [Modello Dati](data-model.md))
- Trigger di `identify_heatwaves()` dopo il caricamento (mai eseguita su
  dati reali — ora possibile, `temperature` è popolata)
- Refresh delle viste materializzate post-load
- Un orchestratore unico che concatena i 3 script (oggi lanciati a mano in
  sequenza: `download_data.py` → `clean_data.py` → `load_to_db.py`)

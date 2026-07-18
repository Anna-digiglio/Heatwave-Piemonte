# Stato del progetto (pianificato vs implementato)

**Sorgenti**: confronto diretto tra `docs/ROADMAP.md`/`PROJECT_SUMMARY.md`
(pianificazione) e stato reale delle cartelle/codice.

Questa pagina è quella con la scadenza più breve nella wiki: va aggiornata a
ogni sessione di lavoro rilevante (vedi workflow di ingest in `CLAUDE.md`).

## Settimana 1 — Setup & Data Acquisition

| Attività | Roadmap | Realtà |
|---|---|---|
| Struttura repo | ✅ | ✅ |
| Schema DB (`01_init_database.sql`) | ✅ | ✅ completo: 6 tabelle, 2 viste, 1 funzione, 25+ indici. **Eseguito per la prima volta su un DB reale il 2026-07-04** (Postgres 16 + PostGIS locale) — trovati e risolti 4 bug mai emersi finché nessuno l'aveva davvero eseguito (vedi [ETL](etl-pipeline.md) e [Modello Dati](data-model.md)) |
| Script download (`download_data.py`) | pianificato | ✅ scritto, bug di import **risolto il 2026-07-04** (vedi [Fonti Dati](data-sources.md)); aggiunto anche retry/backoff per rate limit Open-Meteo |
| Download dati 2000-2026 | ⬜ | ✅ **eseguito il 2026-07-04, esteso il 2026-07-15, due volte il 2026-07-17 e due volte il 2026-07-18** — 1.716.094+ righe reali, **177 comuni** (8 capoluoghi + 169 extra), dal 2000 **fino a oggi** (non più fermo al 31/12/2025) |
| Dati geografici (ISTAT comuni/province) | ⬜ | ✅ **caricati il 2026-07-04** — 1180 comuni reali in `municipalities` (DB Postgres/PostGIS locale), 8 province con codici ISTAT corretti |
| Python environment / requirements | ⬜ | `.venv` presente, `requirements.txt` presente e dettagliato |

## Settimana 2 — ETL & Analisi

| Attività | Roadmap | Realtà |
|---|---|---|
| `DataCleaner` completo | pianificato | ✅ scritto, **ma non era mai stato eseguibile** fino al 2026-07-04 (`SyntaxError` da newline letterali corrotte + bug che scartava il 99,9% dei dati — vedi [ETL](etl-pipeline.md)). Eseguito su 75.976 righe (8 comuni) e poi su altre 341.892 (36 comuni extra, 2026-07-15), senza modifiche al codice |
| Caricamento `temperature` nel DB | pianificato | ✅ **eseguito il 2026-07-04, esteso il 2026-07-15** — **417.868 righe reali, 44 comuni**, in `temperature`, batch insert (vedi [ETL](etl-pipeline.md)) |
| `identify_heatwaves()` eseguita | pianificato | ✅ eseguita il 2026-07-12 su 8 comuni (51 ondate), **rieseguita il 2026-07-15** su 44 comuni (145 ondate), **due volte il 2026-07-17** su 63 poi 98 comuni e **due volte il 2026-07-18** su 155 poi 177 comuni, sempre dopo `TRUNCATE` (non idempotente) — **640 ondate totali**, incluse quelle del 2026 (vedi [Modello Dati](data-model.md)) |
| KPI calcolati | pianificato | ✅ viste materializzate rinfrescate il 2026-07-12 (208 righe, 8 comuni), il 2026-07-15 (1144 righe, 44 comuni), due volte il 2026-07-17 e **due volte il 2026-07-18** — `kpi_annual_by_municipality` ora **4.779 righe** (177 comuni × 27 anni, 2000-2026) |
| Query SQL (10+) | pianificato | 3 query scritte in `02_common_queries.sql` |

## Settimana 3 — Visualizzazione & Deployment

| Attività | Roadmap | Realtà |
|---|---|---|
| `src/analysis/` (statistica, spaziale, temporale) | pianificato | ✅ **implementata ed eseguita su dati reali il 2026-07-15** — trend (Mann-Kendall/regressione), statistiche ondate di calore, STL decomposition, Moran's I + clustering K-means (vedi [Analisi Statistica](statistical-analysis.md)) |
| `src/visualization/` | pianificato | ❌ cartella vuota |
| Progetti QGIS | pianificato | ✅ **generati ed eseguiti il 2026-07-15** — 3 progetti `.qgz` (heatmap, hotspot, animazione temporale) via PyQGIS headless, verificati con render PNG (vedi [Mappe GIS](gis-maps.md)); manca solo la mappa "Heatwave Index" |
| Dashboard Streamlit | pianificato | ✅ **implementata il 2026-07-15, contenuto ampliato sostanzialmente lo stesso giorno** — 5 pagine (home con card di navigazione, analisi temporale, analisi spaziale, ondate di calore, download), filtri, palette colori coerente, dati reali, verificata via `AppTest` e avviata live su `localhost:8501` (vedi [Dashboard](dashboard.md)) |
| Test unitari | pianificato (70%+ coverage) | ✅ **implementati il 2026-07-15** — 31 test pytest (`DataCleaner`, `src/analysis/` funzioni pure, `Config`), 86% di copertura su `clean_data.py`; **1 bug reale trovato e corretto** in `detect_outliers()` (vedi [Test Unitari](testing.md)) |
| Documentazione | in gran parte fatta | ✅ README, PROJECT_SUMMARY, docs/* molto estesi (a volte più avanti del codice) |

## Cronologia degli aggiornamenti principali

**Il nucleo pianificato del progetto è completo**: pipeline Extract →
Transform → Load, analisi statistica/spaziale, mappe GIS e dashboard sono
tutte implementate ed eseguite su dati reali. Quello che segue è la
cronologia di come ci si è arrivati.

### 2026-07-04 — pipeline dati end-to-end (il buco più grande, colmato)

Download Open-Meteo reale, database Postgres/PostGIS locale configurato e
raggiungibile (via `.env`), schema inizializzato, 8 province + 1180
comuni reali + 75.976 righe di temperatura (8 comuni capoluogo,
2000-2025) caricati. Questo era il buco più grande del progetto — da qui
in poi il resto ha avuto dati reali su cui lavorare.

> Nota di granularità: `temperature` copriva inizialmente solo gli **8
> comuni capoluogo di provincia** (unica granularità realmente misurata da
> Open-Meteo), non tutti i 1180 comuni — scelta deliberata, vedi
> [ETL](etl-pipeline.md).

### 2026-07-12 — prima esecuzione di `identify_heatwaves()`

51 ondate identificate (2000-2025) e viste materializzate KPI rinfrescate
(208 righe ciascuna). **Tutta la catena dati → schema → KPI/ondate è ora
reale e verificata**: `temperature`, `heatwave_events`,
`kpi_annual_by_municipality`, `kpi_annual_by_province` hanno tutte
contenuto vero su cui costruire analisi/mappe/dashboard.

### 2026-07-15 — analisi, dashboard, mappe GIS, test, rifiniture

Giornata con il maggior numero di traguardi:

- **`src/analysis/`** scritta ed eseguita su dati reali — trend di
  riscaldamento (7/8 comuni con trend significativo, +0.4/+1.0
  °C/decade), statistiche ondate di calore (intensità/durata popolate su
  tutte le 51 ondate), STL decomposition (ampiezza stagionale ~28-32°C),
  Moran's I + clustering climatico (limitati dal campione di sole 8
  unità spaziali — vedi [Analisi Statistica](statistical-analysis.md) per
  dettaglio e caveat). Risultati salvati come CSV in `output/`.
- **Dashboard Streamlit**: scritta ed eseguita (5 pagine, dati reali) —
  vedi [Dashboard](dashboard.md) per i 3 bug trovati eseguendola per la
  prima volta (import `components` non risolto, WKT passato a
  `folium.GeoJson` senza conversione, API deprecata). Verificata senza
  browser con `streamlit.testing.v1.AppTest`, poi avviata live.
- **Mappe GIS**: generati i 3 progetti QGIS pianificati via script PyQGIS
  headless (`qgis_projects/build_maps.py`), verificati con render PNG
  offscreen invece che aprendo QGIS Desktop — vedi [Mappe GIS](gis-maps.md)
  per i 2 bug reali trovati (nomi di campo dopo un join, subquery SQL non
  eseguibile come `table=` in QGIS) e per l'unico aspetto non verificabile
  in automatico (rendering del testo delle etichette, bloccato da un font
  mancante nell'ambiente headless). **Con questo, tutti e 3 i pezzi
  principali di Settimana 3 (analisi, dashboard, mappe) sono implementati
  ed eseguiti su dati reali.**
- **Rifiniture**: `logging.format` in `config.yaml` corretto alla sintassi
  loguru (era sintassi stdlib `%(...)s`, sovrascriveva erroneamente il
  default corretto di `src/utils/logger.py`) — console e file di log ora
  leggibili. `requirements.txt` allineato alle versioni effettivamente
  installate nel `.venv` (drift esistente da inizio progetto — es. pandas
  2.1.4→3.0.3, numpy 1.26→2.4, streamlit 1.29→1.58); verificato `pip
  check`, nessun conflitto.
- **Estensione a 44 comuni**: su richiesta dell'utente ("rendere Moran's
  I/clustering più robusti"), copertura reale estesa da 8 a 44 comuni (36
  extra selezionati con campionamento "farthest-point" per massimizzare
  la copertura spaziale per provincia — vedi [ETL](etl-pipeline.md)).
  Rieseguita l'intera catena a valle: `identify_heatwaves()` (145
  ondate), viste KPI, tutti e 4 i moduli di `src/analysis/`, i 3 progetti
  QGIS, tutte le pagine dashboard. Risultato più significativo: **Moran's
  I passa da non significativo (p=0.732, n=8) a statisticamente
  significativo (I=0.101, p=0.002, n=44)** — vedi
  [Analisi Statistica](statistical-analysis.md). Nel farlo, scoperto e
  risolto un bug di encoding vecchio di 11 giorni (28 comuni su 1180 con
  nomi corrotti nel DB, mai notato prima — vedi [Fonti Dati](data-sources.md)).
- **Ampliamento contenuto dashboard**: su richiesta esplicita dell'utente,
  contenuto delle 3 pagine di analisi ampliato sostanzialmente (dettaglio
  completo in [Dashboard](dashboard.md)): anomalie termiche, confronto
  stagionale, boxplot per quinquennio e confronto con letteratura in
  Analisi Temporale; mappe coropletiche per provincia (via `ST_Union`
  PostGIS), mappa del trend per comune, fasce altitudinali e isola di
  calore urbana in Analisi Spaziale; conteggio cumulato, mappa di
  concentrazione e heatmap "calendario" in Ondate di Calore. Per la
  fascia altitudinale è stato necessario popolare
  `municipalities.elevation_m` (prima sempre `NULL`) — scaricato per
  davvero da Open-Meteo Elevation API per i 44 comuni con dati (scelta
  confermata con l'utente, invece di un placeholder "non disponibile") —
  vedi [Fonti Dati](data-sources.md) e [Modello Dati](data-model.md).
- **Test unitari**: 31 test pytest scritti, vedi [Test Unitari](testing.md).

### 2026-07-16 — popolazione e uso del suolo (covariate per il paper)

Popolazione residente (`demo.istat.it`) e CORINE Land Cover 2018
popolate per tutti i 1180 comuni — vedi [Fonti Dati](data-sources.md) per
il dettaglio completo di entrambe le fonti.

### 2026-07-17 — estensione a 63 comuni, NDVI, modello statistico, 35 comuni extra

Giornata più densa del progetto, quattro traguardi distinti:

**1. Estensione a 63 comuni + dati fino ad oggi**. Su richiesta esplicita
dell'utente ("coprimi i 1180 comuni piemontesi, e aggiorna la data fino ad
oggi"). Obiettivo iniziale enorme (1180 comuni) ridimensionato insieme
all'utente dopo aver spiegato costi/rischi reali (vedi
[Fonti Dati](data-sources.md) per il dettaglio): tentativi falliti a 300 e
poi 56 comuni extra per lo stesso motivo — **Open-Meteo ha un limite
giornaliero di richieste** (non solo "al minuto" come già noto), scoperto
nel modo peggiore (~5h40 di download quasi tutto sprecato il primo
giorno, perso perché lo script salvava solo a fine esecuzione). Corretto
alla radice: salvataggio incrementale (ogni comune scaricato viene subito
scritto su disco) in `download_extra_municipalities.py` e nel nuovo
`update_recent_data.py`, così nessuna interruzione futura fa più perdere
progresso. Risultato netto in due giorni: **44 → 63 comuni** (19
aggiuntivi, stesso campionamento "farthest-point") e **tutti i 63 comuni
ora arrivano fino a oggi** — non i 1180 completi, ma un incremento reale
ottenuto in modo sostenibile invece di un tentativo fallito in blocco.
Vedi [Fonti Dati](data-sources.md) per la scoperta del rate limit,
[ETL](etl-pipeline.md) per il flusso incrementale, e
[Analisi Statistica](statistical-analysis.md) per i risultati ricalcolati
(Moran's I ora 0.132, p=0.001, ancora più significativo che con 44
comuni).

> **2 bug reali trovati e corretti** per via del nuovo dato che arriva
> fino al 2026 (non più fermo al 2025): (1) `frequency_by_year()` in
> `heatwave_stats.py` aveva un `reindex` fisso `range(2000, 2026)` che
> scartava in silenzio le ondate del 2026 (16 ondate nascoste, trovate
> verificando l'output dopo l'estensione) — reso dinamico sul range anni
> realmente presente nei dati; (2) lo slider dell'intervallo anni nella
> dashboard (`components/filters.py`) aveva `YEAR_MIN, YEAR_MAX = 2000,
> 2025` fissi nel codice, che avrebbe reso impossibile selezionare il
> 2026 una volta arrivati i dati più recenti — resi dinamici dalla data
> reale più vecchia/più recente in `temperature`.

**2. NDVI — terza covariata esplicativa** per il paper (dopo popolazione e
CORINE, fatte il giorno prima) — vedi
[Articolo scientifico](paper-scientifico.md). Decisione presa con
l'utente: Copernicus Global Land Service NDVI 300m V3 (prodotto già
calcolato, download manuale) invece di Sentinel-2 vero (10m, via GEE o
CDSE Statistical API). Un'apparente scorciatoia verso un prodotto NDVI
10m reale trovata durante la navigazione del portale (HR-VPP) si è
rivelata un vicolo cieco — tornati al piano originale. Il download reale
via Copernicus Browser ha richiesto diversi tentativi e ha prodotto un
file **globale** da 3.3 GB (nessun ritaglio lato server per questo
prodotto, a differenza di CLC) — gestito senza saturare la RAM leggendo
solo la finestra Piemonte via `rasterio.windows`. Scala/offset/flag della
formula DN→NDVI **verificati sui metadati embedded del file reale**, non
solo dalla documentazione (rivelatasi imprecisa sui codici di flag).
**Risultato**: `municipality_ndvi` popolata per **1180/1180 comuni**.
Media regionale NDVI 0.663, range 0.327-0.867, valori verificati a
campione coerenti coi risultati CORINE. Vedi [Fonti dati](data-sources.md)
e [Modello dati](data-model.md).

**3. Prima iterazione del modello statistico**: non appena
popolazione/CORINE/NDVI sono state tutte disponibili, prima esecuzione di
`src/analysis/spatial_regression.py` — OLS classico (temp ~
elevazione+popolazione+%urbano+NDVI, VIF tutti <5, R²=0.979 dominato
dall'elevazione) seguito dal check concordato con l'utente (Moran's I sui
residui): ancora significativo (I=0.081, p=0.001), quindi costruito anche
un vero modello a errore spaziale via `spreg`/`libpysal`. La regola di
Anselin ha dato un esito non ambiguo (errore spaziale, non lag):
lambda=0.738 (p<0.001). **Risultato più rilevante**: **% urbano diventa
statisticamente significativo col segno atteso solo nel modello
spaziale** (l'OLS classico lo mascherava) — prima conferma quantitativa,
seppur provvisoria (n=63), dell'ipotesi originale del paper su
città/urbanizzazione come fattore esplicativo. NDVI resta significativo
ma con segno controintuitivo (più verde → temperatura più alta), da
approfondire. Decisione concordata con l'utente: **non** aggiungere
subito altre covariate candidate — si rilancia questa stessa pipeline via
via che il campione di comuni con temperatura cresce. Vedi
[Analisi statistica](statistical-analysis.md) per il dettaglio tecnico
completo e [Articolo scientifico](paper-scientifico.md) per l'impatto sul
piano del paper.

**4. 35 comuni extra, scaricati da una seconda macchina, poi importati lo
stesso giorno**: una collaboratrice, senza accesso al database del
titolare, ha ricostruito quali comuni fossero già coperti leggendo le
preview PNG dei progetti QGIS (tracciate in Git a differenza dei dati),
poi scaricato 35 comuni aggiuntivi da Open-Meteo fino al blocco del rate
limit giornaliero — vedi
[Fonti Dati](data-sources.md#download-collaborativo-da-una-seconda-macchina--35-comuni-extra-2026-07-17)
per il metodo (verificabile) e un bug reale trovato e corretto durante
l'esecuzione (confronto `int`/`str` su `istat_code` che causava download
duplicati). Import eseguito lo stesso pomeriggio: pulizia (`DataCleaner`,
0 righe scartate, 666 outlier IQR) + risoluzione `istat_code` →
`municipality_id` via join contro `municipalities` (tutti e 35 trovati) —
passi documentati in
[Pipeline ETL](etl-pipeline.md#import-dei-35-comuni-extra-dalla-seconda-macchina-2026-07-17).
**Risultato: 63 → 98 comuni, 950.110 righe in `temperature`.**

**5. Ricalcolo completo a valle dei 98 comuni**: elevazione ri-scaricata
per tutti i comuni con temperatura (98/98), `TRUNCATE` + `identify_heatwaves()`
(331 ondate, da 190), refresh viste KPI (`kpi_annual_by_municipality`
2.646 righe, `kpi_annual_by_province` 216), tutti e 5 i moduli di
`src/analysis/` rieseguiti (inclusa `spatial_regression.py`) e mappe QGIS
rigenerate — vedi [Analisi Statistica](statistical-analysis.md) per i
risultati completi. **Cambio degno di nota**: a n=98 **% urbano non è più
statisticamente significativo** nel modello a errore spaziale (lo era a
n=63, p=0.011) — registrato onestamente in
[Articolo scientifico](paper-scientifico.md) invece di tenere solo il
risultato precedente. Testo della dashboard corretto di conseguenza (vedi
[Dashboard](dashboard.md)).

### 2026-07-18 — 98 → 177 comuni: seconda collaborazione + download diretto

Stessa collaboratrice della sessione precedente, stessa macchina esterna.
Dopo `git pull` (che ha portato il repo alla versione a 98 comuni e
importato la nuova pagina [Comuni già coperti](comuni-coperti.md), scritta
dal titolare proprio per evitare di dover ripetere la ricostruzione dai
PNG QGIS della volta precedente), campionamento "farthest-point" rieseguito
sui 1082 comuni ancora scoperti usando questa lista come fonte diretta e
affidabile. Download bloccato dal rate limit giornaliero dopo **57 comuni**
riusciti (su "Cannobio", stesso pattern di backoff crescente già visto) —
questa volta **senza il bug di doppioni** della sessione precedente,
verificato riga per riga.

**File stantio scartato prima dell'import**: insieme al file nuovo
(`batch2`) era presente anche una copia di `temperature_data_extra_helper_35comuni.csv`
— stesso identico contenuto del file già importato il giorno prima
(339.325 righe, stessi 35 codici ISTAT). Verificato contro il DB prima di
toccarlo (tutti e 35 già presenti) e scartato senza importarlo: un
secondo import avrebbe duplicato 339mila righe senza che nessun vincolo
DB lo impedisse. La cautela di controllare sempre il contenuto di un file
consegnato contro lo stato reale del DB, invece di fidarsi del nome del
file o della richiesta dell'utente, ha evitato un danno reale.

**Import di `batch2`** (57 comuni): pulizia + risoluzione `istat_code` →
`municipality_id`, stessi passi già collaudati. **98 → 155 comuni.**

**Download diretto di altri 22 comuni**, eseguito subito dopo (non da una
macchina esterna): `download_extra_municipalities.py --count 40`,
bloccato dal rate limit (già in parte consumato dalla collaboratrice
nella stessa giornata) dopo 22 comuni — questa volta con un sintomo
diverso, nessun errore esplicito ma il processo bloccato "silenziosamente"
per oltre 12 minuti senza scrivere nulla di nuovo, interrotto
manualmente dopo aver verificato che i 22 comuni già ottenuti fossero
completi. **155 → 177 comuni, 1.716.094 righe in `temperature`.**

**Bug reale trovato durante il ricalcolo**: `fetch_elevation.py`
interrogava l'Elevation API con tutte le coordinate in un'unica
richiesta — oltre 100 comuni l'API risponde `400`. Fix: richieste a
lotti da 100.

**Ricalcolo completo a valle dei 177 comuni**: elevazione (177/177,
col fix sopra), `TRUNCATE` + `identify_heatwaves()` (**640 ondate**, da
331), refresh viste KPI (`kpi_annual_by_municipality` 4.779 righe), tutti
e 5 i moduli di `src/analysis/`, mappe QGIS rigenerate. **Ulteriore
cambio nei risultati statistici**: a n=177 nel modello a errore spaziale
**anche NDVI smette di essere significativo** (oltre a % urbano, già non
significativo da n=98) — solo l'elevazione resta un predittore robusto
in tutte e tre le versioni (n=63/98/177). Vedi
[Analisi Statistica](statistical-analysis.md) per il dettaglio, testo
della dashboard corretto di conseguenza.

**Consolidamento file** (stesso pattern del giorno prima): `data/raw/`
e `data/processed/` riportati a 4 e 2 file rispettivamente, dopo aver
unito i file del giorno e verificato zero duplicati/sovrapposizioni.
[Comuni già coperti](comuni-coperti.md) aggiornata con l'elenco completo
dei 177 comuni.

Vedi [Fonti Dati](data-sources.md#seconda-sessione-collaborativa--download-diretto--98--177-comuni-2026-07-18)
e [Pipeline ETL](etl-pipeline.md#comuni-extra--57-dalla-collaboratrice--22-scaricati-direttamente-2026-07-18)
per il dettaglio completo.

## Prossimi passi

Tutti minori/non bloccanti — il nucleo pianificato del progetto è
completo:

1. ~~Aprire i 3 `.qgz` in QGIS Desktop per confermare visivamente le
   etichette~~ — **fatto e confermato dall'utente il 2026-07-15**, incluso
   un fix successivo per le etichette mancanti in `evolution_animation.qgz`
2. ~~Popolare `elevation_m`~~ — **fatto parzialmente il 2026-07-15**, ma
   solo per i comuni con dati di temperatura reali (Open-Meteo Elevation
   API, vedi [Modello Dati](data-model.md)); esteso a 98 comuni il
   2026-07-17 e a 177 il 2026-07-18; resta `NULL` per il resto dei 1180
   comuni
3. Riavviare `postgresql-x64-16` come vero servizio Windows (oggi gira via
   `pg_ctl` manuale — il servizio in sé risulta "Stopped" e non
   ripartirebbe da solo dopo un riavvio del PC)
4. Ricordarsi di rifare `REFRESH MATERIALIZED VIEW` dopo ogni futuro
   caricamento di `temperature` (vedi [Modello Dati](data-model.md)) —
   incluso dopo l'import dei 35 comuni extra descritti sopra
5. Mappa "Heatwave Index" (composito intensità/frequenza ondate) — unica
   mappa pianificata non ancora costruita (vedi [Mappe GIS](gis-maps.md))
6. ~~Test unitari (`tests/` vuota)~~ — **fatto il 2026-07-15**, 31 test
   pytest, vedi [Test Unitari](testing.md); resta da scrivere una
   documentazione API/tutorial
7. Retry più generico per errori di rete transitori (non solo `429`) in
   `download_data.py` — scoperto durante il download dei comuni extra
   (vedi [Analisi Statistica](statistical-analysis.md))
8. ~~Contenuto delle 3 pagine di analisi della dashboard troppo
   essenziale~~ — **ampliato sostanzialmente il 2026-07-15**, vedi
   [Dashboard](dashboard.md)
9. **Valutare il deploy pubblico gratuito della dashboard** (Streamlit
   Community Cloud) — discusso il 2026-07-15, rimandato. Blocco tecnico
   noto: la dashboard si connette a Postgres/PostGIS su `localhost`, non
   raggiungibile da un server remoto. Due strade possibili da valutare:
   (a) database Postgres/PostGIS gratuito in cloud (es. Supabase/Neon,
   verificare supporto PostGIS nel piano free) con credenziali spostate
   in `st.secrets`; (b) far leggere la dashboard solo dai CSV già in
   `output/`/`data/processed/` (nessuna connessione DB dal vivo, ma
   niente aggiornamento automatico se in futuro si ricaricano dati
   nuovi). Vedi [Dashboard](dashboard.md).
10. ~~Importare i 35 comuni extra scaricati dalla seconda macchina~~ —
    **fatto lo stesso giorno (2026-07-17)**: pulizia + risoluzione
    `municipality_id`, poi rilancio di `identify_heatwaves()`/viste
    KPI/`src/analysis/`/mappe QGIS a valle (vedi cronologia sopra).
11. ~~Importare i 57 comuni extra del 2026-07-18~~ — **fatto lo stesso
    giorno**, insieme a un download diretto di altri 22 comuni (98 → 155
    → 177) e al ricalcolo completo a valle (vedi cronologia sopra).

## Discrepanze da tenere a mente quando si presenta il progetto

`README.md` e `PROJECT_SUMMARY.md` descrivono metriche come "1.7M record",
"Status: Production Ready", "database size 3-5 GB" — sono **target
pianificati**, scritti prima di scrivere il codice, non misurazioni reali.
Utile saperlo per non presentarli come risultati raggiunti in un colloquio
o in una demo.

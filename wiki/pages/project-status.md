# Stato del progetto (pianificato vs implementato)

**Sorgenti**: confronto diretto tra `docs/ROADMAP.md`/`PROJECT_SUMMARY.md`
(pianificazione) e stato reale delle cartelle/codice, aggiornato al
2026-07-15.

Questa pagina è quella con la scadenza più breve nella wiki: va aggiornata a
ogni sessione di lavoro rilevante (vedi workflow di ingest in `CLAUDE.md`).

## Settimana 1 — Setup & Data Acquisition

| Attività | Roadmap | Realtà |
|---|---|---|
| Struttura repo | ✅ | ✅ |
| Schema DB (`01_init_database.sql`) | ✅ | ✅ completo: 6 tabelle, 2 viste, 1 funzione, 25+ indici. **Eseguito per la prima volta su un DB reale il 2026-07-04** (Postgres 16 + PostGIS locale) — trovati e risolti 4 bug mai emersi finché nessuno l'aveva davvero eseguito (vedi [ETL](etl-pipeline.md) e [Modello Dati](data-model.md)) |
| Script download (`download_data.py`) | pianificato | ✅ scritto, bug di import **risolto il 2026-07-04** (vedi [Fonti Dati](data-sources.md)); aggiunto anche retry/backoff per rate limit Open-Meteo |
| Download dati 2000-2026 | ⬜ | ✅ **eseguito il 2026-07-04, esteso il 2026-07-15 e il 2026-07-17** — 610.785+ righe reali, **63 comuni** (8 capoluoghi + 55 extra), dal 2000 **fino a oggi** (non più fermo al 31/12/2025) |
| Dati geografici (ISTAT comuni/province) | ⬜ | ✅ **caricati il 2026-07-04** — 1180 comuni reali in `municipalities` (DB Postgres/PostGIS locale), 8 province con codici ISTAT corretti |
| Python environment / requirements | ⬜ | `.venv` presente, `requirements.txt` presente e dettagliato |

## Settimana 2 — ETL & Analisi

| Attività | Roadmap | Realtà |
|---|---|---|
| `DataCleaner` completo | pianificato | ✅ scritto, **ma non era mai stato eseguibile** fino al 2026-07-04 (`SyntaxError` da newline letterali corrotte + bug che scartava il 99,9% dei dati — vedi [ETL](etl-pipeline.md)). Eseguito su 75.976 righe (8 comuni) e poi su altre 341.892 (36 comuni extra, 2026-07-15), senza modifiche al codice |
| Caricamento `temperature` nel DB | pianificato | ✅ **eseguito il 2026-07-04, esteso il 2026-07-15** — **417.868 righe reali, 44 comuni**, in `temperature`, batch insert (vedi [ETL](etl-pipeline.md)) |
| `identify_heatwaves()` eseguita | pianificato | ✅ eseguita il 2026-07-12 su 8 comuni (51 ondate), **rieseguita il 2026-07-15** su 44 comuni (145 ondate) e **il 2026-07-17** su 63 comuni dopo `TRUNCATE` (non idempotente) — **190 ondate totali**, incluse 16 nel 2026 (vedi [Modello Dati](data-model.md)) |
| KPI calcolati | pianificato | ✅ viste materializzate rinfrescate il 2026-07-12 (208 righe, 8 comuni), il 2026-07-15 (1144 righe, 44 comuni) e **il 2026-07-17** — `kpi_annual_by_municipality` ora 1701 righe (63 comuni × 27 anni, 2000-2026) |
| Query SQL (10+) | pianificato | 3 query scritte in `02_common_queries.sql` |

## Settimana 3 — Visualizzazione & Deployment

| Attività | Roadmap | Realtà |
|---|---|---|
| `src/analysis/` (statistica, spaziale, temporale) | pianificato | ✅ **implementata ed eseguita su dati reali il 2026-07-15** — trend (Mann-Kendall/regressione), statistiche ondate di calore, STL decomposition, Moran's I + clustering K-means (vedi [Analisi Statistica](statistical-analysis.md)) |
| `src/visualization/` | pianificato | ❌ cartella vuota |
| Progetti QGIS | pianificato | ✅ **generati ed eseguiti il 2026-07-15** — 3 progetti `.qgz` (heatmap, hotspot, animazione temporale) via PyQGIS headless, verificati con render PNG (vedi [Mappe GIS](gis-maps.md)); manca solo la mappa "Heatwave Index" |
| Dashboard Streamlit | pianificato | ✅ **implementata il 2026-07-15, contenuto ampliato sostanzialmente lo stesso giorno** — 5 pagine (home con card di navigazione, analisi temporale, analisi spaziale, ondate di calore, download), sidebar filtri globali (anni/provincia), palette colori coerente, dati reali, verificata via `AppTest` e avviata live su `localhost:8501` (vedi [Dashboard](dashboard.md)) |
| Test unitari | pianificato (70%+ coverage) | ✅ **implementati il 2026-07-15** — 31 test pytest (`DataCleaner`, `src/analysis/` funzioni pure, `Config`), 86% di copertura su `clean_data.py`; **1 bug reale trovato e corretto** in `detect_outliers()` (vedi [Test Unitari](testing.md)) |
| Documentazione | in gran parte fatta | ✅ README, PROJECT_SUMMARY, docs/* molto estesi (a volte più avanti del codice) |

## Prossimo passo a maggiore impatto

**La pipeline Extract → Transform → Load è ora completa ed eseguita
end-to-end su dati reali** (2026-07-04): download Open-Meteo reale,
database Postgres/PostGIS locale configurato e raggiungibile (via `.env`),
schema inizializzato, 8 province + 1180 comuni reali + 75.976 righe di
temperatura (8 comuni capoluogo, 2000-2025) caricati. Questo era il buco più
grande del progetto — ora l'intero resto ha dati reali su cui lavorare.

Nota di granularità: `temperature` copre solo gli **8 comuni capoluogo di
provincia** (unica granularità realmente misurata da Open-Meteo), non tutti
i 1180 comuni — scelta deliberata, vedi [ETL](etl-pipeline.md).

Aggiornamento 2026-07-12: `identify_heatwaves()` eseguita su dati reali (51
ondate, 2000-2025) e viste materializzate KPI rinfrescate (208 righe
ciascuna). **Tutta la catena dati → schema → KPI/ondate è ora reale e
verificata**: `temperature`, `heatwave_events`, `kpi_annual_by_municipality`,
`kpi_annual_by_province` hanno tutte contenuto vero su cui costruire
analisi/mappe/dashboard.

Aggiornamento 2026-07-15: `src/analysis/` scritta ed eseguita su dati
reali — trend di riscaldamento (7/8 comuni con trend significativo,
+0.4/+1.0 °C/decade), statistiche ondate di calore (intensità/durata
popolate su tutte le 51 ondate), STL decomposition (ampiezza stagionale
~28-32°C), Moran's I + clustering climatico (limitati dal campione di
sole 8 unità spaziali — vedi [Analisi Statistica](statistical-analysis.md)
per il dettaglio e i caveat). Risultati salvati come CSV in `output/`.

Aggiornamento 2026-07-15 (dashboard): scritta ed eseguita la dashboard
Streamlit (5 pagine, dati reali) — vedi [Dashboard](dashboard.md) per i 3
bug trovati eseguendola per la prima volta (import `components` non
risolto, WKT passato a `folium.GeoJson` senza conversione, API deprecata).
Verificata senza browser con `streamlit.testing.v1.AppTest`, poi avviata
live su `http://localhost:8501`.

Aggiornamento 2026-07-15 (mappe GIS): generati i 3 progetti QGIS pianificati
via script PyQGIS headless (`qgis_projects/build_maps.py`), verificati con
render PNG offscreen invece che aprendo QGIS Desktop — vedi
[Mappe GIS](gis-maps.md) per i 2 bug reali trovati (nomi di campo dopo un
join, subquery SQL non eseguibile come `table=` in QGIS) e per l'unico
aspetto non verificabile in automatico (rendering del testo delle
etichette, bloccato da un font mancante nell'ambiente headless, da
confermare aprendo i file in QGIS Desktop). **Con questo, tutti e 3 i
pezzi principali di Settimana 3 (analisi, dashboard, mappe) sono
implementati ed eseguiti su dati reali.**

Aggiornamento 2026-07-15 (rifiniture): due voci minori risolte su
richiesta dell'utente:
- **`logging.format`** in `config.yaml` corretto alla sintassi loguru
  (`{time:...} | {level} | {name}:{function}:{line} - {message}`, lo
  stesso formato già usato come default in `src/utils/logger.py` — il
  valore in `config.yaml` lo sovrascriveva erroneamente con sintassi
  stdlib `%(...)s`). Console e file di log ora leggibili; verificato con
  un test diretto (`logger.info(...)` → riga formattata correttamente sia
  a schermo che in `logs/heatwave_piemonte.log`).
- **`requirements.txt` allineato** alle versioni effettivamente installate
  nel `.venv` (drift esistente da inizio progetto — es. pandas 2.1.4→3.0.3,
  numpy 1.26→2.4, streamlit 1.29→1.58). Verificato `pip check`: nessun
  conflitto di dipendenze nell'ambiente attuale.

**Aggiornamento 2026-07-15 (estensione a 44 comuni)**: su richiesta
dell'utente ("rendere Moran's I/clustering più robusti"), estesa la
copertura reale da 8 a **44 comuni** (36 extra selezionati con
campionamento "farthest-point" per massimizzare la copertura spaziale per
provincia — vedi [ETL](etl-pipeline.md)). Rieseguita l'intera catena a
valle: `identify_heatwaves()` (145 ondate), viste KPI, tutti e 4 i moduli
di `src/analysis/`, i 3 progetti QGIS, tutte le pagine dashboard. Risultato
più significativo: **Moran's I passa da non significativo (p=0.732, n=8) a
statisticamente significativo (I=0.101, p=0.002, n=44)** — vedi
[Analisi Statistica](statistical-analysis.md). Nel farlo, scoperto e
risolto un bug di encoding vecchio di 11 giorni (28 comuni su 1180 con nomi
corrotti nel DB, mai notato prima — vedi [Fonti Dati](data-sources.md)).

**Aggiornamento 2026-07-15 (ampliamento contenuto dashboard)**: su
richiesta esplicita dell'utente, contenuto delle 3 pagine di analisi
ampliato sostanzialmente (dettaglio completo in
[Dashboard](dashboard.md)): anomalie termiche, confronto stagionale,
boxplot per quinquennio e confronto con letteratura in Analisi Temporale;
mappe coropletiche per provincia (via `ST_Union` PostGIS), mappa del trend
per comune, fasce altitudinali e isola di calore urbana in Analisi
Spaziale; conteggio cumulato, mappa di concentrazione e heatmap
"calendario" in Ondate di Calore. Aggiunta anche una sidebar di filtri
globali (anni/provincia, persistiti tra le pagine) e una home con card di
navigazione al posto dei link testuali. Per la fascia altitudinale è stato
necessario popolare `municipalities.elevation_m` (prima sempre `NULL`) —
scaricato per davvero da Open-Meteo Elevation API per i 44 comuni con dati
(scelta confermata con l'utente, invece di un placeholder "non
disponibile") — vedi [Fonti Dati](data-sources.md) e
[Modello Dati](data-model.md).

**Aggiornamento 2026-07-17 (estensione a 63 comuni + dati fino ad oggi)**:
su richiesta esplicita dell'utente ("coprimi i 1180 comuni piemontesi, e
aggiorna la data fino ad oggi"). Obiettivo iniziale enorme (1180 comuni)
ridimensionato insieme all'utente dopo aver spiegato costi/rischi reali
(vedi [Fonti Dati](data-sources.md) per il dettaglio): tentativi falliti a
300 e poi 56 comuni extra per lo stesso motivo — **Open-Meteo ha un limite
giornaliero di richieste** (non solo "al minuto" come già noto), scoperto
nel modo peggiore (~5h40 di download quasi tutto sprecato il primo giorno,
perso perché lo script salvava solo a fine esecuzione). Corretto alla
radice: salvataggio incrementale (ogni comune scaricato viene subito
scritto su disco) in `download_extra_municipalities.py` e nel nuovo
`update_recent_data.py`, così nessuna interruzione futura fa più perdere
progresso. Risultato netto in due giorni: **44 → 63 comuni** (19
aggiuntivi, selezionati con lo stesso campionamento "farthest-point" di
prima) e **tutti i 63 comuni ora arrivano fino a oggi** (non più fermi al
31/12/2025) — non i 1180 completi, ma un incremento reale ottenuto in modo
sostenibile invece di un tentativo fallito in blocco. Vedi
[Fonti Dati](data-sources.md) per il dettaglio della scoperta del rate
limit giornaliero, [ETL](etl-pipeline.md) per il flusso incrementale, e
[Analisi Statistica](statistical-analysis.md) per i risultati ricalcolati
(Moran's I ora 0.132, p=0.001, ancora più significativo che con 44 comuni).

Nello stesso aggiornamento, **2 bug reali trovati e corretti** per via del
nuovo dato che arriva fino al 2026 (non più fermo al 2025): (1)
`frequency_by_year()` in `heatwave_stats.py` aveva un `reindex` fisso
`range(2000, 2026)` che scartava in silenzio le ondate del 2026 (16 ondate
nascoste, trovate verificando l'output dopo l'estensione) — reso
dinamico sul range anni realmente presente nei dati; (2) lo slider
dell'intervallo anni nella dashboard (`components/filters.py`) aveva
`YEAR_MIN, YEAR_MAX = 2000, 2025` fissi nel codice, che avrebbe reso
impossibile selezionare il 2026 una volta arrivati i dati più recenti —
resi dinamici dalla data reale più vecchia/più recente in `temperature`.

Prossimi passi, in ordine (tutti minori/non bloccanti — il nucleo
pianificato del progetto è completo):

1. ~~Aprire i 3 `.qgz` in QGIS Desktop per confermare visivamente le
   etichette~~ — **fatto e confermato dall'utente il 2026-07-15**, incluso
   un fix successivo per le etichette mancanti in `evolution_animation.qgz`
2. ~~Popolare `elevation_m`~~ — **fatto parzialmente il 2026-07-15**, ma
   solo per i 44 comuni con dati di temperatura (Open-Meteo Elevation API,
   vedi [Modello Dati](data-model.md)); `population` resta `NULL` per tutti
   i 1180 comuni, servirebbe un dataset ISTAT demografico separato
3. Riavviare `postgresql-x64-16` come vero servizio Windows (oggi gira via
   `pg_ctl` manuale — il servizio in sé risulta "Stopped" e non
   ripartirebbe da solo dopo un riavvio del PC)
4. Ricordarsi di rifare `REFRESH MATERIALIZED VIEW` dopo ogni futuro
   caricamento di `temperature` (vedi [Modello Dati](data-model.md))
5. Mappa "Heatwave Index" (composito intensità/frequenza ondate) — unica
   mappa pianificata non ancora costruita (vedi [Mappe GIS](gis-maps.md))
6. ~~Test unitari (`tests/` vuota)~~ — **fatto il 2026-07-15**, 31 test
   pytest, vedi [Test Unitari](testing.md); resta da scrivere una
   documentazione API/tutorial
7. Retry più generico per errori di rete transitori (non solo `429`) in
   `download_data.py` — scoperto durante il download dei comuni extra
   (vedi [Analisi Statistica](statistical-analysis.md))
8. ~~Contenuto delle 3 pagine di analisi della dashboard troppo essenziale~~
   — **ampliato sostanzialmente il 2026-07-15** (anomalie, stagionalità,
   boxplot per quinquennio, mappe coropletiche per provincia, fasce
   altitudinali, isola di calore urbana, heatmap calendario delle ondate,
   sidebar filtri globali) — vedi [Dashboard](dashboard.md)
9. **Valutare il deploy pubblico gratuito della dashboard** (Streamlit
   Community Cloud) — discusso il 2026-07-15, rimandato. Blocco tecnico
   noto: la dashboard si connette a Postgres/PostGIS su `localhost`, non
   raggiungibile da un server remoto. Due strade possibili da valutare:
   (a) database Postgres/PostGIS gratuito in cloud (es. Supabase/Neon,
   verificare supporto PostGIS nel piano free) con credenziali spostate in
   `st.secrets`; (b) far leggere la dashboard solo dai CSV già in
   `output/`/`data/processed/` (nessuna connessione DB dal vivo, ma niente
   aggiornamento automatico se in futuro si ricaricano dati nuovi). Vedi
   [Dashboard](dashboard.md).

**Aggiornamento 2026-07-17 (NDVI — fatto)**: terza covariata esplicativa
per il paper (dopo popolazione e CORINE, fatte il 2026-07-16) — vedi
[Articolo scientifico](paper-scientifico.md). Decisione presa con
l'utente: Copernicus Global Land Service NDVI 300m V3 (prodotto gia'
calcolato, download manuale) invece di Sentinel-2 vero (10m, via GEE o
CDSE Statistical API). Un'apparente scorciatoia verso un prodotto NDVI
10m reale trovata durante la navigazione del portale (HR-VPP) si e'
rivelata un vicolo cieco (non cercabile in questo catalogo) — tornati al
piano originale, gia' confermato disponibile. Il download reale via
Copernicus Browser ha richiesto diversi tentativi (selettore data che non
rispondeva al click, filtri fuorvianti) e ha prodotto un file **globale**
da 3.3 GB (nessun ritaglio lato server per questo prodotto, a differenza
di CLC) — gestito senza saturare la RAM leggendo solo la finestra
Piemonte via `rasterio.windows`. Scala/offset/flag della formula
DN→NDVI **verificati sui metadati embedded del file reale** (non solo
dalla documentazione, che si e' rivelata imprecisa sui codici di flag).

**Risultato**: `municipality_ndvi` popolata per **1180/1180 comuni**
(composito 2026-07-01/2026-07-10). Media regionale NDVI 0.663, range
0.327-0.867. Valori verificati a campione coerenti coi risultati CORINE
gia' noti (Vercelli 0.62 — risaie; Torino 0.40 — urbano con verde
comunale; Bardonecchia/Formazza 0.44-0.49 con deviazione standard alta,
0.26-0.28 — gradiente bosco di fondovalle/roccia nuda in quota). Vedi
[Fonti dati](data-sources.md) per il racconto completo (incluso il
vicolo cieco HR-VPP e le difficolta' del portale) e
[Modello dati](data-model.md) per lo schema.

**Aggiornamento 2026-07-17 (prima iterazione del modello statistico)**:
non appena popolazione/CORINE/NDVI sono state tutte disponibili, prima
esecuzione di `src/analysis/spatial_regression.py` (nuovo script) — OLS
classico (temp ~ elevazione+popolazione+%urbano+NDVI, VIF tutti <5, R²=0.979
dominato dall'elevazione) seguito dal check concordato con l'utente
(Moran's I sui residui): ancora significativo (I=0.081, p=0.001), quindi
costruito anche un vero modello a errore spaziale via `spreg`/`libpysal`
(nuove dipendenze). La regola di Anselin ha dato un esito non ambiguo
(errore spaziale, non lag): lambda=0.738 (p<0.001). **Risultato più
rilevante**: **% urbano diventa statisticamente significativo col segno
atteso solo nel modello spaziale** (l'OLS classico lo mascherava) — prima
conferma quantitativa, seppur provvisoria vista la numerosità campionaria
ridotta (n=63), dell'ipotesi originale del paper su citta'/urbanizzazione
come fattore esplicativo. NDVI resta significativo ma con segno
controintuitivo (piu' verde → temperatura piu' alta), da approfondire.
Decisione concordata con l'utente su come procedere: **non** aggiungere
subito le altre covariate candidate (pendenza/esposizione da DEM,
distanza dall'acqua, densita' stradale OSM) — si rilancia questa stessa
pipeline via via che il campione di comuni con temperatura cresce
(l'utente lo sta estendendo gradualmente), osservando se il problema di
confondimento/autocorrelazione residua si attenua da solo prima di
aggiungere altra complessita'. Vedi
[Analisi statistica](statistical-analysis.md) per il dettaglio tecnico
completo e [Articolo scientifico](paper-scientifico.md) per l'impatto sul
piano del paper.

**Aggiornamento 2026-07-17 (35 comuni extra, scaricati da una seconda
macchina — in attesa di import)**: una collaboratrice, senza accesso al
database del titolare, ha ricostruito quali comuni fossero già coperti
leggendo le preview PNG dei progetti QGIS (tracciate in Git a differenza
dei dati), poi scaricato 35 comuni aggiuntivi da Open-Meteo fino al blocco
del rate limit giornaliero — vedi
[Fonti Dati](data-sources.md#download-collaborativo-da-una-seconda-macchina--35-comuni-extra-2026-07-17)
per il metodo (verificabile) e un bug reale trovato e corretto durante
l'esecuzione (confronto `int`/`str` su `istat_code` che causava download
duplicati). **Il file non è ancora nel database**: servono ancora pulizia
(`DataCleaner`) e risoluzione `istat_code` → `municipality_id` prima di
`insert_temperature_for_municipalities()` — passi documentati in
[Pipeline ETL](etl-pipeline.md#comuni-extra-in-attesa-di-import-2026-07-17).
Se importati per intero: 63 → **98 comuni** in `temperature`.

## Discrepanze da tenere a mente quando si presenta il progetto

`README.md` e `PROJECT_SUMMARY.md` descrivono metriche come "1.7M record",
"Status: Production Ready", "database size 3-5 GB" — sono **target
pianificati**, scritti prima di scrivere il codice, non misurazioni reali.
Utile saperlo per non presentarli come risultati raggiunti in un colloquio o
in una demo.

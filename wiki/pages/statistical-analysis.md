# Analisi statistica e spaziale (`src/analysis/`)

**Sorgenti**: `src/analysis/trend_analysis.py`, `src/analysis/heatwave_stats.py`,
`src/analysis/seasonal_analysis.py`, `src/analysis/spatial_analysis.py`.

Implementata ed eseguita per la prima volta su dati reali il 2026-07-15,
dopo che la pipeline ETL (vedi [ETL](etl-pipeline.md)) aveva reso disponibili
75.976 righe di temperatura, 51 ondate di calore e le viste KPI popolate.

**Granularità**: 8 comuni capoluogo → 44 comuni (2026-07-15) → **63 comuni
(2026-07-17)**, sempre con lo stesso campionamento "farthest-point" per
copertura spaziale (vedi [ETL](etl-pipeline.md)). Dal 2026-07-17 il
periodo coperto arriva anche **fino a oggi**, non più fermo al 31/12/2025.
Tutti i numeri qui sotto sono aggiornati alla versione a 63 comuni; dove
rilevante è indicato anche il risultato precedente per confronto.

## Aggiornamento 2026-07-17 — da 44 a 63 comuni, dati fino ad oggi

Richiesta esplicita dell'utente: coprire tutti i 1180 comuni piemontesi e
portare i dati fino ad oggi. Obiettivo ridimensionato insieme all'utente
dopo aver scoperto (nel modo peggiore) che **Open-Meteo ha un limite
giornaliero di richieste**, non solo "al minuto" come già documentato —
vedi [Fonti Dati](data-sources.md) per il racconto completo (due tentativi
falliti, uno sprecato per ~5h40 perché lo script non salvava
incrementalmente). Risultato netto: **+19 comuni** (44→63) più
l'estensione temporale a tutti e 63 fino a oggi, ottenuti in modo
sostenibile con lotti piccoli invece che un tentativo unico in blocco.

**Risultati ricalcolati (63 comuni, 2000 - oggi)**:
- **Trend**: 54/63 comuni con trend significativo (p<0.05), da -0.63 a
  +1.31 °C/decade. Novità: **Briga Alta è l'unico comune con un
  raffreddamento significativo** (-0.63°C/decade, p=0.0014) — un risultato
  controcorrente rispetto al resto del campione, non ancora indagato a
  fondo (possibili cause: microclima locale, breve serie rispetto alla
  variabilità, o semplice rumore anche se il p-value è basso — un solo
  comune anomalo su 63 non permette conclusioni, ma è onesto segnalarlo
  invece di ometterlo).
- **Ondate di calore**: **190 ondate totali** (145 fino al 2025 + 16 nuove
  nel solo 2026, primi 7 mesi dell'anno — coerente con un'estate 2026
  già calda). La disponibilità di dati 2026 ha anche fatto emergere un bug
  (vedi sotto).
- **Moran's I = 0.1319** (atteso sotto casualità: -0.016), **p=0.001 —
  ancora più significativo che con 44 comuni** (era 0.1006, p=0.002).
- **Cluster K-means (k=3)**, ricomposizione con i 19 comuni nuovi:
  - **Cluster 0, alpino** (3.7°C medi, 14 comuni): Acceglio, Aisone,
    Alagna Valsesia, Bardonecchia, Briga Alta, Ceresole Reale, Claviere,
    Entracque, Formazza, Gravere, Macugnaga, Rorà, Sauze di Cesana,
    Usseglio.
  - **Cluster 1, intermedio** (11.4°C medi, 30 comuni): la maggioranza dei
    comuni pedemontani/collinari (Biella, Cuneo, Verbania, ecc.) più molti
    dei 19 nuovi.
  - **Cluster 2, pianura calda** (13.1°C medi, 18 comuni): Alessandria,
    Asti, Torino, Vercelli, Novara e altri comuni di pianura.

**Bug reale trovato e corretto grazie al dato 2026**: `frequency_by_year()`
in `heatwave_stats.py` aveva un `reindex(range(2000, 2026))` fisso nel
codice — un anno finale hardcoded che, con dati fermi al 2025, non aveva
mai fatto danni, ma che con l'arrivo dei dati 2026 **scartava in silenzio
le 16 ondate di quest'anno** dal grafico a barre della dashboard (nessun
errore, semplicemente sparivano). Scoperto confrontando il conteggio
diretto da `heatwave_events` (190) con l'output della funzione (174,
mancavano esattamente le 16 del 2026). Fix: range dinamico
(`df['year'].min()`/`.max()`) invece di limiti fissi nel codice — stesso
tipo di bug, root cause diversa, del reindex già visto altrove nel
progetto (vincoli "temporanei" scritti come costanti fisse che invecchiano
male). Stesso bug trovato e corretto anche nella dashboard
(`components/filters.py`: `YEAR_MIN, YEAR_MAX = 2000, 2025` fisso, reso
dinamico dalla data reale in `temperature`).

## `trend_analysis.py` — trend di riscaldamento

CLI: `python -m src.analysis.trend_analysis`

- `load_annual_temperature()` — legge `temp_mean_annual` per comune/anno da
  `kpi_annual_by_municipality`
- `mann_kendall_trend()` — test di Mann-Kendall (`pymannkendall.original_test`):
  rileva se c'è un trend monotono, senza assumere normalità
- `linear_trend()` — regressione lineare (`scipy.stats.linregress`): stima
  la pendenza in °C/anno e °C/decade
- Output: `output/trend_analysis.csv`

**Risultato reale (2000-2025, 44 comuni)**: 38 comuni su 44 mostrano un
trend crescente statisticamente significativo (p<0.05), tra +0.3 e +1.4
°C/decade (Bagnolo Piemonte il più ripido). Coerente con il segnale di
riscaldamento osservato nel Nord Italia — e ora osservato in modo diffuso
su tutto il territorio piemontese, non solo negli 8 capoluoghi (risultato
originario a 8 comuni: 7/8 significativi, +0.4/+1.0 °C/decade).

## `heatwave_stats.py` — statistiche sulle ondate di calore

CLI: `python -m src.analysis.heatwave_stats`

- `backfill_intensity_and_mean_temp()` — popola `heatwave_events.intensity_index`
  (= `(max_temp - heat_threshold) * duration_days`) e `mean_temp` (media di
  `temperature.temp_mean` nel periodo dell'ondata), lasciati `NULL` da
  `identify_heatwaves()` (vedi [Modello Dati](data-model.md))
- `summary_by_municipality()` — conteggio, durata media/max, intensità
  media/max per comune
- `frequency_by_year()` — conteggio ondate per anno (2000-2025, anni senza
  ondate inclusi come 0); **estesa il 2026-07-15** per includere anche
  `avg_duration_days`/`avg_intensity` per anno, non solo il conteggio —
  usate dal grafico a barre a doppio asse della pagina "Ondate di Calore"
  della dashboard
- Output: `output/heatwave_stats_by_municipality.csv`,
  `output/heatwave_frequency_by_year.csv`

**Risultato reale (44 comuni)**: 145 ondate totali (51 sugli 8 capoluoghi
originari + 94 sui 36 comuni extra). Alessandria resta il comune con più
ondate (14), seguita dal nuovo comune Casalnoceto (13) e Asti (11).
Diversi comuni alpini tra i 36 extra (Formazza, Macugnaga, Acceglio,
Alagna Valsesia, Bardonecchia, Ceresole Reale, Rorà, Aisone) non hanno mai
raggiunto 3 giorni consecutivi sopra i 35°C nel periodo (0 ondate),
coerente con la loro quota/clima alpino — lo stesso vale per Biella e
Verbania tra gli 8 capoluoghi originari.

## `seasonal_analysis.py` — scomposizione stagionale (STL)

CLI: `python -m src.analysis.seasonal_analysis`

- `load_daily_series()` — serie giornaliera continua di `temp_mean` per
  comune (nessun gap nei dati reali: verificato che `asfreq('D')` non
  introduce `NaN`)
- `decompose()` — STL decomposition (`statsmodels.tsa.seasonal.STL`,
  `period=365`, `robust=True`) in trend / stagionalità / residuo
- Output: `output/seasonal_decomposition/{comune}_stl.csv` (serie completa
  giorno per giorno), `output/seasonal_trend_summary.csv` (riepilogo)

**Risultato reale (44 comuni)**: ampiezza stagionale 27-34°C, più ampia nei
comuni alpini/di alta quota (Bardonecchia 34.3°C, Macugnaga 33.4°C,
Formazza 32.6°C — inverni più rigidi) e più contenuta nei comuni di
pianura vicino ai laghi/pedemontani (Verbania 27.8°C, Ghemme 27.9°C).
Componente di trend in aumento in 43 comuni su 44 (unica eccezione:
Carrega Ligure, -0.04°C, sostanzialmente piatta), direzione coerente con
Mann-Kendall/regressione lineare (l'entità numerica differisce
leggermente per via della metodologia diversa: STL confronta due medie
annuali sulla componente smussata, la regressione lineare usa tutti i 26
anni).

**Rieseguita il 2026-07-17 su 63 comuni** (~27 minuti, eseguita in
background per via del tempo di calcolo su 63 serie giornaliere estese
fino ad oggi): componente di trend in aumento in **62 comuni su 63**.
L'unica eccezione è ora **Briga Alta** (-1.56°C di variazione totale di
trend), uno dei 19 comuni aggiunti — **stesso identico comune** segnalato
come raffreddamento significativo da Mann-Kendall/regressione lineare
(-0.63°C/decade, p=0.0014). Le due metodologie, completamente
indipendenti (STL confronta medie smussate a inizio/fine periodo, Mann-
Kendall+regressione guardano l'intera serie annuale), **concordano sullo
stesso comune anomalo** — un indizio che il segnale è reale e non un
artefatto di un singolo metodo, pur restando un solo caso su 63 che non
permette conclusioni forti sulle cause.

## `spatial_analysis.py` — Moran's I e clustering climatico

CLI: `python -m src.analysis.spatial_analysis`

- `build_inverse_distance_weights()` — matrice pesi spaziali W, inverso
  della distanza haversine tra i centroidi dei comuni, row-standardized
- `morans_i()` / `morans_i_permutation_test()` — indice di Moran calcolato
  a mano (nessuna dipendenza aggiuntiva tipo `libpysal`/`esda`);
  significatività via **test di permutazione** (999 permutazioni) anziché
  l'approssimazione normale asintotica classica, più robusta con un
  campione piccolo
- `climate_clustering()` — K-means (k=3) su temperatura media, giorni
  >30°C, giorni >35°C standardizzati. **Etichette rinumerate per
  temperatura crescente (2026-07-16)**: le etichette grezze di sklearn
  (0/1/2) sono assegnate in un ordine arbitrario, senza legame con quanto
  è caldo il gruppo — su richiesta dell'utente ("non c'è una logica di
  ordinamento"), rimappate così che il cluster **0 sia sempre il più
  fresco e il 2 sempre il più caldo**, una convenzione stabile anche se
  l'analisi viene ri-eseguita e sklearn assegna le etichette grezze in un
  ordine diverso.
- Output: `output/spatial_analysis.csv`, `output/morans_i_summary.csv`

**Aggiornamento 2026-07-15 — da 8 a 44 comuni**: il campione iniziale di 8
unità spaziali (i soli capoluoghi) era sotto la soglia comunemente citata
come minima per un'analisi di autocorrelazione spaziale robusta
(tipicamente 20-30 unità), e infatti dava un risultato non significativo.
Estesa la copertura a 44 comuni (vedi [ETL](etl-pipeline.md) per come sono
stati scelti) su richiesta esplicita dell'utente, proprio per superare
questo limite. Risultato:

- **Moran's I = 0.1006** (atteso sotto casualità: -0.0244), **p=0.002 su
  999 permutazioni — statisticamente significativo** (era -0.096, p=0.732,
  non significativo, con 8 comuni). I comuni geograficamente vicini hanno
  temperature realmente più simili tra loro di quanto ci si aspetterebbe
  per caso: il segnale climatico ha una struttura spaziale reale, non è
  rumore geografico. Con 44 unità il test ha ora la sensibilità per
  rilevarlo.
- Clustering K-means (k=3), ora molto più nitido geograficamente (etichette
  0/1/2 = dal più fresco al più caldo, vedi sopra):
  - **Cluster 0, alpino** (3.8°C medi): Acceglio, Aisone, Alagna Valsesia,
    Bardonecchia, Ceresole Reale, Formazza, Macugnaga, Rorà — tutti comuni
    di alta quota, ai margini montani nord e sud-ovest della regione.
  - **Cluster 1, intermedio** (11.1°C medi): comuni pedemontani/collinari
    (Biella, Cuneo, Verbania, ecc.).
  - **Cluster 2, pianura calda** (12.9°C medi): Alessandria, Asti, Torino,
    Vercelli e altri comuni della pianura centro-orientale.

  Verificato visivamente anche nelle mappe QGIS (`hotspot_analysis.qgz`,
  vedi [Mappe GIS](gis-maps.md)): il pattern geografico è visibilmente
  coerente (blu=alpino ai margini montani, rosso=pianura calda al
  centro-est — stessa palette blu→rosso della dashboard, non più colori
  categorici arbitrari), non più solo un'etichetta statistica.

Restano comunque solo 44 dei 1180 comuni piemontesi — un'analisi ancora
più esaustiva richiederebbe temperature per un sottoinsieme più ampio
(vedi [ETL](etl-pipeline.md)), ma il salto qualitativo da "campione troppo
piccolo per dire qualcosa" a "risultato statisticamente significativo" è
già stato fatto.

## Dipendenze aggiunte

`pymannkendall==1.4.3`, `scikit-learn==1.9.0`, `statsmodels==0.14.6`
(aggiunte a `requirements.txt` il 2026-07-15). Moran's I è implementato a
mano per evitare di aggiungere `libpysal`/`esda` per un solo calcolo, dato
il campione ridotto.

## Bug incontrati durante l'implementazione

- `AVG()` di PostgreSQL su colonne intere (es. `days_gt_30c SMALLINT`)
  restituisce `NUMERIC`, letto da psycopg2 come `decimal.Decimal` — in
  conflitto con le colonne `float` quando si fanno operazioni pandas
  (`TypeError: unsupported operand type(s) for -: 'decimal.Decimal' and
  'float'`). Fix: cast esplicito `::float` nella query SQL.
- Query con nome comune interpolato via f-string in `seasonal_analysis.py`
  (bozza iniziale) — corretto in query parametrizzata (`sqlalchemy.text`
  con parametri), anche se il valore veniva comunque da una query interna
  fidata, non da input utente: pattern da evitare comunque.

## Bug incontrati estendendo a 44 comuni (2026-07-15)

- **`identify_heatwaves()` non è idempotente**: ri-eseguirla dopo aver
  aggiunto i 36 comuni extra avrebbe duplicato le 51 ondate già trovate
  per gli 8 capoluoghi (nessun controllo di esistenza prima dell'`INSERT`).
  Fix operativo: `TRUNCATE TABLE heatwave_events` prima di ri-eseguirla —
  sicuro perché è dato interamente derivato/ricalcolabile da `temperature`.
- **Bug di encoding storico scoperto per caso**: durante il download dei
  comuni extra, 2 nomi (Rorà, Cavaglià) sono usciti corrotti nel CSV. La
  causa non era nel nuovo codice, ma in un bug del 2026-07-04 mai notato
  prima (`encoding='cp1252'` invece di `'utf-8'` nella lettura dello
  shapefile ISTAT, che corrompeva il 100% dei nomi con caratteri accentati
  nel database — 28 comuni su 1180). Vedi [Fonti Dati](data-sources.md) per
  il dettaglio completo del fix.
- **Errore di connessione TLS non gestito dal retry esistente**: 5 dei 36
  comuni extra sono falliti al primo download per
  `ConnectionResetError`/`ProtocolError` (non un `429`) — il retry-on-429
  di `download_for_coordinates()` non copre questo caso, l'eccezione si
  propaga e la provincia/comune viene solo loggato e saltato. Risolto
  ri-scaricando manualmente i 5 comuni mancanti in una seconda passata,
  non ancora corretto nel codice (nessun retry generico su errori di rete
  transitori — voce aperta per il futuro).
- **`UnicodeEncodeError` ripetuto su console Windows**: ogni messaggio di
  log contenente "✓"/"✗" falliva silenziosamente sulla console (cp1252 di
  Windows non ha questi caratteri), con loguru che stampava un traceback di
  errore invece del messaggio — non bloccante ma molto rumoroso su run
  lunghi. Fix in `src/utils/logger.py`: `sys.stdout.reconfigure(encoding=
  'utf-8')` prima di configurare l'handler console.

## Prossimi passi

Queste analisi producono CSV in `output/` — usati in mappe GIS (QGIS) e
nella dashboard Streamlit (vedi [Mappe GIS](gis-maps.md),
[Dashboard](dashboard.md)), entrambe già aggiornate ai 44 comuni. Resta
aperta la tabella `kpi` (che ha `annual_anomaly`, non ancora calcolabile
senza una baseline 1961-1990 — vedi [Catalogo KPI](kpi-catalog.md)), e un
retry più generico per errori di rete transitori in `download_data.py`
(vedi bug sopra).

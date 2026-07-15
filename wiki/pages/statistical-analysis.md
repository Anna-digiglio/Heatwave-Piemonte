# Analisi statistica e spaziale (`src/analysis/`)

**Sorgenti**: `src/analysis/trend_analysis.py`, `src/analysis/heatwave_stats.py`,
`src/analysis/seasonal_analysis.py`, `src/analysis/spatial_analysis.py`.

Implementata ed eseguita per la prima volta su dati reali il 2026-07-15,
dopo che la pipeline ETL (vedi [ETL](etl-pipeline.md)) aveva reso disponibili
75.976 righe di temperatura, 51 ondate di calore e le viste KPI popolate.

**Granularità**: tutte le analisi lavorano sugli **8 comuni capoluogo di
provincia**, unica granularità con dati di temperatura reali (vedi
[ETL](etl-pipeline.md) per la motivazione). Dove il campione è
particolarmente piccolo per il tipo di analisi (statistiche spaziali), è
segnalato esplicitamente sotto.

## `trend_analysis.py` — trend di riscaldamento

CLI: `python -m src.analysis.trend_analysis`

- `load_annual_temperature()` — legge `temp_mean_annual` per comune/anno da
  `kpi_annual_by_municipality`
- `mann_kendall_trend()` — test di Mann-Kendall (`pymannkendall.original_test`):
  rileva se c'è un trend monotono, senza assumere normalità
- `linear_trend()` — regressione lineare (`scipy.stats.linregress`): stima
  la pendenza in °C/anno e °C/decade
- Output: `output/trend_analysis.csv`

**Risultato reale (2000-2025)**: 7 comuni su 8 mostrano un trend crescente
statisticamente significativo (p<0.05), tra +0.4 e +1.0 °C/decade. Asti è
borderline (p=0.098, non significativo al livello 0.05). Coerente con il
segnale di riscaldamento osservato nel Nord Italia.

## `heatwave_stats.py` — statistiche sulle ondate di calore

CLI: `python -m src.analysis.heatwave_stats`

- `backfill_intensity_and_mean_temp()` — popola `heatwave_events.intensity_index`
  (= `(max_temp - heat_threshold) * duration_days`) e `mean_temp` (media di
  `temperature.temp_mean` nel periodo dell'ondata), lasciati `NULL` da
  `identify_heatwaves()` (vedi [Modello Dati](data-model.md))
- `summary_by_municipality()` — conteggio, durata media/max, intensità
  media/max per comune
- `frequency_by_year()` — conteggio ondate per anno (2000-2025, anni senza
  ondate inclusi come 0)
- Output: `output/heatwave_stats_by_municipality.csv`,
  `output/heatwave_frequency_by_year.csv`

**Risultato reale**: 2003 (11 ondate) e 2019 (9 ondate) sono gli anni con
più ondate rilevate — coerente con le note ondate di calore europee di
quegli anni. Frequenza in crescita negli anni recenti (2022: 5, 2023: 5,
2025: 3) rispetto al primo decennio (2000-2010: solo 2003 e 2006 con
ondate). Biella e Verbania non hanno mai raggiunto 3 giorni consecutivi
sopra i 35°C nel periodo (0 ondate).

## `seasonal_analysis.py` — scomposizione stagionale (STL)

CLI: `python -m src.analysis.seasonal_analysis`

- `load_daily_series()` — serie giornaliera continua di `temp_mean` per
  comune (nessun gap nei dati reali: verificato che `asfreq('D')` non
  introduce `NaN`)
- `decompose()` — STL decomposition (`statsmodels.tsa.seasonal.STL`,
  `period=365`, `robust=True`) in trend / stagionalità / residuo
- Output: `output/seasonal_decomposition/{comune}_stl.csv` (serie completa
  giorno per giorno), `output/seasonal_trend_summary.csv` (riepilogo)

**Risultato reale**: ampiezza stagionale ~28-32°C in tutti i comuni
(coerente con un clima continentale, inverni freddi ed estati calde);
componente di trend in aumento in tutti gli 8 comuni (dal confronto tra
media del primo e dell'ultimo anno della componente di trend smussata),
direzione coerente con Mann-Kendall/regressione lineare (l'entità numerica
differisce leggermente per via della metodologia diversa: STL confronta due
medie annuali sulla componente smussata, la regressione lineare usa tutti i
26 anni).

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
  >30°C, giorni >35°C standardizzati
- Output: `output/spatial_analysis.csv`, `output/morans_i_summary.csv`

**⚠️ Limite campionario**: solo 8 unità spaziali disponibili (i comuni
capoluogo). Questo è **sotto la soglia comunemente considerata minima per
un'analisi di autocorrelazione spaziale robusta** (tipicamente si vogliono
almeno 20-30 unità). I risultati sono illustrativi:

- Moran's I = -0.096 (atteso sotto casualità: -0.140), p=0.732 —
  nessuna autocorrelazione spaziale significativa rilevabile con questo
  campione.
- Clustering K-means (k=3): {Alessandria, Asti, Vercelli} (pianura, più
  caldo) / {Biella, Cuneo} (pedemontano, più fresco) / {Novara, Torino,
  Verbania} (intermedio) — geograficamente sensato, ma con n=8 va
  presentato come indicativo, non come risultato statisticamente
  conclusivo.

Un'analisi spaziale realmente robusta richiederebbe temperature per un
sottoinsieme più ampio dei 1180 comuni piemontesi (oggi non disponibili,
vedi [ETL](etl-pipeline.md) — Open-Meteo è stato interrogato solo per gli
8 capoluoghi).

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

## Prossimi passi

Queste analisi producono CSV in `output/` — il passo successivo naturale è
usarli in mappe GIS (QGIS) e nella dashboard Streamlit (vedi
[Mappe GIS](gis-maps.md), [Dashboard](dashboard.md)), oppure popolare la
tabella `kpi` (che ha `annual_anomaly`, non ancora calcolabile senza una
baseline 1961-1990 — vedi [Catalogo KPI](kpi-catalog.md)).

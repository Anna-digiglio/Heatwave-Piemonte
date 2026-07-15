# Glossario dei concetti statistici e GIS

**Sorgenti**: `README.md`, `docs/ROADMAP.md`, `docs/ARCHITECTURE.md`,
`src/analysis/*.py` (implementati ed eseguiti su dati reali il 2026-07-15).

Pensato come ponte tra la formazione in Scienze Naturali dell'autore e il
vocabolario tipico di data engineering/BI.

- **Test di Mann-Kendall** — test statistico non parametrico per rilevare un
  trend monotono (crescente/decrescente) in una serie temporale, senza
  assumere normalità dei dati. Usato per verificare se la temperatura media
  annuale ha un trend reale nel 2000-2025, distinguendolo dal rumore
  anno-su-anno. **Implementato** in `src/analysis/trend_analysis.py`
  (`pymannkendall.original_test`) — risultato reale: 7 comuni su 8 mostrano
  un trend crescente significativo (p<0.05), vedi [Stato del Progetto](project-status.md).
- **Regressione lineare del trend** — stima della pendenza °C/anno (o
  °C/decade) per comune; complementare a Mann-Kendall (che dice *se* c'è un
  trend, la regressione dice *quanto*). **Implementata** in
  `trend_analysis.py` (`scipy.stats.linregress`) — trend reali tra +0.4 e
  +1.0 °C/decade nei comuni con trend significativo.
- **Indice di Moran (Moran's I)** — misura di autocorrelazione spaziale:
  quantifica se comuni vicini hanno valori di temperatura simili (clustering
  spaziale) più di quanto ci si aspetterebbe per caso. **Implementato** in
  `src/analysis/spatial_analysis.py` (matrice pesi spaziali = inverso della
  distanza haversine, row-standardized; significatività via test di
  permutazione, più robusto dell'approssimazione normale asintotica con un
  campione piccolo). **Limite importante**: con solo 8 unità spaziali (i
  comuni capoluogo, unica granularità con temperature reali — vedi
  [ETL](etl-pipeline.md)) il risultato (I=-0.096, p=0.73, non significativo)
  è illustrativo, non un'analisi di autocorrelazione spaziale statisticamente
  robusta. Servirebbero dati per molti più comuni.
- **STL decomposition** (Seasonal-Trend decomposition using Loess) — scompone
  una serie temporale giornaliera in componenti trend, stagionalità e
  residuo. Utile per isolare il trend di riscaldamento dalla normale
  variazione stagionale (estate/inverno). **Implementata** in
  `src/analysis/seasonal_analysis.py` (`statsmodels.tsa.seasonal.STL`,
  periodo 365 giorni, `robust=True`) per tutti gli 8 comuni — ampiezza
  stagionale reale ~28-32°C, coerente con un clima continentale.
- **IQR outlier method** — un valore è outlier se fuori da
  `[Q1 - 1.5·IQR, Q3 + 1.5·IQR]` dove `IQR = Q3 - Q1`. Metodo robusto (non
  assume normalità), implementato in `DataCleaner.detect_outliers()`
  (vedi [ETL Pipeline](etl-pipeline.md)).
- **Clustering K-means su feature climatiche** — raggruppa comuni in zone
  climatiche omogenee. **Implementato** in `spatial_analysis.py`, usando
  temperatura media, giorni >30°C e giorni >35°C (standardizzati) come
  feature, k=3. Risultato reale e geograficamente sensato: cluster
  Alessandria/Asti/Vercelli (pianura, più caldo), Biella/Cuneo (pedemontano,
  più fresco), Novara/Torino/Verbania (intermedio). Anche qui, n=8 comuni è
  un campione piccolo — il risultato è indicativo, non definitivo.
- **Ondata di calore (definizione operativa del progetto)** — sequenza di
  ≥3 giorni consecutivi con `temp_max` sopra una soglia (30/35/40°C),
  implementata in `identify_heatwaves()` (vedi [Modello Dati](data-model.md)).
  È una definizione semplificata rispetto a indici climatologici standard
  (es. WMO usa percentili locali anziché soglie fisse), scelta qui per
  semplicità e interpretabilità in un progetto portfolio. Statistiche
  aggregate (durata, intensità, frequenza per anno) in
  `src/analysis/heatwave_stats.py`.
- **Anomalia termica** — differenza tra la temperatura osservata e una
  climatologia di riferimento (qui 1961-1990). Nel dataset attuale (che parte
  dal 2000) questa baseline non è disponibile direttamente: va importata da
  altra fonte (es. Copernicus/ARPA) o approssimata. **Non ancora implementata**.

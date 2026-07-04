# Glossario dei concetti statistici e GIS

**Sorgenti**: `README.md`, `docs/ROADMAP.md`, `docs/ARCHITECTURE.md` (nessuno di
questi concetti ha ancora codice Python associato — sono tutti pianificati per
`src/analysis/`, oggi vuota).

Pensato come ponte tra la formazione in Scienze Naturali dell'autore e il
vocabolario tipico di data engineering/BI.

- **Test di Mann-Kendall** — test statistico non parametrico per rilevare un
  trend monotono (crescente/decrescente) in una serie temporale, senza
  assumere normalità dei dati. Usato qui per verificare se la temperatura
  annuale ha un trend reale nel 2000-2026, distinguendolo dal rumore
  anno-su-anno.
- **Regressione lineare del trend** — stima della pendenza °C/anno per
  provincia; complementare a Mann-Kendall (che dice *se* c'è un trend, la
  regressione dice *quanto*).
- **Indice di Moran (Moran's I)** — misura di autocorrelazione spaziale:
  quantifica se province/comuni vicini hanno valori di temperatura simili
  (clustering spaziale) più di quanto ci si aspetterebbe per caso. Risponde
  alla domanda "esistono differenze territoriali significative o è tutto
  rumore geografico?".
- **STL decomposition** (Seasonal-Trend decomposition using Loess) — scompone
  una serie temporale giornaliera/mensile in componenti trend, stagionalità
  e residuo. Utile per isolare il trend di riscaldamento dalla normale
  variazione stagionale (estate/inverno).
- **IQR outlier method** — un valore è outlier se fuori da
  `[Q1 - 1.5·IQR, Q3 + 1.5·IQR]` dove `IQR = Q3 - Q1`. Metodo robusto (non
  assume normalità), già implementato in `DataCleaner.detect_outliers()`
  (vedi [ETL Pipeline](etl-pipeline.md)).
- **Clustering K-means su coordinate geografiche** — raggruppa comuni in
  zone climatiche omogenee usando lat/lon (+ eventualmente elevazione) come
  feature. Usato per identificare "hotspot climatici" (vedi [Mappe GIS](gis-maps.md)).
- **Ondata di calore (definizione operativa del progetto)** — sequenza di
  ≥3 giorni consecutivi con `temp_max` sopra una soglia (30/35/40°C),
  implementata in `identify_heatwaves()` (vedi [Modello Dati](data-model.md)).
  È una definizione semplificata rispetto a indici climatologici standard
  (es. WMO usa percentili locali anziché soglie fisse), scelta qui per
  semplicità e interpretabilità in un progetto portfolio.
- **Anomalia termica** — differenza tra la temperatura osservata e una
  climatologia di riferimento (qui 1961-1990). Nel dataset attuale (che parte
  dal 2000) questa baseline non è disponibile direttamente: va importata da
  altra fonte (es. Copernicus/ARPA) o approssimata.

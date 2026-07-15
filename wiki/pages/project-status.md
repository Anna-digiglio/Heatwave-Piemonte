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
| Download dati 2000-2026 | ⬜ | ✅ **eseguito il 2026-07-04** — `data/raw/temperature_data.csv`, 75.976 righe, 8 province, 2000-2025 (2026 non incluso, API storica non accetta date future) |
| Dati geografici (ISTAT comuni/province) | ⬜ | ✅ **caricati il 2026-07-04** — 1180 comuni reali in `municipalities` (DB Postgres/PostGIS locale), 8 province con codici ISTAT corretti |
| Python environment / requirements | ⬜ | `.venv` presente, `requirements.txt` presente e dettagliato |

## Settimana 2 — ETL & Analisi

| Attività | Roadmap | Realtà |
|---|---|---|
| `DataCleaner` completo | pianificato | ✅ scritto, **ma non era mai stato eseguibile** fino al 2026-07-04 (`SyntaxError` da newline letterali corrotte + bug che scartava il 99,9% dei dati — vedi [ETL](etl-pipeline.md)). Ora eseguito su dati reali: 75.976/75.976 righe mantenute |
| Caricamento `temperature` nel DB | pianificato | ✅ **eseguito il 2026-07-04** — 75.976 righe reali (8 comuni capoluogo, 2000-2025) in `temperature`, batch insert (vedi [ETL](etl-pipeline.md)) |
| `identify_heatwaves()` eseguita | pianificato | ✅ **eseguita il 2026-07-12** su dati reali — 51 ondate identificate (2000-2025), 2 bug di attribuzione/flush risolti (vedi [Modello Dati](data-model.md)) |
| KPI calcolati | pianificato | ✅ viste materializzate **rinfrescate il 2026-07-12** con dati reali — 208 righe ciascuna (8 comuni/province × 26 anni) |
| Query SQL (10+) | pianificato | 3 query scritte in `02_common_queries.sql` |

## Settimana 3 — Visualizzazione & Deployment

| Attività | Roadmap | Realtà |
|---|---|---|
| `src/analysis/` (statistica, spaziale, temporale) | pianificato | ✅ **implementata ed eseguita su dati reali il 2026-07-15** — trend (Mann-Kendall/regressione), statistiche ondate di calore, STL decomposition, Moran's I + clustering K-means (vedi [Analisi Statistica](statistical-analysis.md)) |
| `src/visualization/` | pianificato | ❌ cartella vuota |
| Progetti QGIS | pianificato | ❌ `qgis_projects/` vuota |
| Dashboard Streamlit | pianificato | ❌ `dashboard/` vuota |
| Test unitari | pianificato (70%+ coverage) | ❌ `tests/` vuota |
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

Prossimi passi, in ordine:

1. Mappe GIS (QGIS) e dashboard Streamlit — ora con dati reali E risultati
   di analisi reali (trend, ondate, cluster climatici) da visualizzare,
   invece di celle vuote
2. **(minore, non bloccante)** correggere `logging.format` in `config.yaml`
   per la sintassi loguru — oggi console e file di log sono illeggibili
   (vedi [Fonti Dati](data-sources.md))
3. **(minore, non bloccante)** popolare `population`/`elevation_m` dei
   comuni con un dataset ISTAT demografico separato (oggi `NULL`, lo
   shapefile dei confini non li include — vedi [Modello Dati](data-model.md))
4. **(minore, non bloccante)** riavviare `postgresql-x64-16` come vero
   servizio Windows (oggi gira via `pg_ctl` manuale — il servizio in sé
   risulta "Stopped" e non ripartirebbe da solo dopo un riavvio del PC)
5. **(minore, non bloccante)** ricordarsi di rifare `REFRESH MATERIALIZED
   VIEW` dopo ogni futuro caricamento di `temperature` — le viste KPI non
   si aggiornano da sole (vedi [Modello Dati](data-model.md))
6. **(minore, non bloccante)** valutare se scaricare temperature reali per
   un sottoinsieme più ampio di comuni (oggi solo 8), per rendere Moran's I
   e il clustering climatico statisticamente più robusti (vedi
   [Analisi Statistica](statistical-analysis.md))

## Discrepanze da tenere a mente quando si presenta il progetto

`README.md` e `PROJECT_SUMMARY.md` descrivono metriche come "1.7M record",
"Status: Production Ready", "database size 3-5 GB" — sono **target
pianificati**, scritti prima di scrivere il codice, non misurazioni reali.
Utile saperlo per non presentarli come risultati raggiunti in un colloquio o
in una demo.

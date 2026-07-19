# Indice — Wiki Heatwave Piemonte

Wiki mantenuta secondo il pattern descritto in `CLAUDE.md` (livello schema).
Ogni pagina cita le sorgenti grezze da cui è sintetizzata — in caso di
dubbio, la sorgente grezza (codice/SQL/config) prevale sempre sulla wiki.

## Panoramica

- [Panoramica del progetto](pages/project-overview.md) — obiettivo, domande di ricerca, stack dichiarato
- [Stato del progetto](pages/project-status.md) — **pianificato vs implementato**, prossimi passi ad alto impatto
- [Articolo scientifico](pages/paper-scientifico.md) — piano verso una pubblicazione peer-reviewed: fasi, dati mancanti (uso del suolo/popolazione), letteratura da citare

## Architettura & infrastruttura

- [Architettura](pages/architecture.md) — flusso a livelli, struttura cartelle reale, pattern di codice
- [Configurazione](pages/config-reference.md) — guida a `config.yaml`

## Dati

- [Fonti dati](pages/data-sources.md) — Open-Meteo, Copernicus ERA5, ARPA, ISTAT, OSM (stato e bug noti)
- [Modello dati](pages/data-model.md) — schema PostgreSQL/PostGIS: tabelle, viste, funzione `identify_heatwaves()`
- [Pipeline ETL](pages/etl-pipeline.md) — extract/transform/load reali, gap noti
- [Comuni già coperti](pages/comuni-coperti.md) — elenco dei 234 comuni già in `temperature` (108 con copertura ARPA), guida al formato per nuovi download collaborativi (evitare doppioni)

## Analisi

- [Analisi statistica e spaziale](pages/statistical-analysis.md) — `src/analysis/`: trend (Mann-Kendall/regressione), ondate di calore, STL, Moran's I, clustering, modello a errore spaziale (temp ~ elevazione/popolazione/uso del suolo/NDVI), **validazione contro stazioni ARPA reali** (108 comuni, bias -1.59°C, correla con elevazione) — eseguita su dati reali
- [Catalogo KPI](pages/kpi-catalog.md) — KPI definiti, formule, dove sono calcolati
- [Query SQL](pages/sql-queries.md) — catalogo query di `sql/02_common_queries.sql`
- [Glossario concetti](pages/concepts.md) — Mann-Kendall, Moran's I, STL, IQR, K-means, definizione di ondata di calore

## Visualizzazione

- [Mappe GIS](pages/gis-maps.md) — 3 progetti QGIS, **generati via PyQGIS ed eseguiti su dati reali**
- [Dashboard](pages/dashboard.md) — dashboard Streamlit, **implementata, eseguita su dati reali e ampliata** (7 pagine, mappe coropletiche PostGIS), **restyling identità "calore" 2026-07-17**, **tema chiaro adattivo per hero/card/stats 2026-07-18**, **selettore fonte Open-Meteo/ARPA/Confronto in Analisi Temporale, Ondate di Calore e Analisi Spaziale 2026-07-18** (la pagina dedicata "Validazione Dati", nata e rimossa lo stesso giorno, è confluita nel selettore), **uso del suolo/popolazione/NDVI spostati dalla pagina Analisi Spaziale a una nuova pagina Contesto Territoriale 2026-07-19**, **nuova pagina Citazioni e Fonti (08) 2026-07-19** — bibliografia + fonti dati con link, in coda a tutte le altre; in arrivo anche una pagina di sintesi divulgativa dell'articolo scientifico (07), in attesa del ricalcolo dati del 2026-07-19

## Qualità del codice

- [Test unitari](pages/testing.md) — 31 test pytest, **un bug reale trovato e corretto** in `DataCleaner.detect_outliers()`

---

Vedi [log.md](log.md) per la cronologia degli aggiornamenti a questa wiki.

# Indice — Wiki Heatwave Piemonte

Wiki mantenuta secondo il pattern descritto in `CLAUDE.md` (livello schema).
Ogni pagina cita le sorgenti grezze da cui è sintetizzata — in caso di
dubbio, la sorgente grezza (codice/SQL/config) prevale sempre sulla wiki.

## Panoramica

- [Panoramica del progetto](pages/project-overview.md) — obiettivo, domande di ricerca, stack dichiarato
- [Stato del progetto](pages/project-status.md) — **pianificato vs implementato**, prossimi passi ad alto impatto

## Architettura & infrastruttura

- [Architettura](pages/architecture.md) — flusso a livelli, struttura cartelle reale, pattern di codice
- [Configurazione](pages/config-reference.md) — guida a `config.yaml`

## Dati

- [Fonti dati](pages/data-sources.md) — Open-Meteo, Copernicus ERA5, ARPA, ISTAT, OSM (stato e bug noti)
- [Modello dati](pages/data-model.md) — schema PostgreSQL/PostGIS: tabelle, viste, funzione `identify_heatwaves()`
- [Pipeline ETL](pages/etl-pipeline.md) — extract/transform/load reali, gap noti

## Analisi

- [Catalogo KPI](pages/kpi-catalog.md) — KPI definiti, formule, dove sono calcolati
- [Query SQL](pages/sql-queries.md) — catalogo query di `sql/02_common_queries.sql`
- [Glossario concetti](pages/concepts.md) — Mann-Kendall, Moran's I, STL, IQR, K-means, definizione di ondata di calore

## Visualizzazione (pianificate, non ancora costruite)

- [Mappe GIS](pages/gis-maps.md) — mappe QGIS previste e prerequisiti mancanti
- [Dashboard](pages/dashboard.md) — struttura Streamlit prevista

---

Vedi [log.md](log.md) per la cronologia degli aggiornamenti a questa wiki.

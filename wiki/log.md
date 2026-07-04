# Log della wiki

Log cronologico append-only. Ogni riga: data, azione, pagine toccate.

- **2026-07-04** — INGEST INIZIALE. Creata la wiki da zero seguendo il pattern
  Karpathy (https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
  applicato al progetto Heatwave Piemonte. Letti come sorgenti grezze:
  `README.md`, `PROJECT_SUMMARY.md`, tutto `docs/*.md`, `config.yaml`,
  `sql/01_init_database.sql`, `sql/02_common_queries.sql`,
  `src/data_acquisition/download_data.py`, `src/data_processing/clean_data.py`,
  `src/database/load_to_db.py`, `src/utils/{config,database}.py`, struttura
  cartelle reale (`find`). Create 10 pagine:
  project-overview, architecture, data-sources, data-model, etl-pipeline,
  config-reference, kpi-catalog, sql-queries, concepts, gis-maps, dashboard,
  project-status. Creato `CLAUDE.md` in root come livello schema. Rilevata
  discrepanza significativa tra documenti di pianificazione (che descrivono
  uno stato molto più avanzato, es. "1.7M record", "Production Ready") e
  codice reale (solo Settimana 1 parziale implementata; `dashboard/`,
  `tests/`, `src/analysis/`, `src/visualization/`, `qgis_projects/` vuote).
  Rilevato bug di import in `download_data.py`
  (`CopernicusERA5Downloader._create_cds_client` annota `-> cdsapi.Client`
  senza importare `cdsapi` a livello di modulo) — documentato in
  `pages/data-sources.md`, non corretto (fuori scope di questo task).

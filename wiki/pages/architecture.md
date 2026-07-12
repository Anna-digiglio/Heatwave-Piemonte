# Architettura

**Sorgenti**: `docs/ARCHITECTURE.md`, struttura reale delle cartelle

## Flusso a livelli

```
Fonti dati esterne (Open-Meteo, Copernicus ERA5, ARPA, ISTAT, OSM)
        │
        ▼
  data/raw/              ← src/data_acquisition/download_data.py
        │
        ▼
  data/processed/        ← src/data_processing/clean_data.py
        │
        ▼
  PostgreSQL + PostGIS   ← src/database/load_to_db.py
        │
        ├──► sql/02_common_queries.sql  → analisi statistiche
        ├──► QGIS (qgis_projects/)      → mappe
        └──► Streamlit (dashboard/)     → dashboard interattiva
```

## Struttura cartelle (reale, luglio 2026)

```
Heatwave Piemonte/
├── CLAUDE.md                  # schema wiki (nuovo)
├── wiki/                      # wiki persistente (nuovo)
├── README.md, PROJECT_SUMMARY.md, SIMPLIFICATION_SUMMARY.md
├── config.yaml                # configurazione centrale (DB, fonti, soglie)
├── requirements.txt
├── docs/                      # documenti di pianificazione dettagliati
│   ├── ARCHITECTURE.md, DATABASE.md, ETL.md
│   ├── IMPLEMENTATION_GUIDE.md, ROADMAP.md
├── sql/
│   ├── 01_init_database.sql   # DDL completo, implementato
│   └── 02_common_queries.sql  # query di analisi, implementato
├── src/
│   ├── data_acquisition/download_data.py   # implementato
│   ├── data_processing/clean_data.py       # implementato
│   ├── database/load_to_db.py              # implementato (parziale, vedi sotto)
│   ├── utils/{config,database,logger}.py   # implementati
│   ├── analysis/          # VUOTA — pianificata, non implementata
│   └── visualization/     # VUOTA — pianificata, non implementata
├── dashboard/              # VUOTA — Streamlit pianificato, non implementato
├── tests/                  # VUOTA — nessun test scritto
├── qgis_projects/          # VUOTA — nessun progetto QGIS creato
└── data/raw/test_open_meteo_torino.csv   # unico dato reale presente (1 riga di test)
```

Per il dettaglio di cosa è realmente pronto vs pianificato, vedi
[Stato del Progetto](project-status.md).

## Pattern di codice usati

- **Singleton** per `Config` (`src/utils/config.py`): un'unica istanza globale
  `config` carica `config.yaml` una volta e la accede via dot-notation
  (`config.get('database.host')`).
- **Connection pooling** per il database (`src/utils/database.py`,
  `DatabaseManager`): engine SQLAlchemy con `pool_pre_ping`, `pool_recycle`,
  context manager `get_session()`.
  **Attenzione (trovato il 2026-07-12)**: `execute_query()` usa
  `engine.connect()` **senza `conn.commit()`** — corretto per le `SELECT`
  pure, ma se ci esegui una funzione con effetti collaterali (es.
  `SELECT * FROM identify_heatwaves();`), SQLAlchemy 2.0 fa rollback
  automatico delle modifiche non committate alla chiusura della
  connessione, silenziosamente (nessun errore, la funzione "riesce" ma non
  scrive nulla). `execute_update()` invece chiama `conn.commit()`
  esplicitamente ed è corretto. Per chiamare funzioni PL/pgSQL con side
  effect, usare `with db_manager.engine.begin() as conn: conn.execute(...)`
  (commit automatico a fine blocco se non ci sono eccezioni), non
  `execute_query()`.
- **Classi downloader dedicate** per fonte dati (`WeatherDataDownloader`,
  `CopernicusERA5Downloader`, `ArpaPiemonteDownloader`, `IstatGeodataDownloader`,
  `OpenStreetMapDownloader`) orchestrate da `ReferenceDataManager` in
  `download_data.py`.
- **Logging centralizzato** via `loguru` (`src/utils/logger.py`), configurato
  da `config.yaml` (livello, formato, file di log).

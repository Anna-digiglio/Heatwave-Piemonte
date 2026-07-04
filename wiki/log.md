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

- **2026-07-04** — FIX + DOWNLOAD REALE. Corretto il bug di import in
  `src/data_acquisition/download_data.py:184`
  (`_create_cds_client` ora annota `-> Optional["cdsapi.Client"]`, forward
  reference stringa invece di riferimento diretto valutato a tempo di
  definizione classe). Verificato che il modulo si importa correttamente.
  Eseguito un download reale via Open-Meteo (`--years 2000:2025 --sources
  open_meteo`, escluso 2026 perché l'API storica rifiuta date future):
  primo tentativo riuscito solo per 3/8 province (Torino, Alessandria, Asti)
  a causa di rate limit `429` non gestito dallo script, con il vero errore
  nascosto da un secondo bug scoperto in corso d'opera — `config.yaml`
  (`logging.format`) usa sintassi `%(asctime)s` da stdlib `logging` mentre
  `src/utils/logger.py` usa loguru (sintassi `{time}`), quindi ogni riga di
  log stampava la stringa di formato letterale invece del messaggio reale.
  Aggiunto retry con backoff esponenziale (rispetta `Retry-After`, max 5
  tentativi) in `WeatherDataDownloader.download_historical_data` e sleep
  tra regioni portato da 1s a 3s in `download_all_regions`. Ri-eseguito il
  download: tutte le 8 province scaricate con successo, 75.976 righe totali
  in `data/raw/temperature_data.csv`, nessun valore nullo. Pagine aggiornate:
  `data-sources.md` (bug cdsapi risolto, nuovo bug logging documentato, bug
  rate-limit documentato+risolto, dati reali scaricati), `etl-pipeline.md`
  (sezione Extract aggiornata con retry/backoff e run reale),
  `project-status.md` (righe 1-2 della roadmap segnate fatte, aggiunto punto
  minore sul fix di `logging.format` ancora da fare). Bug di logging
  **non corretto** (fuori scope: non bloccava il download, solo la
  leggibilità dei log) — resta in cima ai "prossimi passi" come voce minore.

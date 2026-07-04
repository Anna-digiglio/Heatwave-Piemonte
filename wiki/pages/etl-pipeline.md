# Pipeline ETL

**Sorgenti**: `src/data_acquisition/download_data.py`, `src/data_processing/clean_data.py`,
`src/database/load_to_db.py`, `docs/ETL.md`

## Extract — `download_data.py`

CLI: `python src/data_acquisition/download_data.py --years 2000:2026 --regions all --sources open_meteo,copernicus`

- `WeatherDataDownloader.download_all_regions()` itera le 8 province, chiama
  Open-Meteo per ciascuna con 3s di sleep tra una richiesta e l'altra,
  concatena in un unico DataFrame, salva in `data/raw/temperature_data.csv`.
- `download_historical_data()` gestisce i `429` (rate limit) con retry e
  backoff esponenziale (rispetta `Retry-After`, max 5 tentativi) — se anche
  dopo i retry una provincia fallisce, viene loggata e saltata (`continue`
  nel loop di `download_all_regions`), non persa silenziosamente come prima.
- Downloader analoghi per Copernicus ERA5, ARPA, ISTAT, OSM (vedi
  [Fonti Dati](data-sources.md) per stato/bug di ciascuno).
- **Eseguito realmente il 2026-07-04**: `data/raw/temperature_data.csv`
  popolato con 75.976 righe (8 province, 2000-2025, nessun nullo).

## Transform — `clean_data.py`

CLI: `python src/data_processing/clean_data.py --input data/raw/temperature_data.csv`

Pipeline dentro `DataCleaner.clean_data()`, in ordine:

1. `load_data` — legge il CSV, conta record iniziali
2. `remove_duplicates` — dedup su `(date, province)`
3. `handle_missing_values` — interpolazione lineare (max 2 gap) su
   `temp_mean` per provincia, `precipitation` NaN → 0, drop righe senza
   `temp_max`/`temp_min`
4. `validate_temperature` — flag `quality_flag=2` per valori fuori
   `[-50, 60]`, flag `quality_flag=1` per `temp_min > temp_max`
5. `detect_outliers` — IQR method (1.5×IQR) su `temp_max`, `temp_min`,
   `temp_mean`, flag `quality_flag=1`
6. `convert_dtypes` — cast a `float32`/`category`/`uint8` per efficienza
   memoria
7. `apply_quality_flags` — scarta righe con `quality_flag >= 2`
8. `generate_report` — log riassuntivo (record iniziali/finali, %completezza)

Output: `data/processed/temperature_clean.csv`.

**Nota di ordine**: `validate_temperature` gira *dopo* `handle_missing_values`
ma *prima* di `detect_outliers` — quindi un valore fuori range viene comunque
usato per calcolare i quantili IQR prima di essere eventualmente ri-flaggato.
Impatto minimo con pochi outlier, ma da tenere a mente se il dataset reale
mostra codici sentinella (es. `-999` per missing) prima della validazione.

## Load — `load_to_db.py`

CLI: `python src/database/load_to_db.py` → `DatabaseLoader`

- `initialize_schema()` — esegue l'intero `sql/01_init_database.sql` via
  `exec_driver_sql` (idempotente grazie a `IF NOT EXISTS`/`ON CONFLICT`)
- `verify_schema()` — controlla che `provinces`, `municipalities`,
  `temperature` esistano
- `insert_sample_province()` — inserisce **un solo record di prova**

**Gap importante**: `load_to_db.py` oggi **non carica** `data/processed/*.csv`
nella tabella `temperature`. Non esiste ancora l'orchestratore
`etl_pipeline.py` né i `models.py`/batch insert menzionati in
`PROJECT_SUMMARY.md`. Il "Load" reale si ferma a: crea schema + 8 province +
1 record di test. Questo è il prossimo pezzo mancante nella pipeline — vedi
[Stato del Progetto](project-status.md).

## Passaggi pianificati ma non ancora scritti

- Calcolo KPI giornalieri/annuali lato Python (oggi solo le viste
  materializzate SQL calcolano aggregati, vedi [Modello Dati](data-model.md))
- Batch insert ottimizzato per `temperature` (~1.7M righe attese)
- Trigger di `identify_heatwaves()` dopo il caricamento
- Refresh delle viste materializzate post-load

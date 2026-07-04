# Configurazione (`config.yaml`)

**Sorgente**: `config.yaml`, letta da `src/utils/config.py` (classe `Config`,
singleton, dot-notation via `config.get('a.b.c')`).

| Sezione | Contenuto | Note |
|---|---|---|
| `database` | host, port, database, user, password, schema, srid | `password` è in chiaro nel file di esempio — **da spostare su variabili d'ambiente** prima di pubblicare il repo (vedi `.env.example`) |
| `data_sources` | config per Open-Meteo, Copernicus, ARPA, ISTAT, OSM (url, enabled, variabili) | `enabled` per Copernicus è `true` di default ma richiede `CDS_KEY` in env — vedi [Fonti Dati](data-sources.md) |
| `paths` | raw/processed/external data, sql, output, logs | Path relativi, risolti rispetto alla root progetto in `Config.get_data_paths()` |
| `processing.temperature_thresholds` | `extreme_heat_1/2/3` = 30/35/40 °C | Soglie usate per KPI "giorni sopra X°C" e per `identify_heatwaves()` |
| `processing.heatwave_duration_days` | 3 | Minimo giorni consecutivi per ondata di calore — coerente col constraint `duration_days >= 3` in `heatwave_events` |
| `processing.date_range` | 2000–2026 | Copertura temporale target del progetto |
| `processing.regions` | le 8 province piemontesi | Usato come riferimento canonico dei nomi provincia |
| `logging` | livello, formato, file, console | Via `loguru`, log scritto in `logs/heatwave_piemonte.log` |
| `visualization` | stile, palette (`RdYlBu_r`), dpi, formato | Per grafici matplotlib/plotly quando verranno implementati |
| `dashboard` | porta 8501, titolo, tema, max upload | Per Streamlit quando verrà implementato |

## Convenzione di risoluzione del path

`Config._load_config()` cerca `config.yaml` prima nella root del progetto,
poi (fallback) in `src/config.yaml`. Nel repo attuale esiste solo la copia in
root.

## `Config.get_database_url()`

Costruisce l'URL SQLAlchemy `postgresql://user:password@host:port/database`
(senza password se non impostata). Usato da `src/utils/database.py` per
creare l'engine.

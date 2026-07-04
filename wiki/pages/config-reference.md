# Configurazione (`config.yaml`)

**Sorgente**: `config.yaml`, letta da `src/utils/config.py` (classe `Config`,
singleton, dot-notation via `config.get('a.b.c')`).

| Sezione | Contenuto | Note |
|---|---|---|
| `database` | host, port, database, user, password, schema, srid | `password` in `config.yaml` è solo un placeholder (`your_password`) — le variabili d'ambiente (`.env`, non tracciato in git) hanno la precedenza, vedi sotto |
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

**Fixato il 2026-07-04**: `config.py` non chiamava mai `load_dotenv()`
nonostante `python-dotenv` fosse già in `requirements.txt` e `.env.example`
presente — un `.env` locale non aveva quindi alcun effetto. Inoltre
`get_database_url()` leggeva `database.password` da `config.yaml` *prima*
di considerare la variabile d'ambiente `DB_PASSWORD`, quindi anche
impostando l'env var il placeholder in YAML vinceva comunque sempre (dato
che `config.yaml` **è tracciato in git**, a differenza di `.env`). Ora:
`load_dotenv()` viene chiamato all'import del modulo, e `DB_HOST`/`DB_PORT`/
`DB_USER`/`DB_PASSWORD`/`DB_NAME` da variabili d'ambiente hanno precedenza
sui valori in `config.yaml`, che restano solo un fallback/placeholder per la
struttura del file.

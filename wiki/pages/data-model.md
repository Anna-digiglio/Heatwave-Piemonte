# Modello dati (PostgreSQL + PostGIS)

**Sorgente**: `sql/01_init_database.sql` (unica fonte di verità — `docs/DATABASE.md`
può divergere leggermente, in caso di conflitto fidati dello script SQL).

## Tabelle

### `provinces`
- PK `province_id SERIAL`
- `name UNIQUE`, `istat_code`, `geometry GEOMETRY(POINT, 4326)` (baricentro),
  `area_km2`, `population`
- Indici: nome, GIST su geometria, istat_code
- 8 record seed (le province piemontesi) inseriti direttamente nello script DDL

### `municipalities`
- PK `municipality_id SERIAL`, FK `province_id → provinces` (`ON DELETE RESTRICT`)
- `istat_code UNIQUE`, `geometry GEOMETRY(POLYGON, 4326)`, `elevation_m`,
  `population`, `area_km2`
- Nessun dato seed: da popolare via download ISTAT (vedi [Fonti Dati](data-sources.md))

### `temperature` — tabella principale, serie storica giornaliera
- PK `temperature_id BIGSERIAL`
- FK `municipality_id`, `province_id`
- `date`, `temp_mean`, `temp_max NOT NULL`, `temp_min NOT NULL`,
  `precipitation`, `humidity`, `data_source`, `quality_flag` (0=good,
  1=suspect, 2=bad)
- Constraint `valid_temperature`: `temp_min <= temp_mean <= temp_max` e
  range fisico `-50..60 °C`
- Indici: `date`, `(municipality_id, date)`, `(province_id, date)`,
  parziale su `temp_max > 30`, `data_source`

### `heatwave_events` — ondate di calore identificate
- PK `heatwave_id BIGSERIAL`, FK `municipality_id`, `province_id`
- `start_date`, `end_date`, `duration_days`, `max_temp`, `mean_temp`,
  `intensity_index` (= `(max_temp - threshold) * duration`),
  `heat_threshold`, `threshold_type` (`'GT_30'|'GT_35'|'GT_40'`)
- Constraint: `end_date >= start_date AND duration_days >= 3` — coerente con
  la definizione di ondata di calore usata nel progetto (≥3 giorni
  consecutivi sopra soglia, vedi [Concetti](concepts.md))
- Popolata dalla funzione `identify_heatwaves()` (vedi sotto), non da uno
  script Python

### `kpi` — aggregati annuali/mensili a 3 livelli
- PK `kpi_id BIGSERIAL`, FK opzionali `municipality_id`/`province_id`
- `level` (`'municipal'|'provincial'|'regional'`), `year`, `month` (0 = annuale)
- `temp_mean_annual`, `temp_max_annual`, `temp_min_annual`,
  `days_gt_30c/35c/40c`, `heatwave_count`, `heatwave_avg_duration`,
  `annual_anomaly` (vs baseline 1961-1990), `version`
- Constraint `valid_kpi`: garantisce coerenza tra `level` e quali FK sono
  valorizzate (mutuamente esclusive)

### `metadata` — chiave/valore di servizio
- PK `key`, `value`, `data_type`, `last_updated`, `notes`
- Righe seed: `database_version`, `last_etl_run`, `data_start_year` (2000),
  `data_end_year` (2026), `data_completeness`, `created_at`

## Viste materializzate

- `kpi_annual_by_municipality` — aggregazione `temperature` per comune/anno
  (media, max, min, giorni sopra soglia, stddev)
- `kpi_annual_by_province` — stessa aggregazione a livello provinciale
  (`municipality_id` forzato a `NULL`)

Nota: queste viste **duplicano concettualmente** la tabella `kpi`. La tabella
`kpi` sembra pensata per KPI calcolati/persistiti dalla pipeline Python,
mentre le viste materializzate sono la via rapida via SQL puro. Da chiarire
quale sia la fonte usata dalla dashboard quando questa verrà costruita — vedi
[Dashboard](dashboard.md).

## Funzioni

### `identify_heatwaves(p_heat_threshold FLOAT = 35.0, p_min_duration SMALLINT = 3)`
Funzione PL/pgSQL che scandisce `temperature` ordinata per comune/data,
individua sequenze di giorni consecutivi con `temp_max > p_heat_threshold` di
lunghezza ≥ `p_min_duration`, e inserisce i risultati in `heatwave_events`.
Unico punto del progetto dove la logica di rilevamento ondate è già scritta
(lato SQL, non Python — `src/analysis/heatwave_detection.py` menzionato nei
docs di pianificazione non esiste ancora).

## Diagramma relazionale (sintetico)

```
provinces 1───* municipalities 1───* temperature
    │                   │
    │                   └──────* heatwave_events
    │
    └── (province_id nullable FK) ──* kpi *── (municipality_id nullable FK)
```

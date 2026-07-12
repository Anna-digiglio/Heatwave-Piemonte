# Modello dati (PostgreSQL + PostGIS)

**Sorgente**: `sql/01_init_database.sql` (unica fonte di verità — `docs/DATABASE.md`
può divergere leggermente, in caso di conflitto fidati dello script SQL).

## Tabelle

### `provinces`
- PK `province_id SERIAL`
- `name UNIQUE`, `istat_code`, `geometry GEOMETRY(POINT, 4326)` (baricentro),
  `area_km2`, `population`
- Indici: nome, GIST su geometria, istat_code
- 8 record seed (le province piemontesi) inseriti direttamente nello script DDL.
  **Fixato il 2026-07-04**: `istat_code` di Alessandria era `'001'`,
  duplicato di Torino — corretto in `'006'` (verificato incrociando lo
  shapefile ufficiale ISTAT, che riporta `COD_PROV=6` per i comuni
  alessandrini).

### `municipalities`
- PK `municipality_id SERIAL`, FK `province_id → provinces` (`ON DELETE RESTRICT`)
- `istat_code UNIQUE`, `geometry GEOMETRY(MULTIPOLYGON, 4326)`, `elevation_m`,
  `population`, `area_km2`
- **Popolata il 2026-07-04** con dati reali ISTAT: 1180 comuni piemontesi
  (confini amministrativi al 01/01/2026, shapefile generalizzato). Vedi
  [Fonti Dati](data-sources.md) per la provenienza e [ETL](etl-pipeline.md)
  per il flusso di caricamento. Colonna `geometry` cambiata da `POLYGON` a
  `MULTIPOLYGON` (era il tipo originario nello script DDL): 74 dei 1180
  comuni hanno confini multi-parte nei dati ISTAT reali (es. exclavi), che
  un `POLYGON` semplice non può rappresentare.
- `population` ed `elevation_m` sono `NULL` per tutti i comuni: lo
  shapefile ISTAT dei confini amministrativi non include questi dati
  (serve un dataset demografico ISTAT separato, non ancora integrato).

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
- **Popolata il 2026-07-04**: 75.976 righe reali (8 comuni capoluogo di
  provincia, 2000-2025). Vedi [ETL](etl-pipeline.md) per la nota sulla
  granularità (solo capoluoghi, non tutti i 1180 comuni).

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
- **Eseguita per la prima volta su dati reali il 2026-07-12**: 51 ondate
  identificate (soglia 35°C, durata minima 3 giorni) su 8 comuni
  capoluogo, 2000-2025 — inclusa la storica ondata dell'agosto 2003.
  Verificate contro un conteggio indipendente via window function SQL
  (`ROW_NUMBER()`-based gap detection): coincidenza esatta, 51/51.

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
- `value` **non è più `NOT NULL`** (fixato il 2026-07-04): il seed inserisce
  `NULL` per `last_etl_run` (nessun ETL ancora eseguito), che violava il
  vincolo originario

## Viste materializzate

- `kpi_annual_by_municipality` — aggregazione `temperature` per comune/anno
  (media, max, min, giorni sopra soglia, stddev)
- `kpi_annual_by_province` — stessa aggregazione a livello provinciale
  (`municipality_id` forzato a `NULL`)
- **Rinfrescate il 2026-07-12** con dati reali (`REFRESH MATERIALIZED VIEW`):
  208 righe ciascuna (8 comuni/province × 26 anni, 2000-2025). Erano vuote
  da quando create (calcolate quando `temperature` non aveva ancora dati) —
  **non si aggiornano da sole quando la tabella sottostante cambia**, va
  rifatto il refresh esplicitamente dopo ogni nuovo caricamento.

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

**Bug risolti il 2026-07-12, trovati eseguendo la funzione per la prima
volta su dati reali** (senza questi fix avrebbe inserito 0 righe, o righe
attribuite al comune sbagliato):
1. Quando la sequenza si interrompeva per **cambio comune** (non solo per
   un buco di date), l'`INSERT` usava `rec.municipality_id`/`rec.province_id`
   — cioè i valori del comune **nuovo**, non di quello a cui l'ondata appena
   conclusa apparteneva davvero. Fix: variabili dedicate
   (`v_municipality_id`/`v_province_id`) aggiornate solo quando si apre una
   nuova sequenza, usate nell'`INSERT` invece dei campi di `rec`.
2. **Nessun "flush finale"**: se l'ultimo comune elaborato (nell'`ORDER BY
   municipality_id, date`) terminava la serie storica *durante* un'ondata
   ancora attiva, quell'ultima ondata non veniva mai salvata (il loop
   finisce senza controllare la sequenza in corso). Fix: controllo
   esplicito dopo il `FOR ... LOOP`.
3. **Ambiguità di nomi**: le due nuove variabili si chiamavano quasi come le
   colonne selezionate (`municipality_id`, `province_id`), causando
   `ERRORE: riferimento alla colonna ambiguo`. Fix: query interna con alias
   di tabella esplicito (`FROM temperature t`, colonne `t.municipality_id`
   ecc.).
4. **Side effect silenziosamente annullato**: la prima esecuzione "riuscita"
   (nessun errore) aveva inserito 0 righe perché invocata via
   `db_manager.execute_query()`, che non fa `commit()` — vedi
   [Architettura](architecture.md) per il dettaglio. Verificato con un
   conteggio indipendente via SQL (window function `ROW_NUMBER()` per
   individuare gap di date): 51 ondate reali attese, 51 trovate dopo il fix.

## Diagramma relazionale (sintetico)

```
provinces 1───* municipalities 1───* temperature
    │                   │
    │                   └──────* heatwave_events
    │
    └── (province_id nullable FK) ──* kpi *── (municipality_id nullable FK)
```

# ETL PIPELINE - HEATWAVE PIEMONTE

## 📋 Visione d'insieme

La **Pipeline ETL** è il cuore del progetto, responsabile di:
1. **E**xtract: Acquisire dati da fonti esterne
2. **T**ransform: Pulire, validare, elaborare
3. **L**oad: Caricare in database PostgreSQL

```
EXTRACT → TRANSFORM → LOAD → ANALYZE
  ↓         ↓          ↓        ↓
Source   Cleaning   Database  Insights
Data     & Prep      Store    & KPI
```

---

## 🔄 Flusso ETL Dettagliato

### 1️⃣ EXTRACT Phase

#### Dati Acquisiti

Nota: Nella modalità "approccio intermedio" le sorgenti predefinite sono **Open-Meteo** e **Copernicus ERA5**; ARPA/ISTAT/OSM sono opzionali e scaricabili se necessario.

| Fonte | Tipo | Volume | Frequenza |
|-------|------|--------|-----------|
| **Open-Meteo API** | JSON | 1.7M record | Storico 2000-2026 |
| **Copernicus ERA5** | NetCDF | Multi-GB (dati grezzi) | Storico 2000-2026 |
| **ARPA Piemonte** | CSV / metadata | Stazioni locali | Aggiornamento quotidiano / mensile (opzionale) |
| **ISTAT** | GeoJSON / Shapefile | Confini amministrativi | Dati storici (opzionale) |
| **OpenStreetMap** | GeoJSON | Confini | Geo-boundaries dinamici (opzionale) |
| **Copernicus ERA5** | NetCDF | Multi-GB (dati grezzi) | Storico 2000-2026 |
| **ARPA Piemonte** | CSV / metadata | Stazioni locali | Aggiornamento quotidiano / mensile |
| **ISTAT** | GeoJSON / Shapefile | Confini amministrativi | Dati storici |
| **OpenStreetMap** | GeoJSON | Confini | Geo-boundaries dinamici |

#### Script: `download_data.py`

```python
WeatherDataDownloader
├── download_historical_data(region, start_date, end_date)
│   ├── Query Open-Meteo API
│   ├── Parse JSON response
│   └── Return DataFrame
├── download_all_regions(start_date, end_date)
│   ├── Loop su 8 province
│   ├── Concatenate results
│   └── Save CSV
└── save_data(df, filename)
    └── CSV output: data/raw/

GeospatialDataDownloader
├── download_piemonte_boundaries()
├── create_dummy_provinces()
└── save GeoJSON/Shapefile
```

**Output**: `data/raw/temperature_*.csv` (~2-3 GB)

---

### 2️⃣ TRANSFORM Phase

#### Data Cleaning Pipeline

```
Raw Data (input)
    ↓
[1] Remove Duplicates
    ├── Subset: (date, province, municipality)
    └── Keep: first occurrence
    ↓
[2] Handle Missing Values
    ├── Temperature: Linear interpolation (max gap: 2 days)
    ├── Precipitation: Fill with 0
    └── Drop if critical cols missing
    ↓
[3] Validate Temperature
    ├── Range check: -50°C to +60°C
    ├── Logic check: temp_min ≤ temp_mean ≤ temp_max
    └── Flag suspect records
    ↓
[4] Detect Outliers
    ├── IQR method (Q1-1.5*IQR, Q3+1.5*IQR)
    ├── Flag outliers
    └── Keep for inspection
    ↓
[5] Feature Engineering
    ├── Calculate KPI daily
    ├── Flag extreme days
    ├── Identify heatwaves
    └── Add anomaly column
    ↓
[6] Type Conversion
    ├── Date → datetime64
    ├── Temp → float32
    ├── Province → category
    └── Quality flag → uint8
    ↓
[7] Quality Filtering
    ├── Remove quality_flag = 2 (bad)
    ├── Keep quality_flag = 0,1 (ok,suspect)
    └── Log statistics
    ↓
Cleaned Data (output)
```

#### Script: `clean_data.py`

```python
DataCleaner
├── remove_duplicates(df) → int records_removed
├── handle_missing_values(df) → df cleaned
├── validate_temperature(df) → df flagged
├── detect_outliers(df) → df flagged
├── convert_dtypes(df) → df typed
├── apply_quality_flags(df) → df filtered
└── clean_data(input_path) → DataFrame cleaned
```

#### Quality Report

```
==============================================================================
REPORT CLEANING DATI
==============================================================================
Record iniziali:               1,723,428
Duplicati rimossi:               1,245
Temperature non valide:            567
Outlier rilevati:              23,456
Record finali:                1,698,160
Completezza dati:                98.5%
==============================================================================
```

**Output**: `data/processed/temperature_clean.csv` (~1.5 GB)

---

### 3️⃣ LOAD Phase

#### Database Loading Strategy

**Tabelle Load Order**:

```
1. PROVINCES
   └─ 8 records (reference data)
   
2. MUNICIPALITIES
   └─ ~170 records (reference data)
   
3. TEMPERATURE (MAIN - 1.7M records)
   ├── Batch insert 10K records/batch
   ├── Chunk processing
   └── Progress tracking
   
4. HEATWAVE_EVENTS (DERIVED)
   ├── Identified from TEMPERATURE
   ├── Function: identify_heatwaves()
   └── ~1000 events
   
5. KPI (AGGREGATED)
   ├── Computed from TEMPERATURE
   └── 8 province × 27 years = 216 records
```

#### Script: `etl_pipeline.py` (To implement)

```python
class ETLOrchestrator
├── validate_input_files() → bool
├── load_provinces() → int rows_loaded
├── load_municipalities() → int rows_loaded
├── load_temperature(df_clean)
│   ├── Split into chunks (10K rows)
│   ├── For each chunk:
│   │   ├── Map to MUNICIPALITIES
│   │   ├── Map to PROVINCES
│   │   ├── Insert batch
│   │   └── Log progress
│   └── Return: total_loaded
├── identify_and_load_heatwaves() → int events_loaded
├── compute_and_load_kpi() → int kpi_records
└── full_etl_pipeline()
    ├── Extract → Clean → Validate
    ├── Load → Verify → Index
    ├── Compute → Refresh Views
    └── Log summary
```

#### Loading Performance

| Operazione | Tempo | Note |
|-----------|-------|------|
| Province insert | <1 sec | 8 records |
| Municipalities insert | ~5 sec | 170 records |
| Temperature insert | 20-30 min | 1.7M records, batch optimized |
| Index creation | 5-10 min | 25+ indici |
| Heatwave detection | 10-15 min | Function based |
| KPI computation | 5 min | Aggregation queries |
| **TOTAL** | **~60 min** | End-to-end |

#### Connection Pooling

```python
# SQLAlchemy config
pool_size = 10          # Min concurrent connections
max_overflow = 20       # Additional connections allowed
pool_pre_ping = True    # Test connection before use
pool_recycle = 3600     # Recycle connection after 1hr
```

---

### 4️⃣ ANALYZE Phase (Post-Load)

#### KPI Computation

**KPI Calcolati** (stored in `kpi` table):

```sql
FOR EACH (municipality, year):
  ├── temp_mean_annual: AVG(temp_mean)
  ├── temp_max_annual: MAX(temp_max)
  ├── temp_min_annual: MIN(temp_min)
  ├── days_gt_30c: COUNT WHERE temp_max > 30
  ├── days_gt_35c: COUNT WHERE temp_max > 35
  ├── days_gt_40c: COUNT WHERE temp_max > 40
  ├── heatwave_count: COUNT heatwave events
  ├── heatwave_avg_duration: AVG(duration_days)
  └── annual_anomaly: diff from 1961-1990 baseline

FOR EACH (province, year):
  └── Same aggregations at province level
  
FOR EACH (region, year):
  └── Same aggregations at regional level
```

#### Materialized Views

```sql
-- Refreshed after each ETL run
REFRESH MATERIALIZED VIEW kpi_annual_by_municipality;
REFRESH MATERIALIZED VIEW kpi_annual_by_province;
```

---

## ⚡ Performance Optimization

### Indici Critici

```sql
-- Temperature table (most queries hit this)
idx_temperature_date              -- Date range queries
idx_temperature_municipality_date  -- By location + time
idx_temperature_province_date     -- Province aggregations
idx_temperature_temp_max (partial) -- Only temp > 30

-- Heatwave events
idx_heatwave_dates
idx_heatwave_municipality
idx_heatwave_intensity

-- KPI lookup
idx_kpi_year
idx_kpi_municipality_year
idx_kpi_province_year
```

### Query Optimization

```sql
-- ❌ Slow (full table scan)
SELECT * FROM temperature WHERE temp_max > 35;

-- ✅ Fast (indexed partial search)
SELECT * FROM temperature WHERE temp_max > 35 AND date >= '2020-01-01';

-- ❌ Slow (computation in WHERE)
SELECT * FROM temperature WHERE YEAR(date) = 2020;

-- ✅ Fast (direct date range)
SELECT * FROM temperature WHERE date >= '2020-01-01' AND date < '2021-01-01';
```

---

## 📊 Data Quality Checks

### Pre-Load Validation

```python
✓ Schema validation (columns, dtypes)
✓ Range checks (temp -50...+60°C)
✓ Logical checks (temp_min ≤ temp_mean ≤ temp_max)
✓ Completeness checks (% missing values)
✓ Uniqueness (date + municipality + temperature unique)
✓ Duplicate detection (exact rows)
✓ Outlier identification (IQR method)
✓ Data type validation (dates, floats)
```

### Post-Load Verification

```sql
-- Row counts
SELECT COUNT(*) FROM temperature;  -- Expected: 1.7M

-- Date coverage
SELECT MIN(date), MAX(date) FROM temperature;  -- 2000-2026

-- Temperature ranges
SELECT MIN(temp_min), MAX(temp_max) FROM temperature;

-- Missing values
SELECT COUNT(*) FROM temperature WHERE temp_max IS NULL;  -- 0

-- Quality flags distribution
SELECT quality_flag, COUNT(*) FROM temperature GROUP BY quality_flag;

-- Heatwave events count
SELECT COUNT(*) FROM heatwave_events;  -- Expected: 1000-2000

-- KPI completeness
SELECT COUNT(*) FROM kpi;  -- Expected: 216+ records
```

---

## 🔄 Incremental ETL (Future)

Per aggiornamenti dati giornalieri:

```python
class IncrementalETL(ETLOrchestrator)
├── get_last_loaded_date() → DATE
├── download_new_data(last_date, today)
├── transform_new_data(df)
├── upsert_temperature(df)
│   ├── Check if (date, municipality) exists
│   ├── UPDATE if exists
│   ├── INSERT if new
│   └── Keep audit trail
├── refresh_kpi_for_new_dates()
└── log_etl_run(rows_loaded, errors, duration)
```

---

## 🚨 Error Handling

```python
class ETLException(Exception)
├── DataValidationError
├── LoadingError
├── DatabaseError
└── APIError

# Recovery strategy
try:
    etl_pipeline.run()
except ETLException as e:
    logger.error(f"ETL failed: {e}")
    db_manager.rollback_to_checkpoint()
    notify_admin(e)
    # Manual intervention required
```

---

## 📈 Monitoraggio ETL

### Logging Structure

```
[2026-05-30 14:30:15] INFO | extract | Downloaded 1.7M records from Open-Meteo
[2026-05-30 14:32:45] INFO | transform | Removed 1,245 duplicates
[2026-05-30 14:33:12] INFO | transform | Handled 567 missing values
[2026-05-30 14:45:30] INFO | load | Inserted 1.7M temperature records
[2026-05-30 15:00:00] INFO | analyze | Computed 216 KPI records
[2026-05-30 15:02:30] INFO | summary | ETL completed in 32 minutes
```

### Dashboard di Monitoraggio

```
┌─ ETL Status Dashboard ─────────────────┐
│                                        │
│ Last Run: 2026-05-30 15:02:30         │
│ Duration: 32 minutes                  │
│ Status: ✓ SUCCESS                     │
│                                        │
│ Records Loaded: 1,698,160             │
│ Quality Score: 98.5%                  │
│ Errors: 0                             │
│                                        │
│ Next Run: 2026-05-31 01:00 (Scheduled)│
└────────────────────────────────────────┘
```

---

## 📝 Checklist di Implementazione

- [ ] `download_data.py` - Acquisizione
- [ ] `clean_data.py` - Validazione e pulizia
- [ ] `etl_pipeline.py` - Orchestrazione
- [ ] `01_init_database.sql` - Schema
- [ ] `02_common_queries.sql` - Query utili
- [ ] Error handling e retry logic
- [ ] Logging strutturato
- [ ] Performance benchmarks
- [ ] Data quality report
- [ ] Documentation completa

---

**Versione**: 1.0  
**Ultimo aggiornamento**: Maggio 2026  
**Responsabile**: Data Engineering Team

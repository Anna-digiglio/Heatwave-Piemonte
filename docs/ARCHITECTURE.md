# ARCHITETTURA DEL PROGETTO HEATWAVE PIEMONTE

## 📐 Diagramma dell'Architettura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          HEATWAVE PIEMONTE ARCHITECTURE                     │
└─────────────────────────────────────────────────────────────────────────────┘

                            ┌─────────────────────┐
                            │   DATA SOURCES      │
                            ├─────────────────────┤
                            │ • ARPA Piemonte     │
                            │ • Open-Meteo API    │
                            │ • Copernicus ERA5   │
                            │ • ISTAT Geografi    │
                            └──────────┬──────────┘
                                       │
                            ┌──────────▼──────────┐
                            │  DATA ACQUISITION   │
                            │  (Python Scripts)   │
                            ├─────────────────────┤
                            │ • download_data.py  │
                            │ • parse_csv.py      │
                            │ • api_client.py     │
                            └──────────┬──────────┘
                                       │
                    ┌──────────────────▼──────────────────┐
                    │        RAW DATA STORAGE             │
                    ├─────────────────────────────────────┤
                    │  data/raw/                          │
                    │  ├── temperature_*.csv              │
                    │  ├── precipitation_*.csv            │
                    │  ├── metadata_provinces.geojson     │
                    │  └── municipalities_*.shp           │
                    └──────────────┬──────────────────────┘
                                   │
                        ┌──────────▼──────────┐
                        │  DATA PROCESSING    │
                        ├─────────────────────┤
                        │ • clean_data.py     │
                        │ • validate_data.py  │
                        │ • transform_data.py │
                        └──────────┬──────────┘
                                   │
                    ┌──────────────▼──────────────────┐
                    │     PROCESSED DATA STORAGE      │
                    ├─────────────────────────────────┤
                    │  data/processed/                │
                    │  ├── temperature_clean.csv      │
                    │  ├── heatwave_events.csv        │
                    │  └── kpi_summary.csv            │
                    └──────────┬──────────────────────┘
                               │
                ┌──────────────▼──────────────────┐
                │      PostgreSQL + PostGIS       │
                ├─────────────────────────────────┤
                │ SCHEMA: heatwave_piemonte      │
                │                                 │
                │ TABLES:                         │
                │ • temperature (timeseries)      │
                │ • heatwave_events               │
                │ • provinces (geometry)          │
                │ • municipalities (geometry)     │
                │ • kpi (aggregated)              │
                │ • metadata                      │
                └──────────┬──────────────────────┘
                           │
        ┌──────────────────┼──────────────────────┐
        │                  │                      │
        ▼                  ▼                      ▼
    ┌─────────┐        ┌──────────┐         ┌──────────┐
    │ ANALYSIS│        │ QGIS     │         │STREAMLIT │
    │ Scripts │        │ Projects │         │Dashboard │
    │         │        │          │         │          │
    │ • stat_ │        │ • temp_  │         │ • home.py│
    │   analysis.py    │   heatmap.qgz       │ • analysis
    │ • spatial_       │ • hotspot │         │   _page.py
    │   analysis.py    │ • evolution        │ • maps_page
    │ • trend_         │   .qgz             │   .py
    │   analysis.py    │                    │ • kpi_page
    │                  │                    │   .py
    └─────────┘        └──────────┘         └──────────┘
        │                  │                     │
        └──────────────────┼─────────────────────┘
                           │
                    ┌──────▼───────┐
                    │   OUTPUTS    │
                    ├──────────────┤
                    │ • Reports    │
                    │ • Maps       │
                    │ • Charts     │
                    │ • Dashboard  │
                    └──────────────┘
```

## 🏗️ Architettura Componentale

### 1. **Data Acquisition Layer**

**Responsabilità**: Raccogliere dati da molteplici fonti esterne

**Componenti**:
- `download_data.py`: Orchestratore principale per download multi-sorgente
- `utils/config.py`: Lettura e gestione configurazione centralizzata
- `utils/logger.py`: Logging centralizzato per download e processi
- `src/data_processing/clean_data.py`: Pulizia e validazione dei dati
- `src/database/load_to_db.py`: Caricamento dati su PostgreSQL/PostGIS

**Output**: CSV, JSON, NetCDF in `data/raw/`

**Tecnologie**:
- requests, aiohttp
- beautifulsoup4
- pandas I/O
- cdsapi (Copernicus)

---

### 2. **Data Processing Layer**

**Responsabilità**: Pulizia, validazione e trasformazione dati

**Componenti**:
- `clean_data.py`: Rimozione duplicati, outlier, valori mancanti
- `validate_data.py`: Schema validation, range checks
- `transform_data.py`: Aggregazioni, calcolo KPI
- `geospatial_processing.py`: Join geografici, spatial joins

**Processi**:
```
Raw Data → Cleaning → Validation → Transformation → Processed Data
```

**Tecnologie**:
- pandas, numpy
- geopandas
- sqlalchemy

---

### 3. **Database Layer**

**Stack**: PostgreSQL 14+ + PostGIS 3.0+

**Schema Relazionale**:

```sql
-- Core tables
├── temperature (PK: id, FK: province_id, municipality_id)
│   └── Timeseries dati giornalieri
├── heatwave_events (PK: id, FK: municipality_id)
│   └── Eventi estremi identificati
├── provinces (PK: province_id, geometry)
│   └── Dati geografici province
├── municipalities (PK: municipality_id, FK: province_id, geometry)
│   └── Geometrie comuni piemontesi
├── kpi (PK: id, FK: municipality_id, province_id)
│   └── KPI aggregati
└── metadata (PK: key)
    └── Informazioni datasource e versioni
```

**Indici Ottimizzati**:
```sql
-- Performance
CREATE INDEX idx_temperature_date ON temperature(date);
CREATE INDEX idx_temperature_province ON temperature(province_id);
CREATE INDEX idx_geometry_provinces ON provinces USING GIST(geometry);
```

**Partitioning**:
```sql
-- Tabella temperatura partizionata per anno
PARTITION BY RANGE (YEAR(date))
```

---

### 4. **Analysis Layer**

**Responsabilità**: Eseguire analisi statistiche e geospaziali

**Componenti**:

| Script | Obiettivo |
|--------|-----------|
| `statistical_analysis.py` | Trend, distribuzioni, correlazioni |
| `spatial_analysis.py` | Autocorrelazione spaziale (Moran's I) |
| `temporal_analysis.py` | Seasonality, moving averages |
| `heatwave_detection.py` | Identificazione ondate di calore |
| `vulnerability_assessment.py` | Indici di vulnerabilità |

**Algoritmi**:
- Mann-Kendall trend test
- Linear regression con confidence intervals
- K-means clustering geografico
- Moran's I autocorrelation test
- STL decomposition (Seasonal-Trend decomposition)

---

### 5. **Visualization Layer**

#### 5a. **QGIS (Analisi Geospaziale)**
Progetti preconfigurati:
- `temperature_heatmap.qgz` - Mappa calore province
- `hotspot_analysis.qgz` - Hotspot climatici
- `evolution_animation.qgz` - Animazione temporale

#### 5b. **Streamlit Dashboard**
Sezioni:
- **Home**: Overview e KPI principali
- **Analisi Temporale**: Trend 2000-2026
- **Analisi Provinciale**: Confronti territoriali
- **Mappe Interattive**: Folium + Plotly
- **Report Scaricabile**: Export PDF/Excel

---

### 6. **Utility Layer**

**Moduli Helper**:
- `config.py` - Gestione configurazione YAML
- `logger.py` - Logging centralizzato
- `database.py` - Connection pooling
- `validators.py` - Data validation schema
- `constants.py` - Costanti e magic numbers

---

## 🔄 Pipeline ETL Dettagliato

```
EXTRACT
├── ARPA Piemonte API/Scraping
├── Open-Meteo Archive API
├── Copernicus ERA5 NetCDF
└── Geospatial data (ISTAT)
         │
         ▼
TRANSFORM
├── Data Cleaning
│   ├── Handle missing values
│   ├── Remove duplicates
│   └── Outlier detection (IQR method)
├── Data Validation
│   ├── Schema validation
│   ├── Range checking (e.g., temp -50:+60°C)
│   └── Geospatial validation
├── Feature Engineering
│   ├── Heatwave detection (consecutive days)
│   ├── Rolling averages
│   ├── Anomaly calculation
│   └── KPI computation
└── Aggregation
    ├── Daily → Weekly
    ├── Daily → Monthly
    └── Daily → Yearly
         │
         ▼
LOAD
├── PostgreSQL INSERT
├── Spatial index creation
├── Materialized views refresh
└── Backup

TIME: ~2 hours for full ETL (2000-2026)
```

---

## 📊 Modello Relazionale Semplificato

```
┌──────────────────────┐
│   PROVINCES          │
├──────────────────────┤
│ PK province_id       │
│    name (8 prov)     │
│    geometry          │
│    area_km2          │
│    center_lat/lon    │
└──────────────────────┘
         │ 1
         │
         │ N
┌──────────────────────────────┐
│   MUNICIPALITIES             │
├──────────────────────────────┤
│ PK municipality_id           │
│ FK province_id               │
│    name                      │
│    istat_code                │
│    geometry (point/polygon)  │
│    elevation_m               │
└──────────────────────────────┘
         │ 1
         │
         │ N
┌──────────────────────────────┐
│   TEMPERATURE (Timeseries)   │
├──────────────────────────────┤
│ PK id                        │
│ FK municipality_id           │
│ FK province_id               │
│    date (indexed)            │
│    temp_mean (°C)            │
│    temp_max (°C)             │
│    temp_min (°C)             │
│    precipitation (mm)        │
│    data_source               │
└──────────────────────────────┘
         │ 1
         │
         │ N
┌──────────────────────────────┐
│   HEATWAVE_EVENTS            │
├──────────────────────────────┤
│ PK heatwave_id               │
│ FK municipality_id           │
│    start_date                │
│    end_date                  │
│    duration_days             │
│    max_temp                  │
│    intensity_index           │
│    identified_at             │
└──────────────────────────────┘

┌──────────────────────────────┐
│   KPI (Aggregated)           │
├──────────────────────────────┤
│ PK kpi_id                    │
│ FK municipality_id (nullable)│
│ FK province_id (nullable)    │
│    year                      │
│    month                     │
│    temp_mean_annual          │
│    temp_max_annual           │
│    days_gt_30c               │
│    days_gt_35c               │
│    days_gt_40c               │
│    heatwave_count            │
│    computed_at               │
└──────────────────────────────┘
```

---

## 🔐 Sicurezza & Best Practices

### Database Security
```yaml
- Role-based access control (RBAC)
- Connection SSL/TLS
- Credential management via .env
- Query parameterization (SQLAlchemy ORM)
- Audit logging
```

### Code Quality
```yaml
- Type hints (mypy compliance)
- Docstring (Google style)
- Logging (structlog/loguru)
- Error handling (try-except)
- Configuration centralization
```

### Data Validation
```yaml
- Schema validation (pandas)
- Range checks per colonna
- Geospatial validity checks
- Duplicate detection
- Completeness checks
```

---

## 🚀 Deployment Architecture

```
Development → Testing → Staging → Production

Local Setup
├── Python venv
├── PostgreSQL local
└── Data files (1GB)
        ↓
GitHub Repository
├── Source code
├── SQL scripts
├── Config files
└── Documentation
        ↓
Docker Container (Optional)
├── Python environment
├── Database init
└── Dependencies pre-installed
        ↓
Cloud Deployment
├── AWS RDS (PostgreSQL)
├── S3 (Data storage)
├── EC2 (Dashboard server)
└── GitHub Pages (Documentation)
```

---

## 📈 Performance Considerations

| Componente | Metrica | Target |
|-----------|---------|--------|
| Data Download | Tempo | <30 min |
| Data Processing | Tempo | <1 hour |
| DB Load | Throughput | 10k+ rows/sec |
| Query Response | Latency | <2 sec |
| Dashboard Load | Time | <3 sec |

---

## 🔄 Versioning Strategy

```
Branches:
├── main (production-ready)
├── develop (integration)
└── feature/* (individual features)

Tags: v1.0.0, v1.0.1, ...
Releases: Major features + documentation
```

---

## 📚 Dipendenze Critiche

- **Python**: Runtime
- **PostgreSQL**: Data persistence
- **PostGIS**: Geospatial queries
- **pandas**: Data manipulation
- **geopandas**: Spatial dataframes
- **sqlalchemy**: ORM + database abstraction
- **streamlit**: Web dashboard
- **plotly**: Interactive visualizations

---

**Documento creato**: Maggio 2026  
**Versione**: 1.0  
**Autore**: Data Engineering Team

# DATABASE SCHEMA - HEATWAVE PIEMONTE

## 📋 Modello Relazionale

```
┌─────────────────────────────────────────────────────┐
│              HEATWAVE PIEMONTE DATABASE             │
└─────────────────────────────────────────────────────┘

PROVINCES (Province piemontesi)
├─ province_id: INTEGER (PRIMARY KEY)
├─ name: VARCHAR(50)
├─ geometry: GEOMETRY(POINT, 4326)
├─ area_km2: FLOAT
└─ created_at: TIMESTAMP

MUNICIPALITIES (Comuni piemontesi)
├─ municipality_id: INTEGER (PRIMARY KEY)
├─ province_id: INTEGER (FOREIGN KEY → PROVINCES)
├─ name: VARCHAR(100)
├─ istat_code: VARCHAR(6) UNIQUE
├─ geometry: GEOMETRY(POLYGON, 4326)
├─ elevation_m: INTEGER
└─ created_at: TIMESTAMP

TEMPERATURE (Timeseries dati giornalieri)
├─ temperature_id: BIGINT (PRIMARY KEY)
├─ municipality_id: INTEGER (FOREIGN KEY → MUNICIPALITIES)
├─ province_id: INTEGER (FOREIGN KEY → PROVINCES)
├─ date: DATE (INDEXED)
├─ temp_mean: FLOAT (°C)
├─ temp_max: FLOAT (°C)
├─ temp_min: FLOAT (°C)
├─ precipitation: FLOAT (mm)
├─ data_source: VARCHAR(50)
├─ quality_flag: SMALLINT (0=good, 1=suspect)
└─ created_at: TIMESTAMP

HEATWAVE_EVENTS (Ondate di calore identificate)
├─ heatwave_id: BIGINT (PRIMARY KEY)
├─ municipality_id: INTEGER (FOREIGN KEY → MUNICIPALITIES)
├─ province_id: INTEGER (FOREIGN KEY → PROVINCES)
├─ start_date: DATE
├─ end_date: DATE
├─ duration_days: SMALLINT
├─ max_temp: FLOAT
├─ intensity_index: FLOAT (0-100)
├─ heat_threshold: FLOAT (°C)
├─ threshold_type: VARCHAR(20) (e.g., '>35', '>40')
└─ identified_at: TIMESTAMP

KPI (Key Performance Indicators aggregati)
├─ kpi_id: BIGINT (PRIMARY KEY)
├─ municipality_id: INTEGER (NULLABLE, FOREIGN KEY)
├─ province_id: INTEGER (NULLABLE, FOREIGN KEY)
├─ year: SMALLINT (INDEXED)
├─ month: SMALLINT (1-12)
├─ level: VARCHAR(20) ('municipal', 'provincial', 'regional')
├─ temp_mean_annual: FLOAT
├─ temp_max_annual: FLOAT
├─ temp_min_annual: FLOAT
├─ days_gt_30c: SMALLINT
├─ days_gt_35c: SMALLINT
├─ days_gt_40c: SMALLINT
├─ heatwave_count: SMALLINT
├─ heatwave_avg_duration: FLOAT
├─ annual_anomaly: FLOAT
├─ computed_at: TIMESTAMP
└─ version: SMALLINT

METADATA (Informazioni di sistema)
├─ key: VARCHAR(100) (PRIMARY KEY)
├─ value: TEXT
├─ data_type: VARCHAR(20)
├─ last_updated: TIMESTAMP
└─ notes: TEXT
```

## 🔑 Chiavi e Vincoli

### Primary Keys
```sql
PROVINCES.province_id
MUNICIPALITIES.municipality_id
TEMPERATURE.temperature_id
HEATWAVE_EVENTS.heatwave_id
KPI.kpi_id
METADATA.key
```

### Foreign Keys
```sql
MUNICIPALITIES.province_id → PROVINCES.province_id
TEMPERATURE.municipality_id → MUNICIPALITIES.municipality_id
TEMPERATURE.province_id → PROVINCES.province_id
HEATWAVE_EVENTS.municipality_id → MUNICIPALITIES.municipality_id
HEATWAVE_EVENTS.province_id → PROVINCES.province_id
KPI.municipality_id → MUNICIPALITIES.municipality_id
KPI.province_id → PROVINCES.province_id
```

### Unique Constraints
```sql
MUNICIPALITIES(istat_code)
PROVINCES(name)
```

## 📑 Tabelle Dettagliate

**Nota**: Province e comuni hanno geometrie generate per testing. In produzione, usare dati ufficiali.

### 1. PROVINCES

| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| province_id | SERIAL | ID univoco provincia |
| name | VARCHAR(50) | Nome provincia (es. "Torino") |
| geometry | GEOMETRY | Centroide geografico (POINT) |
| area_km2 | NUMERIC(10,2) | Area in km² |
| created_at | TIMESTAMP | Data creazione record |

**Indici**:
```sql
CREATE INDEX idx_provinces_name ON provinces(name);
CREATE INDEX idx_provinces_geometry ON provinces USING GIST(geometry);
```

---

### 2. MUNICIPALITIES

| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| municipality_id | SERIAL | ID univoco comune |
| province_id | INT | FK a PROVINCES |
| name | VARCHAR(100) | Nome comune |
| istat_code | VARCHAR(6) | Codice ISTAT univoco |
| geometry | GEOMETRY | Geometria amministrativa (POLYGON) |
| elevation_m | SMALLINT | Altitudine in metri |
| created_at | TIMESTAMP | Data inserimento |

**Indici**:
```sql
CREATE INDEX idx_municipalities_province ON municipalities(province_id);
CREATE INDEX idx_municipalities_istat ON municipalities(istat_code);
CREATE INDEX idx_municipalities_geometry ON municipalities USING GIST(geometry);
```

---

### 3. TEMPERATURE (TIMESERIES PRINCIPALE)

| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| temperature_id | BIGINT | ID univoco record |
| municipality_id | INT | FK a MUNICIPALITIES |
| province_id | INT | FK a PROVINCES (denormalizzato per query speed) |
| date | DATE | Data misura (INDEXED) |
| temp_mean | FLOAT | Temperatura media (°C) |
| temp_max | FLOAT | Temperatura massima (°C) |
| temp_min | FLOAT | Temperatura minima (°C) |
| precipitation | FLOAT | Precipitazioni (mm) |
| data_source | VARCHAR(50) | Fonte dati (e.g., 'ARPA', 'OpenMeteo') |
| quality_flag | SMALLINT | 0=buona qualità, 1=sospetta |
| created_at | TIMESTAMP | Data inserimento |

**Statistiche**:
- ~1.2M righe per comune (26 anni × 365 giorni)
- ~200M righe totali (170 comuni)
- Size: ~2-3 GB

**Indici Critici**:
```sql
CREATE INDEX idx_temperature_date ON temperature(date);
CREATE INDEX idx_temperature_municipality_date ON temperature(municipality_id, date);
CREATE INDEX idx_temperature_province_date ON temperature(province_id, date);
CREATE INDEX idx_temperature_temp_mean ON temperature(temp_mean) 
  WHERE temp_mean > 30;  -- Partial index
```

**Partitioning** (opzionale per performance):
```sql
CREATE TABLE temperature_2000 PARTITION OF temperature
  FOR VALUES FROM ('2000-01-01') TO ('2000-12-31');
CREATE TABLE temperature_2001 PARTITION OF temperature
  FOR VALUES FROM ('2001-01-01') TO ('2001-12-31');
-- ... e così via per ogni anno
```

---

### 4. HEATWAVE_EVENTS

| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| heatwave_id | BIGINT | ID evento |
| municipality_id | INT | FK a MUNICIPALITIES |
| province_id | INT | FK a PROVINCES |
| start_date | DATE | Inizio ondata |
| end_date | DATE | Fine ondata |
| duration_days | SMALLINT | Giorni consecutivi |
| max_temp | FLOAT | Temp max raggiunta (°C) |
| intensity_index | FLOAT | Indice 0-100 (calc: (max_temp - threshold) * duration) |
| heat_threshold | FLOAT | Soglia usata (es. 35°C) |
| threshold_type | VARCHAR(20) | Tipo soglia ('GT_30', 'GT_35', 'GT_40') |
| identified_at | TIMESTAMP | Data identificazione |

**Criteri Identificazione**:
- Minimo 3 giorni consecutivi con temp_max > soglia
- Soglie: 30°C (caldo), 35°C (intenso), 40°C (estremo)

**Indici**:
```sql
CREATE INDEX idx_heatwave_dates ON heatwave_events(start_date, end_date);
CREATE INDEX idx_heatwave_municipality ON heatwave_events(municipality_id);
CREATE INDEX idx_heatwave_intensity ON heatwave_events(intensity_index DESC);
```

---

### 5. KPI (AGGREGATED METRICS)

| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| kpi_id | BIGINT | ID KPI |
| municipality_id | INT | FK a MUNICIPALITIES (NULL se provinciale) |
| province_id | INT | FK a PROVINCES (NULL se municipale) |
| year | SMALLINT | Anno |
| month | SMALLINT | Mese (1-12) o 0 per annuale |
| level | VARCHAR(20) | 'municipal', 'provincial', 'regional' |
| temp_mean_annual | FLOAT | Media annuale (°C) |
| temp_max_annual | FLOAT | Massima annuale (°C) |
| temp_min_annual | FLOAT | Minima annuale (°C) |
| days_gt_30c | SMALLINT | Giorni >30°C |
| days_gt_35c | SMALLINT | Giorni >35°C |
| days_gt_40c | SMALLINT | Giorni >40°C |
| heatwave_count | SMALLINT | Numero ondate >3 giorni |
| heatwave_avg_duration | FLOAT | Durata media (giorni) |
| annual_anomaly | FLOAT | Differenza da media climatica 1961-1990 (°C) |
| computed_at | TIMESTAMP | Quando calcolato |
| version | SMALLINT | Versione calcolo (per track cambiamenti) |

**Computed View Example**:
```sql
CREATE MATERIALIZED VIEW kpi_annual AS
SELECT 
  municipality_id,
  province_id,
  EXTRACT(YEAR FROM date)::SMALLINT as year,
  AVG(temp_mean) as temp_mean_annual,
  MAX(temp_max) as temp_max_annual,
  MIN(temp_min) as temp_min_annual,
  COUNT(*) FILTER (WHERE temp_max > 30) as days_gt_30c,
  COUNT(*) FILTER (WHERE temp_max > 35) as days_gt_35c,
  COUNT(*) FILTER (WHERE temp_max > 40) as days_gt_40c
FROM temperature
GROUP BY municipality_id, province_id, year;
```

---

### 6. METADATA

| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| key | VARCHAR(100) | Identificatore chiave |
| value | TEXT | Valore |
| data_type | VARCHAR(20) | 'string', 'number', 'date', 'json' |
| last_updated | TIMESTAMP | Ultimo aggiornamento |
| notes | TEXT | Note descrittive |

**Esempi di record**:
```sql
INSERT INTO metadata VALUES
('database_version', '1.0', 'string', NOW(), 'Schema version'),
('last_etl_run', '2026-05-30 14:30:00', 'date', NOW(), 'Ultimo caricamento dati'),
('data_completeness', '95.5', 'number', NOW(), '% di completezza dati'),
('copernicus_key', 'xxxxxxxx', 'string', NOW(), 'API key Copernicus');
```

---

## 🔒 Sicurezza Database

### Roles & Permissions

```sql
-- Ruolo di lettura (per dashboard)
CREATE ROLE app_reader WITH LOGIN PASSWORD 'password';
GRANT CONNECT ON DATABASE heatwave_piemonte TO app_reader;
GRANT USAGE ON SCHEMA public TO app_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_reader;

-- Ruolo di scrittura (per ETL)
CREATE ROLE etl_writer WITH LOGIN PASSWORD 'password';
GRANT CONNECT ON DATABASE heatwave_piemonte TO etl_writer;
GRANT USAGE, CREATE ON SCHEMA public TO etl_writer;
GRANT INSERT, UPDATE, DELETE, SELECT ON ALL TABLES IN SCHEMA public TO etl_writer;

-- Ruolo admin (development)
CREATE ROLE admin WITH SUPERUSER;
```

---

## 📊 Statistiche Dati Attese

| Metrica | Valore |
|---------|--------|
| Numero province | 8 |
| Numero comuni | ~170 |
| Anni dati | 27 (2000-2026) |
| Giorni per comune | ~9,855 |
| Total records temperatura | ~1.7M |
| Total records heatwave | ~500-1,000 |
| Dimensione DB | ~3-5 GB |
| Dimensione indici | ~800 MB |

---

**Creato**: Maggio 2026  
**Versione Schema**: 1.0  
**Compatibilità**: PostgreSQL 14+, PostGIS 3.0+

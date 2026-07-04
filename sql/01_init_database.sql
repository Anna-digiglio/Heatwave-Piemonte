-- ============================================================================
-- HEATWAVE PIEMONTE - Database Initialization
-- PostgreSQL 14+ with PostGIS 3.0+
-- ============================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- ============================================================================
-- 1. PROVINCES TABLE (Province piemontesi)
-- ============================================================================

CREATE TABLE IF NOT EXISTS provinces (
    province_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    istat_code VARCHAR(3),
    geometry GEOMETRY(POINT, 4326) NOT NULL,
    area_km2 NUMERIC(10, 2),
    population INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_provinces_name ON provinces(name);
CREATE INDEX IF NOT EXISTS idx_provinces_geometry ON provinces USING GIST(geometry);
CREATE INDEX IF NOT EXISTS idx_provinces_istat ON provinces(istat_code);

-- ============================================================================
-- 2. MUNICIPALITIES TABLE (Comuni piemontesi)
-- ============================================================================

CREATE TABLE IF NOT EXISTS municipalities (
    municipality_id SERIAL PRIMARY KEY,
    province_id INTEGER NOT NULL REFERENCES provinces(province_id) ON DELETE RESTRICT,
    name VARCHAR(100) NOT NULL,
    istat_code VARCHAR(6) NOT NULL UNIQUE,
    -- MULTIPOLYGON e non POLYGON: alcuni comuni reali (es. exclavi/isole
    -- amministrative) hanno confini multi-parte nei dati ISTAT.
    geometry GEOMETRY(MULTIPOLYGON, 4326) NOT NULL,
    elevation_m SMALLINT,
    population INTEGER,
    area_km2 NUMERIC(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_municipalities_province ON municipalities(province_id);
CREATE INDEX IF NOT EXISTS idx_municipalities_istat ON municipalities(istat_code);
CREATE INDEX IF NOT EXISTS idx_municipalities_geometry ON municipalities USING GIST(geometry);
CREATE INDEX IF NOT EXISTS idx_municipalities_name ON municipalities(name);

-- ============================================================================
-- 3. TEMPERATURE TABLE (Timeseries dati giornalieri)
-- ============================================================================

CREATE TABLE IF NOT EXISTS temperature (
    temperature_id BIGSERIAL PRIMARY KEY,
    municipality_id INTEGER NOT NULL REFERENCES municipalities(municipality_id),
    province_id INTEGER NOT NULL REFERENCES provinces(province_id),
    date DATE NOT NULL,
    temp_mean FLOAT,
    temp_max FLOAT NOT NULL,
    temp_min FLOAT NOT NULL,
    precipitation FLOAT DEFAULT 0,
    humidity FLOAT,
    data_source VARCHAR(50) DEFAULT 'unknown',
    quality_flag SMALLINT DEFAULT 0,  -- 0=good, 1=suspect, 2=bad
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_temperature CHECK (
        temp_min <= temp_mean AND temp_mean <= temp_max AND
        temp_max >= -50 AND temp_min <= 60
    )
);

-- Critical indexes for performance
CREATE INDEX IF NOT EXISTS idx_temperature_date ON temperature(date);
CREATE INDEX IF NOT EXISTS idx_temperature_municipality_date ON temperature(municipality_id, date);
CREATE INDEX IF NOT EXISTS idx_temperature_province_date ON temperature(province_id, date);
CREATE INDEX IF NOT EXISTS idx_temperature_temp_max ON temperature(temp_max) 
    WHERE temp_max > 30;
CREATE INDEX IF NOT EXISTS idx_temperature_data_source ON temperature(data_source);

-- ============================================================================
-- 4. HEATWAVE_EVENTS TABLE (Ondate di calore identificate)
-- ============================================================================

CREATE TABLE IF NOT EXISTS heatwave_events (
    heatwave_id BIGSERIAL PRIMARY KEY,
    municipality_id INTEGER NOT NULL REFERENCES municipalities(municipality_id),
    province_id INTEGER NOT NULL REFERENCES provinces(province_id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    duration_days SMALLINT NOT NULL,
    max_temp FLOAT NOT NULL,
    mean_temp FLOAT,
    intensity_index FLOAT,  -- (max_temp - threshold) * duration
    heat_threshold FLOAT NOT NULL,
    threshold_type VARCHAR(20),  -- 'GT_30', 'GT_35', 'GT_40'
    identified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_heatwave CHECK (
        end_date >= start_date AND duration_days >= 3
    )
);

CREATE INDEX IF NOT EXISTS idx_heatwave_dates ON heatwave_events(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_heatwave_municipality ON heatwave_events(municipality_id);
CREATE INDEX IF NOT EXISTS idx_heatwave_province ON heatwave_events(province_id);
CREATE INDEX IF NOT EXISTS idx_heatwave_intensity ON heatwave_events(intensity_index DESC);
CREATE INDEX IF NOT EXISTS idx_heatwave_threshold ON heatwave_events(heat_threshold);

-- ============================================================================
-- 5. KPI TABLE (Key Performance Indicators aggregati)
-- ============================================================================

CREATE TABLE IF NOT EXISTS kpi (
    kpi_id BIGSERIAL PRIMARY KEY,
    municipality_id INTEGER REFERENCES municipalities(municipality_id),
    province_id INTEGER REFERENCES provinces(province_id),
    year SMALLINT NOT NULL,
    month SMALLINT,  -- 0-12, 0 for annual
    level VARCHAR(20) NOT NULL,  -- 'municipal', 'provincial', 'regional'
    temp_mean_annual FLOAT,
    temp_max_annual FLOAT,
    temp_min_annual FLOAT,
    days_gt_30c SMALLINT DEFAULT 0,
    days_gt_35c SMALLINT DEFAULT 0,
    days_gt_40c SMALLINT DEFAULT 0,
    heatwave_count SMALLINT DEFAULT 0,
    heatwave_avg_duration FLOAT,
    annual_anomaly FLOAT,  -- vs 1961-1990 baseline
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version SMALLINT DEFAULT 1,
    CONSTRAINT valid_kpi CHECK (
        (municipality_id IS NOT NULL AND province_id IS NULL AND level = 'municipal') OR
        (municipality_id IS NULL AND province_id IS NOT NULL AND level = 'provincial') OR
        (municipality_id IS NULL AND province_id IS NULL AND level = 'regional')
    )
);

CREATE INDEX IF NOT EXISTS idx_kpi_year ON kpi(year);
CREATE INDEX IF NOT EXISTS idx_kpi_municipality_year ON kpi(municipality_id, year);
CREATE INDEX IF NOT EXISTS idx_kpi_province_year ON kpi(province_id, year);
CREATE INDEX IF NOT EXISTS idx_kpi_level ON kpi(level);

-- ============================================================================
-- 6. METADATA TABLE (Informazioni di sistema)
-- ============================================================================

CREATE TABLE IF NOT EXISTS metadata (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    data_type VARCHAR(20),  -- 'string', 'number', 'date', 'json'
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- ============================================================================
-- 7. MATERIALIZED VIEWS (Per performance su query comuni)
-- ============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS kpi_annual_by_municipality AS
SELECT
    municipality_id,
    province_id,
    EXTRACT(YEAR FROM date)::SMALLINT as year,
    COUNT(*) as total_days,
    ROUND(AVG(temp_mean)::numeric, 2)::FLOAT as temp_mean_annual,
    MAX(temp_max)::FLOAT as temp_max_annual,
    MIN(temp_min)::FLOAT as temp_min_annual,
    COUNT(*) FILTER (WHERE temp_max > 30)::SMALLINT as days_gt_30c,
    COUNT(*) FILTER (WHERE temp_max > 35)::SMALLINT as days_gt_35c,
    COUNT(*) FILTER (WHERE temp_max > 40)::SMALLINT as days_gt_40c,
    STDDEV_POP(temp_max)::FLOAT as stddev_temp_max,
    CURRENT_TIMESTAMP as computed_at
FROM temperature
WHERE temp_max IS NOT NULL
GROUP BY municipality_id, province_id, EXTRACT(YEAR FROM date)
ORDER BY year, municipality_id;

CREATE INDEX IF NOT EXISTS idx_kpi_annual_municipality ON kpi_annual_by_municipality(municipality_id, year);
CREATE INDEX IF NOT EXISTS idx_kpi_annual_province ON kpi_annual_by_municipality(province_id, year);

---

CREATE MATERIALIZED VIEW IF NOT EXISTS kpi_annual_by_province AS
SELECT
    NULL::INTEGER as municipality_id,
    province_id,
    EXTRACT(YEAR FROM date)::SMALLINT as year,
    COUNT(*) as total_days,
    ROUND(AVG(temp_mean)::numeric, 2)::FLOAT as temp_mean_annual,
    MAX(temp_max)::FLOAT as temp_max_annual,
    MIN(temp_min)::FLOAT as temp_min_annual,
    COUNT(*) FILTER (WHERE temp_max > 30)::SMALLINT as days_gt_30c,
    COUNT(*) FILTER (WHERE temp_max > 35)::SMALLINT as days_gt_35c,
    COUNT(*) FILTER (WHERE temp_max > 40)::SMALLINT as days_gt_40c,
    STDDEV_POP(temp_max)::FLOAT as stddev_temp_max,
    CURRENT_TIMESTAMP as computed_at
FROM temperature
WHERE temp_max IS NOT NULL
GROUP BY province_id, EXTRACT(YEAR FROM date)
ORDER BY year, province_id;

CREATE INDEX IF NOT EXISTS idx_kpi_annual_province_year ON kpi_annual_by_province(province_id, year);

-- ============================================================================
-- 8. FUNCTIONS (Stored Procedures)
-- ============================================================================

-- Funzione per identificare ondate di calore
CREATE OR REPLACE FUNCTION identify_heatwaves(
    p_heat_threshold FLOAT DEFAULT 35.0,
    p_min_duration SMALLINT DEFAULT 3
)
RETURNS TABLE (
    heatwave_id BIGINT,
    municipality_id INTEGER,
    province_id INTEGER,
    start_date DATE,
    end_date DATE,
    duration_days SMALLINT,
    max_temp FLOAT,
    intensity_index FLOAT
) AS $$
DECLARE
    rec RECORD;
    v_current_streak INT := 0;
    v_streak_start DATE;
    v_max_temp FLOAT;
BEGIN
    FOR rec IN
        SELECT 
            municipality_id,
            province_id,
            date,
            temp_max
        FROM temperature
        WHERE temp_max > p_heat_threshold
        ORDER BY municipality_id, date
    LOOP
        IF v_current_streak = 0 THEN
            v_streak_start := rec.date;
            v_max_temp := rec.temp_max;
            v_current_streak := 1;
        ELSE
            IF rec.date = v_streak_start + (v_current_streak || ' days')::INTERVAL THEN
                v_current_streak := v_current_streak + 1;
                v_max_temp := GREATEST(v_max_temp, rec.temp_max);
            ELSE
                IF v_current_streak >= p_min_duration THEN
                    INSERT INTO heatwave_events
                    (municipality_id, province_id, start_date, end_date, 
                     duration_days, max_temp, heat_threshold, threshold_type)
                    VALUES
                    (rec.municipality_id, rec.province_id, v_streak_start,
                     v_streak_start + ((v_current_streak - 1) || ' days')::INTERVAL,
                     v_current_streak, v_max_temp, p_heat_threshold,
                     'GT_' || CAST(CAST(p_heat_threshold AS INT) AS VARCHAR));
                END IF;
                v_streak_start := rec.date;
                v_max_temp := rec.temp_max;
                v_current_streak := 1;
            END IF;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 9. INSERT DATI DI TEST (8 Province piemontesi)
-- ============================================================================

INSERT INTO provinces (name, istat_code, geometry, area_km2, population) VALUES
('Alessandria', '006', ST_GeomFromText('POINT(8.64 44.91)', 4326), 3559, 427000),
('Asti', '005', ST_GeomFromText('POINT(8.19 44.90)', 4326), 1511, 206000),
('Biella', '096', ST_GeomFromText('POINT(8.06 45.57)', 4326), 913, 175000),
('Cuneo', '004', ST_GeomFromText('POINT(7.54 44.39)', 4326), 6903, 585000),
('Novara', '003', ST_GeomFromText('POINT(8.62 45.44)', 4326), 1339, 365000),
('Torino', '001', ST_GeomFromText('POINT(7.68 45.07)', 4326), 6829, 2257000),
('Verbano-Cusio-Ossola', '103', ST_GeomFromText('POINT(8.57 45.93)', 4326), 2255, 161000),
('Vercelli', '002', ST_GeomFromText('POINT(8.42 45.32)', 4326), 2089, 176000)
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- 10. METADATA INITIALIZATION
-- ============================================================================

INSERT INTO metadata (key, value, data_type, notes) VALUES
('database_version', '1.0', 'string', 'Schema version'),
('last_etl_run', NULL, 'date', 'Last successful data load'),
('data_start_year', '2000', 'number', 'First year of data'),
('data_end_year', '2026', 'number', 'Last year of data'),
('data_completeness', '0', 'number', '% of data completeness'),
('created_at', CURRENT_TIMESTAMP::TEXT, 'date', 'Database creation date')
ON CONFLICT (key) DO UPDATE SET 
    value = EXCLUDED.value,
    last_updated = CURRENT_TIMESTAMP;

-- ============================================================================
-- 11. CREATE GRANTS
-- ============================================================================

-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO etl_writer;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_reader;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO etl_writer;

-- ============================================================================
-- Execution summary
-- ============================================================================
-- ESECUZIONE:
-- psql -U postgres -d heatwave_piemonte -f sql/01_init_database.sql
-- 
-- Tabelle create: 6
-- Views create: 2
-- Indici create: 25+
-- Funzioni create: 1
-- ============================================================================

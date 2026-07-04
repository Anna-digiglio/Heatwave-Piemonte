-- ============================================================================
-- HEATWAVE PIEMONTE - Query SQL Utili per Analisi
-- ============================================================================

-- ===========================================================================
-- 1. TREND TEMPERATURA ANNUALE PER PROVINCIA
-- ===========================================================================

-- Query: Temperatura media annuale per provincia (2000-2026)
SELECT 
    p.name as provincia,
    EXTRACT(YEAR FROM t.date)::INT as anno,
    ROUND(AVG(t.temp_mean)::numeric, 2) as temp_media_c,
    ROUND(MAX(t.temp_max)::numeric, 2) as temp_max_c,
    ROUND(MIN(t.temp_min)::numeric, 2) as temp_min_c,
    ROUND(STDDEV_POP(t.temp_max)::numeric, 2) as stddev_temp_max,
    COUNT(*) as total_giorni,
    COUNT(*) FILTER (WHERE t.temp_max > 40) as giorni_over_40c,
    COUNT(*) FILTER (WHERE t.temp_max > 35) as giorni_over_35c,
    COUNT(*) FILTER (WHERE t.temp_max > 30) as giorni_over_30c
FROM temperature t
JOIN provinces p ON t.province_id = p.province_id
WHERE t.date >= '2000-01-01' AND t.date <= CURRENT_DATE
GROUP BY p.province_id, p.name, EXTRACT(YEAR FROM t.date)
ORDER BY anno ASC, p.name;

-- ===========================================================================
-- 2. TREND DECENNALE - VARIAZIONE PERCENTUALE
-- ===========================================================================

-- Query: Variazione temperatura ogni 10 anni (decenni 2000-2010, 2010-2020, 2020-2026)
WITH decadal_stats AS (
    SELECT 
        p.province_id,
        p.name,
        CASE 
            WHEN EXTRACT(YEAR FROM t.date) < 2010 THEN '2000-2009'
            WHEN EXTRACT(YEAR FROM t.date) < 2020 THEN '2010-2019'
            ELSE '2020-2026'
        END as decennio,
        AVG(t.temp_mean) as temp_media,
        COUNT(*) FILTER (WHERE t.temp_max > 35) as giorni_over_35
    FROM temperature t
    JOIN provinces p ON t.province_id = p.province_id
    WHERE t.date >= '2000-01-01' AND t.date <= CURRENT_DATE
    GROUP BY p.province_id, p.name, decennio
)
SELECT 
    name,
    MAX(CASE WHEN decennio = '2000-2009' THEN temp_media END) as temp_2000_2009,
    MAX(CASE WHEN decennio = '2010-2019' THEN temp_media END) as temp_2010_2019,
    MAX(CASE WHEN decennio = '2020-2026' THEN temp_media END) as temp_2020_2026,
    ROUND((
        (MAX(CASE WHEN decennio = '2020-2026' THEN temp_media END) - 
         MAX(CASE WHEN decennio = '2000-2009' THEN temp_media END)) / 
        MAX(CASE WHEN decennio = '2000-2009' THEN temp_media END) * 100
    )::numeric, 2) as variazione_perc_26_anni,
    MAX(CASE WHEN decennio = '2000-2009' THEN giorni_over_35 END) as giorni_over_35_2000_2009,
    MAX(CASE WHEN decennio = '2020-2026' THEN giorni_over_35 END) as giorni_over_35_2020_2026
FROM decadal_stats
GROUP BY province_id, name
ORDER BY variazione_perc_26_anni DESC;

-- ===========================================================================
-- 3. PROVINCIA CON MAGGIORI INCREMENTI
-- ===========================================================================

-- Query: Province con massimo incremento temperatura (regressione lineare)
WITH yearly_temp AS (
    SELECT 
        p.name,
        EXTRACT(YEAR FROM t.date)::INT as anno,
        AVG(t.temp_mean) as temp_media
    FROM temperature t
    JOIN provinces p ON t.province_id = p.province_id
    WHERE t.date >= '2000-01-01' AND t.date <= CURRENT_DATE
    GROUP BY p.province_id, p.name, anno
)
SELECT 
    name,
    COUNT(*) as anni,
    ROUND(AVG(temp_media)::numeric, 2) as temp_media_overall,
    ROUND((regr_slope(temp_media, anno) * 26)::numeric, 2) as incremento_26_anni_c,
    ROUND(regr_slope(temp_media, anno)::numeric, 4) as slope_per_anno,
    ROUND(regr_r2(temp_media, anno)::numeric, 3) as r2_regressione
FROM yearly_temp
GROUP BY name
ORDER BY incremento_26_anni_c DESC;

-- ===========================================================================
-- 4. GIORNI CON TEMPERATURE ESTREME (>30, >35, >40)
-- ===========================================================================

-- Query: Conteggio giorni per soglia di temperatura per comune
SELECT 
    m.name as comune,
    p.name as provincia,
    COUNT(*) FILTER (WHERE t.temp_max >= 30 AND t.temp_max < 35) as giorni_30_35c,
    COUNT(*) FILTER (WHERE t.temp_max >= 35 AND t.temp_max < 40) as giorni_35_40c,
    COUNT(*) FILTER (WHERE t.temp_max >= 40) as giorni_oltre_40c,
    COUNT(*) FILTER (WHERE t.temp_max >= 30) as giorni_over_30c_totale,
    EXTRACT(YEAR FROM t.date)::INT as anno
FROM temperature t
JOIN municipalities m ON t.municipality_id = m.municipality_id
JOIN provinces p ON t.province_id = p.province_id
WHERE t.date >= '2000-01-01' AND t.date <= CURRENT_DATE
    AND t.temp_max IS NOT NULL
GROUP BY m.municipality_id, m.name, p.name, EXTRACT(YEAR FROM t.date)
ORDER BY anno DESC, giorni_oltre_40c DESC
LIMIT 50;

-- ===========================================================================
-- 5. ONDATE DI CALORE - STATISTICHE
-- ===========================================================================

-- Query: Statistiche ondate di calore per provincia
SELECT 
    p.name as provincia,
    EXTRACT(YEAR FROM h.start_date)::INT as anno,
    COUNT(*) as numero_ondate,
    ROUND(AVG(h.duration_days)::numeric, 1) as durata_media_giorni,
    MAX(h.duration_days) as durata_max_giorni,
    MIN(h.duration_days) as durata_min_giorni,
    ROUND(AVG(h.max_temp)::numeric, 1) as temp_max_media,
    MAX(h.max_temp) as temp_max_assoluta,
    ROUND(AVG(h.intensity_index)::numeric, 1) as intensity_media
FROM heatwave_events h
JOIN provinces p ON h.province_id = p.province_id
WHERE h.heat_threshold = 35  -- Filtra per ondate intensità >35°C
GROUP BY p.province_id, p.name, EXTRACT(YEAR FROM h.start_date)
ORDER BY anno DESC, numero_ondate DESC;

-- ===========================================================================
-- 6. COMPARAZIONE TERRITORIALE - PROVINCE A CONFRONTO
-- ===========================================================================

-- Query: Tabella di comparazione tra province
SELECT 
    p.name as provincia,
    ROUND(AVG(t.temp_mean)::numeric, 2) as temp_media_overall_c,
    ROUND(MAX(t.temp_max)::numeric, 2) as temp_max_record_c,
    ROUND(MIN(t.temp_min)::numeric, 2) as temp_min_record_c,
    COUNT(*) FILTER (WHERE t.temp_max > 40) as giorni_totali_over_40c,
    COUNT(*) FILTER (WHERE t.temp_max > 35) as giorni_totali_over_35c,
    (SELECT COUNT(*) 
     FROM heatwave_events h 
     WHERE h.province_id = p.province_id 
     AND h.heat_threshold = 35) as numero_ondate_35c,
    ROUND((COUNT(*) FILTER (WHERE t.temp_max > 35)::FLOAT / 
          COUNT(*)::FLOAT * 100)::numeric, 2) as perc_giorni_over_35c,
    COUNT(DISTINCT m.municipality_id) as numero_comuni,
    p.population as popolazione_provincia
FROM temperature t
JOIN provinces p ON t.province_id = p.province_id
LEFT JOIN municipalities m ON t.municipality_id = m.municipality_id
WHERE t.date >= '2000-01-01' AND t.date <= CURRENT_DATE
GROUP BY p.province_id, p.name, p.population
ORDER BY temp_media_overall_c DESC;

-- ===========================================================================
-- 7. COMUNI PIÙ VULNERABILI (INDICE DI VULNERABILITÀ)
-- ===========================================================================

-- Query: Indice di vulnerabilità alle ondate di calore
SELECT 
    m.name as comune,
    p.name as provincia,
    m.elevation_m as altitudine_m,
    COUNT(*) FILTER (WHERE t.temp_max > 35)::FLOAT / 
        COUNT(*)::FLOAT * 100 as perc_giorni_hot,
    COUNT(*) FILTER (WHERE t.temp_max > 40) as giorni_extreme,
    (SELECT COUNT(*) 
     FROM heatwave_events h 
     WHERE h.municipality_id = m.municipality_id) as numero_heatwave,
    ROUND(((COUNT(*) FILTER (WHERE t.temp_max > 35)::FLOAT * 0.5) +
           (COUNT(*) FILTER (WHERE t.temp_max > 40)::FLOAT * 0.3) +
           ((SELECT COUNT(*) 
             FROM heatwave_events h 
             WHERE h.municipality_id = m.municipality_id)::FLOAT * 0.2)
    )::numeric, 2) as indice_vulnerabilita
FROM temperature t
JOIN municipalities m ON t.municipality_id = m.municipality_id
JOIN provinces p ON t.province_id = p.province_id
WHERE t.date >= '2000-01-01' AND t.date <= CURRENT_DATE
GROUP BY m.municipality_id, m.name, p.name, m.elevation_m
HAVING COUNT(*) > 500  -- Solo comuni con dati sufficienti
ORDER BY indice_vulnerabilita DESC
LIMIT 30;

-- ===========================================================================
-- 8. SERIE TEMPORALE - MEDIE MOBILI
-- ===========================================================================

-- Query: Media mobile 30 giorni per provincia (utile per smoothing)
SELECT 
    p.name as provincia,
    t.date,
    t.temp_mean,
    AVG(t.temp_mean) OVER (
        PARTITION BY t.province_id 
        ORDER BY t.date 
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) as media_mobile_30gg,
    AVG(t.temp_mean) OVER (
        PARTITION BY t.province_id 
        ORDER BY t.date 
        ROWS BETWEEN 364 PRECEDING AND CURRENT ROW
    ) as media_mobile_1anno
FROM temperature t
JOIN provinces p ON t.province_id = p.province_id
WHERE t.date >= '2000-01-01' AND t.date <= CURRENT_DATE
    AND t.province_id IN (SELECT province_id FROM provinces WHERE name = 'Torino')
ORDER BY t.date
LIMIT 1000;

-- ===========================================================================
-- 9. ANOMALIA TERMICA - DIFFERENZA DA BASELINE
-- ===========================================================================

-- Query: Anomalia termica rispetto a periodo baseline (es. 1961-1990)
-- NOTA: Questo richiede una baseline esterna (non presente nei dati 2000-2026)
-- La query calcola invece anomalia rispetto alla media 2000-2009

WITH baseline AS (
    SELECT 
        province_id,
        EXTRACT(MONTH FROM date)::INT as mese,
        AVG(temp_mean) as temp_baseline
    FROM temperature
    WHERE EXTRACT(YEAR FROM date) BETWEEN 2000 AND 2009
    GROUP BY province_id, EXTRACT(MONTH FROM date)
)
SELECT 
    p.name as provincia,
    EXTRACT(YEAR FROM t.date)::INT as anno,
    EXTRACT(MONTH FROM t.date)::INT as mese,
    ROUND(AVG(t.temp_mean)::numeric, 2) as temp_media_corrente,
    ROUND(b.temp_baseline::numeric, 2) as temp_baseline,
    ROUND((AVG(t.temp_mean) - b.temp_baseline)::numeric, 2) as anomalia_c
FROM temperature t
JOIN provinces p ON t.province_id = p.province_id
JOIN baseline b ON t.province_id = b.province_id 
    AND EXTRACT(MONTH FROM t.date)::INT = b.mese
WHERE t.date >= '2010-01-01' AND t.date <= CURRENT_DATE
GROUP BY p.province_id, p.name, anno, mese, b.temp_baseline
ORDER BY anno DESC, mese, p.name;

-- ===========================================================================
-- 10. DISTRIBUZIONE FREQUENZA TEMPERATURE
-- ===========================================================================

-- Query: Istogramma temperature per provincia
SELECT 
    p.name as provincia,
    CASE 
        WHEN t.temp_max < 0 THEN '< 0°C'
        WHEN t.temp_max < 10 THEN '0-10°C'
        WHEN t.temp_max < 20 THEN '10-20°C'
        WHEN t.temp_max < 25 THEN '20-25°C'
        WHEN t.temp_max < 30 THEN '25-30°C'
        WHEN t.temp_max < 35 THEN '30-35°C'
        WHEN t.temp_max < 40 THEN '35-40°C'
        ELSE '> 40°C'
    END as range_temp,
    COUNT(*) as numero_giorni,
    ROUND(COUNT(*)::FLOAT / COUNT(*) OVER (PARTITION BY p.province_id) * 100, 2) as perc
FROM temperature t
JOIN provinces p ON t.province_id = p.province_id
WHERE t.date >= '2000-01-01' AND t.date <= CURRENT_DATE
GROUP BY p.province_id, p.name, range_temp
ORDER BY p.name, 
    CASE range_temp
        WHEN '< 0°C' THEN 1
        WHEN '0-10°C' THEN 2
        WHEN '10-20°C' THEN 3
        WHEN '20-25°C' THEN 4
        WHEN '25-30°C' THEN 5
        WHEN '30-35°C' THEN 6
        WHEN '35-40°C' THEN 7
        ELSE 8
    END;

-- ===========================================================================
-- REFRESH MATERIALIZED VIEWS
-- ===========================================================================

REFRESH MATERIALIZED VIEW CONCURRENTLY kpi_annual_by_municipality;
REFRESH MATERIALIZED VIEW CONCURRENTLY kpi_annual_by_province;

-- ============================================================================
-- Fine queries
-- ============================================================================

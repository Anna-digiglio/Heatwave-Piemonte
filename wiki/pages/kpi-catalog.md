# Catalogo KPI

**Sorgenti**: `README.md`, `sql/01_init_database.sql` (tabella `kpi`, viste
materializzate), `config.yaml` (`processing.temperature_thresholds`)

| KPI | Definizione | Dove è calcolato oggi |
|---|---|---|
| Temperatura media annuale | `AVG(temp_mean)` per anno/provincia/comune | Vista materializzata `kpi_annual_by_*`; colonna `kpi.temp_mean_annual` (non ancora popolata da codice Python) |
| Temperatura massima annuale | `MAX(temp_max)` | Idem |
| Giorni >30°C | `COUNT(*) FILTER (WHERE temp_max > 30)` | Idem — soglia da `processing.temperature_thresholds.extreme_heat_1` |
| Giorni >35°C | `COUNT(*) FILTER (WHERE temp_max > 35)` | Idem — soglia `extreme_heat_2` |
| Giorni >40°C | `COUNT(*) FILTER (WHERE temp_max > 40)` | Idem — soglia `extreme_heat_3` |
| Durata media ondate di calore | `AVG(duration_days)` da `heatwave_events` | ✅ `src/analysis/heatwave_stats.py` (`summary_by_municipality`), eseguito il 2026-07-15 |
| Trend per provincia (decennale) | Variazione °C ogni 10 anni | ✅ `src/analysis/trend_analysis.py` (Mann-Kendall + regressione lineare), eseguito il 2026-07-15 — vedi [Analisi Statistica](statistical-analysis.md); anche `sql/02_common_queries.sql` query #2/#3 |
| Variazione % vs periodo iniziale | `(temp_recente - temp_iniziale) / temp_iniziale * 100` | `sql/02_common_queries.sql` query #2 |
| Anomalia termica | vs baseline climatica 1961-1990 | Colonna `kpi.annual_anomaly` — **baseline non disponibile nel dataset** (si parte dal 2000): da decidere come approssimare (es. media 2000-2009 come proxy). Non ancora implementata |
| Intensità ondata di calore | `(max_temp - threshold) * duration` | ✅ Colonna `heatwave_events.intensity_index`, popolata da `src/analysis/heatwave_stats.py` (`backfill_intensity_and_mean_temp`), eseguito il 2026-07-15 |

## Nota di disegno

I KPI hanno **due percorsi di calcolo paralleli** nel modello dati attuale:
le viste materializzate (`kpi_annual_by_municipality/province`, pure SQL,
ricalcolate al bisogno) e la tabella `kpi` (pensata per essere popolata da
uno step Python della pipeline, con `version` per tracciare ricalcoli). Nessun
codice Python popola ancora la tabella `kpi` — `src/analysis/` (vedi
[Analisi Statistica](statistical-analysis.md)) oggi legge dalle viste
materializzate e scrive i propri risultati in CSV sotto `output/`, non
nella tabella `kpi`. Le viste materializzate restano l'unica fonte SQL
diretta di KPI. Vedi [Stato del Progetto](project-status.md).

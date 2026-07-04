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
| Durata media ondate di calore | `AVG(duration_days)` da `heatwave_events` | Popolabile dopo `identify_heatwaves()` (vedi [Modello Dati](data-model.md)), nessuna query di aggregazione ancora scritta |
| Trend per provincia (decennale) | Variazione °C ogni 10 anni | `sql/02_common_queries.sql` query #2/#3 (regressione/confronto decadi) |
| Variazione % vs periodo iniziale | `(temp_recente - temp_iniziale) / temp_iniziale * 100` | `sql/02_common_queries.sql` query #2 |
| Anomalia termica | vs baseline climatica 1961-1990 | Colonna `kpi.annual_anomaly` — **baseline non disponibile nel dataset** (si parte dal 2000): da decidere come approssimare (es. media 2000-2009 come proxy) |
| Intensità ondata di calore | `(max_temp - threshold) * duration` | Colonna `heatwave_events.intensity_index`, calcolo lasciato a query/ETL a valle di `identify_heatwaves()` |

## Nota di disegno

I KPI hanno **due percorsi di calcolo paralleli** nel modello dati attuale:
le viste materializzate (`kpi_annual_by_municipality/province`, pure SQL,
ricalcolate al bisogno) e la tabella `kpi` (pensata per essere popolata da
uno step Python della pipeline, con `version` per tracciare ricalcoli). Nessun
codice Python popola ancora `kpi` — finché non viene scritto, le viste
materializzate sono l'unica fonte di KPI realmente interrogabile. Vedi
[Stato del Progetto](project-status.md).

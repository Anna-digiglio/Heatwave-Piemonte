# Mappe GIS (QGIS)

**Sorgenti**: `README.md`, `docs/ROADMAP.md`

Stato: **nessun progetto QGIS esiste ancora** — `qgis_projects/` è vuota. Le
mappe seguenti sono pianificate, non implementate.

| Mappa | Descrizione | Dati necessari |
|---|---|---|
| Temperatura media per provincia | Coropletica su poligoni provincia | `provinces.geometry` + `kpi_annual_by_province` |
| Giorni >35°C | Coropletica/heatmap dei giorni di caldo intenso | Idem, colonna `days_gt_35c` |
| Hotspot climatici | Zone ad alta vulnerabilità (es. da clustering K-means, vedi [Concetti](concepts.md)) | `municipalities.geometry` + risultati clustering (non ancora calcolati) |
| Evoluzione temporale | Animazione 2000-2026 (time slider QGIS o serie di frame) | `temperature` per comune/anno completa |
| Heatwave Index | Composito intensità/frequenza ondate | `heatwave_events.intensity_index` aggregato per zona |

## Prerequisiti mancanti prima di poter costruire queste mappe

1. `municipalities` deve essere popolata con geometrie reali (oggi vuota —
   serve il download ISTAT, vedi [Fonti Dati](data-sources.md))
2. `temperature` deve contenere dati reali (oggi 1 riga di test, vedi
   [Stato del Progetto](project-status.md))
3. Le viste `kpi_annual_by_*` vanno quindi popolate/aggiornate (`REFRESH
   MATERIALIZED VIEW`)

File previsti: `qgis_projects/temperature_heatmap.qgz`,
`hotspot_analysis.qgz`, `evolution_animation.qgz` (nomi da `PROJECT_SUMMARY.md`).

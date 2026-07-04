# Dashboard Streamlit

**Sorgenti**: `README.md`, `PROJECT_SUMMARY.md`, `config.yaml` (sezione `dashboard`)

Stato: **non implementata** — `dashboard/` è vuota, nessun `app.py`.

## Struttura pianificata (da `PROJECT_SUMMARY.md`)

```
dashboard/
├── app.py                          # entry point
├── pages/
│   ├── 01_home.py                  # overview & KPI
│   ├── 02_temporal_analysis.py     # trend e serie temporali
│   ├── 03_spatial_analysis.py      # mappe interattive
│   ├── 04_kpi_detail.py            # KPI dettagliati
│   └── 05_download.py              # export dati
└── components/
    ├── charts.py, maps.py, queries.py
```

Configurazione già presente in `config.yaml`: porta 8501, titolo, tema
`light`, `max_upload_size` 200 MB.

## Dipendenze da avere pronte prima di costruirla

- Database popolato con dati reali ([Stato del Progetto](project-status.md))
- KPI calcolabili (viste materializzate o tabella `kpi`, vedi
  [Catalogo KPI](kpi-catalog.md))
- Se si vogliono mappe interattive nella dashboard (Folium/Plotly), serve
  `municipalities.geometry` popolata (vedi [Fonti Dati](data-sources.md))

Fino a quel momento, la dashboard non ha dati reali da mostrare oltre alle
8 province seed e al singolo record di test.

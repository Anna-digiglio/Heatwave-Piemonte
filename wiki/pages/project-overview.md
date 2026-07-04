
# Panoramica del progetto

**Sorgenti**: `README.md`, `PROJECT_SUMMARY.md`

Heatwave Piemonte è un progetto portfolio (Data Engineering + Data Science +
GIS) che analizza l'evoluzione delle temperature e delle ondate di calore nei
comuni e nelle province piemontesi dal 2000 a oggi. È pensato per dimostrare
competenze in Python, SQL, ETL, PostGIS, QGIS e Business Intelligence a un
livello intermedio, realistico per un percorso Data Manager for BI Software
Developer (ITS) con base in Scienze Naturali.

## Domande di ricerca

1. Le giornate con temperature estreme sono aumentate nel tempo?
2. Quali province mostrano i maggiori incrementi?
3. Esistono differenze territoriali significative?
4. È possibile identificare aree maggiormente vulnerabili alle ondate di calore?

Queste quattro domande sono il filo conduttore di tutto il progetto: guidano lo
schema dati ([Modello Dati](data-model.md)), i KPI ([Catalogo KPI](kpi-catalog.md)),
le query ([Query SQL](sql-queries.md)) e le mappe GIS previste ([Mappe GIS](gis-maps.md)).

## Stack tecnologico (dichiarato)

- **Python**: pandas, numpy, geopandas, sqlalchemy, plotly, matplotlib
- **Database**: PostgreSQL + PostGIS
- **GIS**: QGIS, Folium, Shapely, Pyproj
- **Dashboard**: Streamlit
- **Versionamento**: Git/GitHub

Per lo stato reale di implementazione di ciascun pezzo vedi
[Stato del Progetto](project-status.md) — i documenti README/PROJECT_SUMMARY
descrivono l'obiettivo finale, non necessariamente ciò che esiste oggi nel
codice.

## Fonti dati

Vedi [Fonti Dati](data-sources.md) per il dettaglio implementativo di ciascuna
fonte (Open-Meteo, Copernicus ERA5, ARPA Piemonte, ISTAT, OpenStreetMap).

## Pianificazione

Il piano originale è una roadmap di 3 settimane (vedi `docs/ROADMAP.md`):
Settimana 1 Setup & Acquisizione, Settimana 2 ETL & Analisi, Settimana 3
Visualizzazione & Deployment. Stato aggiornato in [Stato del Progetto](project-status.md).

# Fonti dati

**Sorgenti**: `src/data_acquisition/download_data.py`, `config.yaml` (sezione `data_sources`)

| Fonte | Stato codice | Abilitata di default | Note |
|---|---|---|---|
| **Open-Meteo** | Implementata (`WeatherDataDownloader`) | Sì | Nessuna API key. Endpoint `archive-api.open-meteo.com/v1/archive`. Scarica `temperature_2m_max/min/mean` e `precipitation_sum` giornalieri per gli 8 capoluoghi di provincia (coordinate hardcoded in `PIEMONTE_REGIONS`). |
| **Copernicus ERA5** | Implementata (`CopernicusERA5Downloader`) | Sì (in `config.yaml`) | Richiede libreria `cdsapi` (in `requirements.txt`) e variabile d'ambiente `CDS_KEY`. Vedi bug noto sotto. |
| **ARPA Piemonte** | Implementata (`ArpaPiemonteDownloader`) | No | Download CSV da URL configurato in `config.yaml`, per validazione/calibrazione locale. |
| **ISTAT** | Implementata (`IstatGeodataDownloader`) | No | Confini amministrativi comuni/province in GeoJSON, via `geopandas` se disponibile. |
| **OpenStreetMap** | Implementata (`OpenStreetMapDownloader`) | No | Confine regionale via Nominatim (`nominatim.openstreetmap.org`), richiede `User-Agent`. |

Le fonti da scaricare si scelgono con il flag `--sources` di
`download_data.py` (default `open_meteo,copernicus`; `all` abilita tutte).

## Bug noto: `CopernicusERA5Downloader._create_cds_client`

In `download_data.py` il metodo `_create_cds_client` ha annotazione di ritorno
`-> cdsapi.Client` ma `cdsapi` viene importato solo *dentro* il corpo del
metodo, non a livello di modulo. In Python senza
`from __future__ import annotations`, questo causa un `NameError` alla
definizione della classe (l'annotazione viene valutata subito), quindi
**l'intero modulo `download_data.py` non si importa** finché non si sistema
questo punto. Da correggere prima di eseguire qualunque script che fa
`import src.data_acquisition.download_data`.

## Dati realmente scaricati oggi

Solo `data/raw/test_open_meteo_torino.csv`: 1 riga di test (Torino,
2020-06-01). Nessun download massivo 2000-2026 è stato ancora eseguito — i
numeri "1.7M record" citati in README/PROJECT_SUMMARY sono una stima
pianificata, non un dato reale. Vedi [Stato del Progetto](project-status.md).

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

## Bug risolto: `CopernicusERA5Downloader._create_cds_client`

**Fixato il 2026-07-04.** Il metodo `_create_cds_client` aveva annotazione di
ritorno `-> cdsapi.Client`, ma `cdsapi` viene importato solo *dentro* il corpo
del metodo, non a livello di modulo. In Python, senza
`from __future__ import annotations`, le annotazioni vengono valutate subito
alla definizione della classe — quindi il `NameError` scattava
**all'import del modulo stesso**, prima ancora di chiamare qualunque
funzione. Fix: annotazione trasformata in forward reference stringa e resa
opzionale — `-> Optional["cdsapi.Client"]` (il metodo può restituire `None`
se `cdsapi` non è installato). Nessun nuovo import necessario (`Optional`
era già importato).

## Bug noto: formato di logging incompatibile con loguru

`config.yaml` (`logging.format`) usa la sintassi `%(asctime)s - %(name)s -
%(levelname)s - %(message)s`, tipica del modulo `logging` di Python standard.
Ma `src/utils/logger.py` usa **loguru**, che si aspetta placeholder in stile
`{time} {level} {message}`. Loguru non solleva errori: stampa la stringa di
formato letteralmente, su ogni riga, senza sostituire nulla — quindi sia la
console che `logs/heatwave_piemonte.log` sono oggi illeggibili (nessun
messaggio reale, solo la stringa di formato ripetuta). Non blocca
l'esecuzione degli script ma nasconde tutti i log/errori reali. Da correggere
in `config.yaml` (sezione `logging.format`) usando la sintassi loguru.

## Bug noto/gestito: rate limit "al minuto" di Open-Meteo

L'endpoint `archive-api.open-meteo.com/v1/archive` applica un limite di
richieste al minuto più stringente di quanto lascia intendere il campo
`rate_limit: 10000` (giornaliero) in `config.yaml` — richieste pesanti (26
anni di dati giornalieri) in sequenza ravvicinata ricevono `429 Too Many
Requests`. Riscontrato durante il primo download reale (3/8 province
fallite silenziosamente). Fix applicato in
`WeatherDataDownloader.download_historical_data`: retry con backoff
esponenziale (rispetta l'header `Retry-After` se presente, max 5 tentativi)
+ sleep tra le regioni portato da 1s a 3s in `download_all_regions`.

## Dati realmente scaricati oggi

**Download reale eseguito il 2026-07-04**: `data/raw/temperature_data.csv`,
75.976 righe — 8 province × 9.497 giorni (2000-01-01 → 2025-12-31), nessun
valore nullo. Il 2026 non è incluso (l'API storica non accetta date future
oltre il giorno corrente; si potrà aggiungere un aggiornamento incrementale
in seguito). I numeri "1.7M record" citati in README/PROJECT_SUMMARY restano
una stima pianificata (verosimilmente basata su dati orari, non giornalieri)
— il dataset reale a cadenza giornaliera per 8 stazioni è strutturalmente
più piccolo. Vedi [Stato del Progetto](project-status.md).

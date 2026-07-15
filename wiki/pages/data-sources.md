# Fonti dati

**Sorgenti**: `src/data_acquisition/download_data.py`, `config.yaml` (sezione `data_sources`)

| Fonte | Stato codice | Abilitata di default | Note |
|---|---|---|---|
| **Open-Meteo** | Implementata (`WeatherDataDownloader`) | Sì | Nessuna API key. Endpoint `archive-api.open-meteo.com/v1/archive`. Scarica `temperature_2m_max/min/mean` e `precipitation_sum` giornalieri. Due modalità: `download_historical_data(region)` per gli 8 capoluoghi hardcoded in `PIEMONTE_REGIONS`, e (dal 2026-07-15) `download_for_coordinates(name, lat, lon)` per coordinate arbitrarie — usata per estendere la copertura ad altri comuni, vedi sotto. |
| **Copernicus ERA5** | Implementata (`CopernicusERA5Downloader`) | Sì (in `config.yaml`) | Richiede libreria `cdsapi` (in `requirements.txt`) e variabile d'ambiente `CDS_KEY`. Vedi bug noto sotto. |
| **ARPA Piemonte** | Implementata (`ArpaPiemonteDownloader`) | No | Download CSV da URL configurato in `config.yaml`, per validazione/calibrazione locale. |
| **ISTAT** | Implementata (`IstatGeodataDownloader`) | No | Confini amministrativi comuni in shapefile (zip), via `geopandas`. `download_municipalities()` riscritto il 2026-07-04 (vedi sotto); `download_provinces()`/`provinces_url` non ancora verificati (province già seedate come punti in `sql/01_init_database.sql`). |
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

## Bug risolto: formato di logging incompatibile con loguru

**Fixato il 2026-07-15.** `config.yaml` (`logging.format`) usava la sintassi
`%(asctime)s - %(name)s - %(levelname)s - %(message)s`, tipica del modulo
`logging` di Python standard. Ma `src/utils/logger.py` usa **loguru**, che
si aspetta placeholder in stile `{time} {level} {message}`. Loguru non
sollevava errori: stampava la stringa di formato letteralmente, su ogni
riga, senza sostituire nulla — quindi sia la console che
`logs/heatwave_piemonte.log` sono stati illeggibili per gran parte del
progetto (nessun messaggio reale, solo la stringa di formato ripetuta),
nascondendo log/errori reali durante il debug di molte sessioni precedenti.
Fix: `logging.format` in `config.yaml` allineato alla sintassi loguru
(`{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} -
{message}`), lo stesso formato già usato come fallback di default in
`logger.py` — quindi ora config e codice sono coerenti. Verificato con un
test diretto: messaggi formattati correttamente sia a schermo sia su file.

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

## `IstatGeodataDownloader.download_municipalities` — riscritta il 2026-07-04

L'URL in `config.yaml` (`data_sources.istat.municipalities_url`) puntava a
una pagina HTML di archivio (`istat.it/it/archivio/222527`), non a un file
scaricabile. Trovato (via ricerca web, verificato con richiesta HTTP diretta)
l'URL reale del dataset ufficiale ISTAT dei confini amministrativi:
`https://www.istat.it/storage/cartografia/confini_amministrativi/generalizzati/2026/Limiti01012026_g.zip`
(shapefile, ~10MB, aggiornato al 01/01/2026). Il metodo: scarica lo zip
(con cache locale in `data/external/istat_confini/`), lo estrae, legge
`Com*_WGS84.shp` con `geopandas`, filtra `COD_REG == 1` (Piemonte, 1180
comuni), calcola `area_km2` nel CRS proiettato originale (UTM32, metri — non
dopo la riproiezione in 4326, dove i gradi non sono unità di superficie),
riproietta in EPSG:4326, e salva sia `data/external/istat_municipalities.geojson`
sia `data/external/municipalities.csv` (quest'ultimo con geometria in WKT,
pronto per `DatabaseLoader.insert_municipalities`, vedi [ETL](etl-pipeline.md)).

**Bug di encoding, introdotto il 2026-07-04 e corretto solo il 2026-07-15**:
i file ISTAT non hanno un `.cpg` che dichiari l'encoding del `.dbf`. Il fix
originario usava `encoding='cp1252'`, verificato all'epoca stampando un nome
a terminale ("Agliè" sembrava corretto) — ma quella verifica era ingannevole:
il terminale stava mostrando un doppio mojibake che *sembrava* giusto per
coincidenza. Verificando a livello di byte
(`nome.encode('utf-8')`) si è scoperto che **`cp1252` produceva una doppia
codifica UTF-8** per ogni nome con lettere accentate (es. "Agliè" diventava
`b'Agli\xc3\x83\xc2\xa8'` invece del corretto `b'Agli\xc3\xa8'`), corrompendo
**28 dei 1180 comuni piemontesi** nel database reale (tutti quelli con
caratteri non-ASCII nel nome, il 100% di essi). Il file `.dbf` è in realtà
codificato in **UTF-8**: `encoding='utf-8'` esplicito dà il risultato
corretto. Corretti sia lo script (`download_data.py`) sia i 28 nomi già
presenti nel database (via `UPDATE ... WHERE istat_code = ...`, chiave
stabile non affetta dal bug) sia `data/external/municipalities.csv`
(rigenerato). Lezione: **non fidarsi della resa a terminale per verificare
encoding** — controllare sempre i byte espliciti.

**Curiosità/trappola**: uno dei 1180 comuni (istat_code `001168`, provincia
di Torino) si chiama letteralmente **"None"** (Pinerolese, noto per
l'asparago). Chi rilegge `municipalities.csv` con `pandas.read_csv` di
default lo trasforma in `NaN` (pandas tratta la stringa `"None"` come valore
mancante) — va sempre letto con `keep_default_na=False`.

## `download_extra_municipalities.py` — copertura estesa a 44 comuni (2026-07-15)

Motivazione: Moran's I e il clustering K-means (vedi
[Analisi Statistica](statistical-analysis.md)) erano statisticamente deboli
con solo 8 unità spaziali. `src/data_acquisition/download_extra_municipalities.py`:

1. **Selezione spaziale**: per ciascuna delle 8 province, campionamento
   "farthest-point" (greedy, massimizza la distanza minima dai punti già
   scelti) a partire dal capoluogo già scaricato — sceglie comuni che
   coprono aree diverse della provincia (montagna, pianura, confini),
   non i più vicini al capoluogo. 36 comuni extra selezionati (proporzionali
   alla dimensione di ciascuna provincia: 9 per Torino, 7 per Cuneo, ...,
   2 per Biella/Verbano-Cusio-Ossola).
2. **Download**: `WeatherDataDownloader.download_for_coordinates()`
   (nuovo metodo, refactoring di `download_historical_data()` per accettare
   coordinate arbitrarie, non solo gli 8 capoluoghi hardcoded).
3. Salvataggio in `data/raw/temperature_data_extra.csv`.

**Esecuzione reale**: 31/36 comuni scaricati al primo tentativo; 5 falliti
per un errore di connessione TLS transitorio (`ConnectionResetError`,
non un `429` — il retry-on-429 esistente non copriva questo caso), riscaricati
con una seconda passata mirata. Risultato finale: 36/36 comuni, 341.892
righe, nessun dato mancante.

## Dati realmente scaricati/caricati (2026-07-04 → 2026-07-15)

- `data/raw/temperature_data.csv`: 75.976 righe — 8 province × 9.497 giorni
  (2000-01-01 → 2025-12-31), nessun valore nullo. Il 2026 non è incluso
  (l'API storica non accetta date future oltre il giorno corrente). I numeri
  "1.7M record" citati in README/PROJECT_SUMMARY restano una stima
  pianificata (verosimilmente basata su dati orari, non giornalieri).
- `data/raw/temperature_data_extra.csv` (2026-07-15): 341.892 righe — 36
  comuni extra × 9.497 giorni, stesso periodo.
- `data/external/municipalities.csv` + tabella `municipalities` nel DB:
  1180 comuni piemontesi reali, geometrie tutte valide (`ST_IsValid`),
  nomi corretti (encoding fix del 2026-07-15). `population` ed
  `elevation_m` restano `NULL` (non presenti nello shapefile dei confini,
  serve un dataset ISTAT demografico separato — non fatto in questa
  sessione, l'utente ha dato priorità all'estensione delle temperature).
- Tabella `temperature`: **417.868 righe, 44 comuni** (8 capoluoghi +
  36 extra), 2000-2025.

Vedi [Stato del Progetto](project-status.md).

# Fonti dati

**Sorgenti**: `src/data_acquisition/download_data.py`, `config.yaml` (sezione `data_sources`)

| Fonte | Stato codice | Abilitata di default | Note |
|---|---|---|---|
| **Open-Meteo** | Implementata (`WeatherDataDownloader`) | Sì | Nessuna API key. Endpoint `archive-api.open-meteo.com/v1/archive`. Scarica `temperature_2m_max/min/mean` e `precipitation_sum` giornalieri. Due modalità: `download_historical_data(region)` per gli 8 capoluoghi hardcoded in `PIEMONTE_REGIONS`, e (dal 2026-07-15) `download_for_coordinates(name, lat, lon)` per coordinate arbitrarie — usata per estendere la copertura ad altri comuni, vedi sotto. |
| **Copernicus ERA5** | Implementata (`CopernicusERA5Downloader`) | Sì (in `config.yaml`) | Richiede libreria `cdsapi` (in `requirements.txt`) e variabile d'ambiente `CDS_KEY`. Vedi bug noto sotto. |
| **ARPA Piemonte** | Implementata (`ArpaPiemonteDownloader`) | No | Download CSV da URL configurato in `config.yaml`, per validazione/calibrazione locale. |
| **ISTAT** | Implementata (`IstatGeodataDownloader`) | No | Confini amministrativi comuni in shapefile (zip), via `geopandas`. `download_municipalities()` riscritto il 2026-07-04 (vedi sotto); `download_provinces()`/`provinces_url` non ancora verificati (province già seedate come punti in `sql/01_init_database.sql`). |
| **OpenStreetMap** | Implementata (`OpenStreetMapDownloader`) | No | Confine regionale via Nominatim (`nominatim.openstreetmap.org`), richiede `User-Agent`. |
| **Open-Meteo Elevation API** | Implementata (`src/data_acquisition/fetch_elevation.py`) | Solo one-off | Endpoint separato `api.open-meteo.com/v1/elevation` (stessa piattaforma, nessuna API key). Non fa parte del flusso `download_data.py` regolare: script a sé, eseguito una volta il 2026-07-15 per popolare `municipalities.elevation_m` dei 44 comuni con dati di temperatura reali (coordinate = centroide della geometria, letto da PostGIS). Vedi [Modello Dati](data-model.md). |

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

## Scoperto il limite giornaliero di Open-Meteo (2026-07-17)

Richiesta dell'utente: coprire tutti i 1180 comuni piemontesi e portare i
dati fino ad oggi. Il bug noto sopra ("rate limit al minuto") non era
tutta la storia — esiste anche un **limite giornaliero** di richieste,
scoperto nel modo peggiore:

1. **Tentativo 1 (256 comuni extra, obiettivo 300 totali)**: dopo **~5h40**
   di download continuo, solo 37/256 comuni riusciti e 123 falliti
   definitivamente (rate limit sempre più severo). Interrotto il processo
   — e siccome `download_all()` collezionava tutto in una lista Python e
   scriveva il CSV **solo alla fine**, l'interruzione ha fatto perdere
   **tutto** il lavoro delle 5h40 (nessun file scritto su disco).
2. **Tentativo 2 (56 comuni, obiettivo ridotto a 100 totali)**: bloccato
   **immediatamente** — anche una singola richiesta di test isolata (senza
   nessun batch in corso) restituiva `429`. Il corpo della risposta ha
   rivelato la causa reale: `{"error":true,"reason":"Daily API request
   limit exceeded. Please try again tomorrow."}` — un limite **giornaliero**,
   non "al minuto": la finestra di 5h40 sprecata il giorno prima aveva
   già esaurito la quota per l'intera giornata.
3. **Fix strutturale prima di riprovare**: salvataggio **incrementale** —
   ogni comune scaricato con successo viene subito appeso al CSV
   (`mode='a'`), non solo a fine esecuzione — sia in
   `download_extra_municipalities.py` sia nel nuovo
   `update_recent_data.py`. Un'interruzione futura, per qualunque motivo,
   non fa più perdere il lavoro già fatto.
4. **Giorno successivo (2026-07-17)**: quota resettata (verificato con una
   richiesta di test leggera prima di lanciare qualunque batch). Su
   richiesta esplicita dell'utente, lotti prudenti e **parametrici**
   (`--count`, non più un target fisso nel codice) invece di un unico
   tentativo grande. Un lotto di 50 comuni ha **rivelato empiricamente la
   soglia**: si blocca sempre intorno a **19-20 richieste "pesanti"**
   (26 anni di storico ciascuna) — dopo il 19° comune, ogni tentativo
   successivo falliva con "rate limit persistente dopo 5 tentativi".
   Fermato subito (nessuna perdita, grazie al fix del punto 3): **19
   comuni aggiuntivi salvati con successo** (44 → 63 comuni totali).
5. **Scoperta interessante**: il limite sembra legato al **volume di dati
   per richiesta**, non a un conteggio piatto di richieste. Il giorno
   dopo, un aggiornamento "delta" (`update_recent_data.py`, richieste
   piccole di ~198 giorni ciascuna invece di 26 anni interi) ha
   completato **tutti e 63 i comuni in un solo lotto, zero errori** — ben
   oltre la soglia di ~19-20 vista con le richieste "pesanti". Non è stato
   verificato in modo rigoroso (nessuna documentazione ufficiale
   consultata sul funzionamento esatto della quota), ma è coerente con i
   fatti osservati: richieste piccole "costano" meno quota di richieste
   grandi.

**Risultato netto**: 44 → **63 comuni** (19 aggiuntivi, stesso
campionamento "farthest-point" per copertura spaziale), e **tutti i 63
comuni portati fino a oggi** (non più fermi al 31/12/2025) tramite il
delta incrementale. Non i 1180 comuni completi richiesti inizialmente, ma
un incremento reale ottenuto in modo sostenibile — vedi
[Stato del Progetto](project-status.md) per la sintesi della decisione
presa insieme all'utente (costi/rischi di 1180 comuni spiegati prima di
ridimensionare l'obiettivo).

## `update_recent_data.py` — estensione a oggi per tutti i comuni (2026-07-17)

Nuovo script: a differenza di `download_extra_municipalities.py` (comuni
mai scaricati prima), questo estende **comuni già presenti** in
`temperature` fino alla data più recente disponibile. Per ciascun comune,
calcola `MAX(date)` già in DB e scarica solo il **delta** (dal giorno
successivo a oggi) — mai l'intero storico, evitando duplicati (nessun
vincolo di unicità `(municipality_id, date)` in `temperature`: un doppio
insert sullo stesso periodo creerebbe righe duplicate silenziosamente).
Stesso fix di salvataggio incrementale di `download_extra_municipalities.py`.

**Esecuzione reale**: 63/63 comuni aggiornati con successo, zero errori —
44 comuni con un delta di ~198 giorni (dal 1/1/2026), 19 comuni (appena
scaricati) con un delta di un solo giorno. 8.731 righe totali.

## Dati realmente scaricati/caricati (2026-07-04 → 2026-07-17)

- `data/raw/temperature_data.csv`: 75.976 righe — 8 province × 9.497 giorni
  (2000-01-01 → 2025-12-31), nessun valore nullo. Il 2026 non è incluso
  (l'API storica non accetta date future oltre il giorno corrente). I numeri
  "1.7M record" citati in README/PROJECT_SUMMARY restano una stima
  pianificata (verosimilmente basata su dati orari, non giornalieri).
- `data/raw/temperature_data_extra.csv`: 526.078 righe — cresciuto da 36 a
  **55 comuni extra** (2026-07-15 → 2026-07-17), stesso periodo di base
  (2000 → 16/07/2026 per i 19 comuni più recenti).
- `data/raw/temperature_data_recent.csv` (2026-07-17): 8.731 righe — delta
  fino a oggi per tutti i 63 comuni (vedi `update_recent_data.py` sopra).
- `data/external/municipalities.csv` + tabella `municipalities` nel DB:
  1180 comuni piemontesi reali, geometrie tutte valide (`ST_IsValid`),
  nomi corretti (encoding fix del 2026-07-15). `elevation_m` popolato solo
  per i 63 comuni con dati di temperatura (Open-Meteo Elevation API);
  `population` popolato per tutti i 1180 comuni il 2026-07-16 (vedi
  sezione dedicata sotto).
- Tabella `temperature`: **610.785 righe, 63 comuni** (8 capoluoghi +
  55 extra), dal 2000 **fino a oggi** (non più fermo al 31/12/2025).

## `download_population.py` — popolazione residente reale per tutti i 1180 comuni (2026-07-16)

Motivazione: covariata esplicativa mancante per il paper scientifico (vedi
[Articolo scientifico](paper-scientifico.md)) — `municipalities.population`
era `NULL` dall'inizio del progetto.

**Percorso trovato dopo un'indagine con diversi vicoli ciechi** (dettaglio
completo in [Articolo scientifico](paper-scientifico.md)): l'API SDMX nuova
di ISTAT (`esploradati.istat.it`) ha la struttura giusta (stessi codici
`istat_code`) ma non restituisce osservazioni per il dataset
`DCIS_POPORESBIL1`; il vecchio portale `dati.istat.it` è dismesso (redirect
a un avviso). **`demo.istat.it`** è invece un sistema separato e attivo, con
un file ZIP scaricabile per provincia
(`https://demo.istat.it/data/posas/POSAS_{anno}_it_{codice}_{nome}.zip`,
nessuna chiave/account), CSV con una riga per comune/età/sesso — la riga
con età=999 è il totale per comune. Verificato che i codici comune nel CSV
coincidono esattamente con `municipalities.istat_code`.

**Bug incontrato durante l'implementazione**: la colonna età viene letta da
pandas come stringa (non intero, per via di alcune righe non puramente
numeriche nel file), quindi il filtro sulla riga di totale va scritto come
confronto a stringa (`== '999'`), non a intero (`== 999`, che restituiva
sempre 0 righe) — scoperto testando prima su un file scaricato a mano
prima di lanciare lo script su tutte le 8 province.

**Risultato reale**: eseguito su tutte le 8 province, **1180/1180 comuni
aggiornati** (non solo i comuni con temperatura) — 312 Torino, 247 Cuneo,
187 Alessandria, 117 Asti, 87 Novara, 82 Vercelli, 74 Biella, 74
Verbano-Cusio-Ossola (somma esatta con l'allocazione già usata in
`download_extra_municipalities.py`). Dato: stima al 1° gennaio 2026.
Valori verificati a campione: Torino 855.654 ab. (densità 6580 ab/km²),
Alessandria 93.409 ab., Cuneo 55.747 ab., Bardonecchia 2.853 ab. (densità
21.6 ab/km²), Formazza 410 ab. (densità 3.1 ab/km²) — gradiente
pianura/alpino coerente con quanto già trovato in
[Analisi statistica](statistical-analysis.md).

## CORINE Land Cover 2018 — uso del suolo per tutti i 1180 comuni (2026-07-16)

Motivazione: seconda covariata esplicativa mancante per il paper scientifico
(vedi [Articolo scientifico](paper-scientifico.md)), dopo la popolazione.

**Decisione presa con l'utente**: niente API CLMS con token JWT (troppo
complessa per un dataset che si aggiorna ogni ~6 anni) — account EU Login
gratuito su `land.copernicus.eu`, poi download manuale via "Download by
area" (ritaglio sul Piemonte invece di tutta Europa), formato vettoriale
GeoPackage.

**Due tentativi prima del file giusto**: il primo file fornito
dall'utente (`U2018_CLC2018_V2020_20u1_doc/`) era solo documentazione/
legenda (PDF, metadata XML), senza geometrie — cartella eliminata dopo aver
salvato solo `data/external/clc_legend.csv` (tabella dei codici CLC, utile
per la categorizzazione). Il file dati vero (`U2018_CLC2018_V2020_20u1.gpkg`,
136 MB, EPSG:3035, 52.794 poligoni, campo `Code_18` = codice CLC a 3 cifre)
è arrivato al secondo giro.

**Metodo**: `src/data_acquisition/process_land_cover.py` — overlay
geopandas tra le geometrie di tutti i 1180 comuni (riproiettate in
EPSG:3035, la stessa proiezione equal-area di CLC, per calcoli di area
corretti — stessa lezione già imparata per `area_km2`) e i poligoni CLC.
Percentuali aggregate alle 5 categorie di Livello 1 (primo carattere del
codice a 3 cifre: 1=urbano, 2=agricolo, 3=forestale/seminaturale,
4=zone umide, 5=corpi idrici; i codici speciali 990/995/999 finiscono in
"other"). Overlay completo sui 1180 comuni eseguito in ~16 secondi.
Risultati in `municipality_land_cover` (vedi
[Modello Dati](data-model.md)).

**Nota temporale**: CLC2018 è uno scatto del 2018, usato come covariata
statica contro temperature 2000-2025 e popolazione stimata 2026 — pratica
comune per l'uso del suolo (cambia lentamente, un'epoca CLC copre ~6 anni),
ma da dichiarare esplicitamente come limite nel paper, non da nascondere.

Vedi [Stato del Progetto](project-status.md).

# Fonti dati

**Sorgenti**: `src/data_acquisition/download_data.py`, `config.yaml` (sezione `data_sources`)

| Fonte | Stato codice | Abilitata di default | Note |
|---|---|---|---|
| **Open-Meteo** | Implementata (`WeatherDataDownloader`) | Sì | Nessuna API key. Endpoint `archive-api.open-meteo.com/v1/archive`. Scarica `temperature_2m_max/min/mean` e `precipitation_sum` giornalieri. Due modalità: `download_historical_data(region)` per gli 8 capoluoghi hardcoded in `PIEMONTE_REGIONS`, e (dal 2026-07-15) `download_for_coordinates(name, lat, lon)` per coordinate arbitrarie — usata per estendere la copertura ad altri comuni, vedi sotto. |
| **Copernicus ERA5** | Implementata (`CopernicusERA5Downloader`) | Sì (in `config.yaml`) | Richiede libreria `cdsapi` (in `requirements.txt`) e variabile d'ambiente `CDS_KEY`. Vedi bug noto sotto. |
| **ARPA Piemonte** | Implementata ma rotta (`ArpaPiemonteDownloader`) | No | L'URL in `config.yaml` (`arpa_piemonte.url`, pagina statica `/dati/climatici`) risponde 404 — mai stato un endpoint dati reale. **API reale trovata via ricerca web il 2026-07-18, non ancora integrata nel codice**, vedi sotto. |
| **ISTAT** | Implementata (`IstatGeodataDownloader`) | No | Confini amministrativi comuni in shapefile (zip), via `geopandas`. `download_municipalities()` riscritto il 2026-07-04 (vedi sotto); `download_provinces()`/`provinces_url` non ancora verificati (province già seedate come punti in `sql/01_init_database.sql`). |
| **OpenStreetMap** | Implementata (`OpenStreetMapDownloader`) | No | Confine regionale via Nominatim (`nominatim.openstreetmap.org`), richiede `User-Agent`. |
| **Open-Meteo Elevation API** | Implementata (`src/data_acquisition/fetch_elevation.py`) | Solo one-off | Endpoint separato `api.open-meteo.com/v1/elevation` (stessa piattaforma, nessuna API key). Non fa parte del flusso `download_data.py` regolare: script a sé, eseguito una volta il 2026-07-15 per popolare `municipalities.elevation_m` dei comuni con dati di temperatura reali (coordinate = centroide della geometria, letto da PostGIS). Vedi [Modello Dati](data-model.md). |

Le fonti da scaricare si scelgono con il flag `--sources` di
`download_data.py` (default `open_meteo,copernicus`; `all` abilita tutte).

## Bug risolti

**`CopernicusERA5Downloader._create_cds_client` (fixato il 2026-07-04)**
Il metodo aveva annotazione di ritorno `-> cdsapi.Client`, ma `cdsapi`
viene importato solo *dentro* il corpo del metodo, non a livello di
modulo. In Python, senza `from __future__ import annotations`, le
annotazioni vengono valutate subito alla definizione della classe — quindi
il `NameError` scattava **all'import del modulo stesso**, prima ancora di
chiamare qualunque funzione. Fix: annotazione trasformata in forward
reference stringa e resa opzionale — `-> Optional["cdsapi.Client"]` (il
metodo può restituire `None` se `cdsapi` non è installato).

**Formato di logging incompatibile con loguru (fixato il 2026-07-15)**
`config.yaml` (`logging.format`) usava la sintassi
`%(asctime)s - %(name)s - %(levelname)s - %(message)s`, tipica del modulo
`logging` di Python standard. Ma `src/utils/logger.py` usa **loguru**, che
si aspetta placeholder in stile `{time} {level} {message}`. Loguru non
sollevava errori: stampava la stringa di formato letteralmente, su ogni
riga, senza sostituire nulla — quindi sia la console che
`logs/heatwave_piemonte.log` sono stati illeggibili per gran parte del
progetto (nessun messaggio reale, solo la stringa di formato ripetuta),
nascondendo log/errori reali durante il debug di molte sessioni
precedenti. Fix: `logging.format` allineato alla sintassi loguru
(`{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} -
{message}`), lo stesso formato già usato come fallback di default in
`logger.py`. Verificato con un test diretto: messaggi formattati
correttamente sia a schermo sia su file.

**Rate limit "al minuto" di Open-Meteo (bug noto/gestito)**
L'endpoint `archive-api.open-meteo.com/v1/archive` applica un limite di
richieste al minuto più stringente di quanto lascia intendere il campo
`rate_limit: 10000` (giornaliero) in `config.yaml` — richieste pesanti (26
anni di dati giornalieri) in sequenza ravvicinata ricevono `429 Too Many
Requests`. Riscontrato durante il primo download reale (3/8 province
fallite silenziosamente). Fix applicato in
`WeatherDataDownloader.download_historical_data`: retry con backoff
esponenziale (rispetta l'header `Retry-After` se presente, max 5
tentativi) + sleep tra le regioni portato da 1s a 3s in
`download_all_regions`. Vedi sotto per il **limite giornaliero**, distinto
e scoperto più tardi.

## `IstatGeodataDownloader.download_municipalities` — riscritta il 2026-07-04

L'URL in `config.yaml` (`data_sources.istat.municipalities_url`) puntava a
una pagina HTML di archivio (`istat.it/it/archivio/222527`), non a un file
scaricabile. Trovato (via ricerca web, verificato con richiesta HTTP
diretta) l'URL reale del dataset ufficiale ISTAT dei confini
amministrativi:
`https://www.istat.it/storage/cartografia/confini_amministrativi/generalizzati/2026/Limiti01012026_g.zip`
(shapefile, ~10MB, aggiornato al 01/01/2026).

**Metodo**: scarica lo zip (con cache locale in
`data/external/istat_confini/`), lo estrae, legge `Com*_WGS84.shp` con
`geopandas`, filtra `COD_REG == 1` (Piemonte, 1180 comuni), calcola
`area_km2` nel CRS proiettato originale (UTM32, metri — non dopo la
riproiezione in 4326, dove i gradi non sono unità di superficie),
riproietta in EPSG:4326, e salva sia
`data/external/istat_municipalities.geojson` sia
`data/external/municipalities.csv` (quest'ultimo con geometria in WKT,
pronto per `DatabaseLoader.insert_municipalities`, vedi
[ETL](etl-pipeline.md)).

> **Bug di encoding, introdotto il 2026-07-04 e corretto solo il
> 2026-07-15**: i file ISTAT non hanno un `.cpg` che dichiari l'encoding
> del `.dbf`. Il fix originario usava `encoding='cp1252'`, verificato
> all'epoca stampando un nome a terminale ("Agliè" sembrava corretto) — ma
> quella verifica era ingannevole: il terminale stava mostrando un doppio
> mojibake che *sembrava* giusto per coincidenza. Verificando a livello di
> byte (`nome.encode('utf-8')`) si è scoperto che **`cp1252` produceva una
> doppia codifica UTF-8** per ogni nome con lettere accentate (es. "Agliè"
> diventava `b'Agli\xc3\x83\xc2\xa8'` invece del corretto
> `b'Agli\xc3\xa8'`), corrompendo **28 dei 1180 comuni piemontesi** nel
> database reale (tutti quelli con caratteri non-ASCII nel nome, il 100%
> di essi). Il file `.dbf` è in realtà codificato in **UTF-8**:
> `encoding='utf-8'` esplicito dà il risultato corretto. Corretti sia lo
> script (`download_data.py`) sia i 28 nomi già presenti nel database (via
> `UPDATE ... WHERE istat_code = ...`, chiave stabile non affetta dal bug)
> sia `data/external/municipalities.csv` (rigenerato). **Lezione**: non
> fidarsi della resa a terminale per verificare encoding — controllare
> sempre i byte espliciti.

> **Curiosità/trappola**: uno dei 1180 comuni (istat_code `001168`,
> provincia di Torino) si chiama letteralmente **"None"** (Pinerolese,
> noto per l'asparago). Chi rilegge `municipalities.csv` con
> `pandas.read_csv` di default lo trasforma in `NaN` (pandas tratta la
> stringa `"None"` come valore mancante) — va sempre letto con
> `keep_default_na=False`.

## `download_extra_municipalities.py` — copertura estesa a 44 comuni (2026-07-15)

**Motivazione**: Moran's I e il clustering K-means (vedi
[Analisi Statistica](statistical-analysis.md)) erano statisticamente
deboli con solo 8 unità spaziali.

`src/data_acquisition/download_extra_municipalities.py`:

1. **Selezione spaziale**: per ciascuna delle 8 province, campionamento
   "farthest-point" (greedy, massimizza la distanza minima dai punti già
   scelti) a partire dal capoluogo già scaricato — sceglie comuni che
   coprono aree diverse della provincia (montagna, pianura, confini), non
   i più vicini al capoluogo. 36 comuni extra selezionati (proporzionali
   alla dimensione di ciascuna provincia: 9 per Torino, 7 per Cuneo, ...,
   2 per Biella/Verbano-Cusio-Ossola).
2. **Download**: `WeatherDataDownloader.download_for_coordinates()`
   (nuovo metodo, refactoring di `download_historical_data()` per
   accettare coordinate arbitrarie, non solo gli 8 capoluoghi hardcoded).
3. Salvataggio in `data/raw/temperature_data_extra.csv`.

**Esecuzione reale**: 31/36 comuni scaricati al primo tentativo; 5 falliti
per un errore di connessione TLS transitorio (`ConnectionResetError`, non
un `429` — il retry-on-429 esistente non copriva questo caso), riscaricati
con una seconda passata mirata. Risultato finale: 36/36 comuni, 341.892
righe, nessun dato mancante.

## API reale ARPA Piemonte trovata (2026-07-18, ricerca web — non ancora integrata nel codice)

**Contesto**: fase 1 del piano paper ([Articolo scientifico](paper-scientifico.md)) —
validare le temperature Open-Meteo (dati di rianalisi/modello) contro
osservazioni di stazione reali — era bloccata dal 2026-07-16 (URL in
`config.yaml` risponde 404, l'unica alternativa nota era l'interfaccia a
mappa `map_meteoweb` o una richiesta manuale via email).

**Trovata via ricerca web** (non nel codice, non in `config.yaml`): ARPA
Piemonte espone una **API REST pubblica, senza chiave**, costruita su Django
REST Framework, sotto `utility.arpa.piemonte.it/meteoidro/` — root
browsable con 30 endpoint (meteo, idro, nivo, piezometrico, stazioni
centenarie). Non è la stessa cosa della "Banca Dati Storica" citata nella
pagina pubblica (quella resta dietro la mappa interattiva) né della
`api_realtime` (quella copre solo gli ultimi 6 giorni, endpoint
`/data_pie`, `/ggd`) — è un terzo sistema distinto, trovato solo cercando
uno degli URL citati a margine dai risultati di ricerca.

Endpoint rilevanti per la validazione:

- **`stazione_meteorologica/`** — anagrafica stazioni: `denominazione`,
  `codice_stazione`, `comune`, `sigla_prov`, `codice_istat_comune` (stessa
  chiave già usata per `municipalities.istat_code` in tutto il progetto —
  join diretto, nessuna risoluzione nome↔codice necessaria), coordinate
  (`latitudine_n_wgs84_d`/`longitudine_e_wgs84_d`), `quota_stazione`,
  `data_inizio`/`data_fine` (null se stazione ancora attiva), `tipo_staz`.
- **`punti_misura_meteo/`** — punti di misura, con `data_inizio_dati`/
  `data_fine_dati` (copertura temporale reale dei dati, non solo della
  stazione fisica) — un punto di test (`ALA DI STURA`, comune
  `001003`) copre 1993-07-22 → 2025-12-31.
- **`dati_giornalieri_meteo/?fk_id_punto_misura_meteo=<codice>`** — dati
  giornalieri veri: JSON paginato stile DRF (`count`/`next`/`previous`/
  `results`), campi `data`, `tmedia`/`tmax`/`tmin`, `ptot`, `umedia`/
  `umin`/`umax`, `vmedia`/`vraffica`, `bmedia`, `hdd_base18`/`cdd_base18`,
  ecc. Un punto di test ha restituito 10.645 record giornalieri —
  coerente con ~29 anni di storico. **Molti campi risultano `null` nei
  record più vecchi** (copertura sensori non uniforme nel tempo, da
  verificare per stazione prima di usarla per la validazione).

**Non ancora verificato** (da fare prima di scrivere codice): quanti dei
177 comuni già in `temperature` hanno una stazione ARPA con
`codice_istat_comune` corrispondente (la rete ARPA ha ~400 stazioni su
1180 comuni piemontesi, quindi la sovrapposizione reale potrebbe essere
molto minore di 177); il comportamento esatto della paginazione
(`page`/`page_size`, non confermato se supporta filtri di data
`data_after`/`data_before` come query string); eventuali limiti di rate
impliciti (non documentati, il pattern del progetto con Open-Meteo
suggerisce di verificarli empiricamente con un lotto piccolo prima di
lanciare un download massivo).

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
   **immediatamente** — anche una singola richiesta di test isolata
   (senza nessun batch in corso) restituiva `429`. Il corpo della
   risposta ha rivelato la causa reale: `{"error":true,"reason":"Daily
   API request limit exceeded. Please try again tomorrow."}` — un limite
   **giornaliero**, non "al minuto": la finestra di 5h40 sprecata il
   giorno prima aveva già esaurito la quota per l'intera giornata.
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
   soglia**: si blocca sempre intorno a **19-20 richieste "pesanti"** (26
   anni di storico ciascuna) — dopo il 19° comune, ogni tentativo
   successivo falliva con "rate limit persistente dopo 5 tentativi".
   Fermato subito (nessuna perdita, grazie al fix del punto 3): **19
   comuni aggiuntivi salvati con successo** (44 → 63 comuni totali).
5. **Scoperta interessante**: il limite sembra legato al **volume di dati
   per richiesta**, non a un conteggio piatto di richieste. Il giorno
   dopo, un aggiornamento "delta" (`update_recent_data.py`, richieste
   piccole di ~198 giorni ciascuna invece di 26 anni interi) ha
   completato **tutti e 63 i comuni in un solo lotto, zero errori** — ben
   oltre la soglia di ~19-20 vista con le richieste "pesanti". Non è
   stato verificato in modo rigoroso (nessuna documentazione ufficiale
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
Stesso fix di salvataggio incrementale di
`download_extra_municipalities.py`.

**Esecuzione reale**: 63/63 comuni aggiornati con successo, zero errori —
44 comuni con un delta di ~198 giorni (dal 1/1/2026), 19 comuni (appena
scaricati) con un delta di un solo giorno. 8.731 righe totali.

## Dati realmente scaricati/caricati (2026-07-04 → 2026-07-17)

| File | Righe | Copertura |
|---|---|---|
| `data/raw/temperature_data.csv` | 75.976 | 8 province × 9.497 giorni (2000-01-01 → 2025-12-31), nessun nullo. Il 2026 non incluso (l'API storica non accetta date future oltre il giorno corrente) |
| `data/raw/temperature_data_extra.csv` | 526.078 | Cresciuto da 36 a **55 comuni extra** (2026-07-15 → 2026-07-17), stesso periodo di base (2000 → 16/07/2026 per i 19 comuni più recenti) |
| `data/raw/temperature_data_recent.csv` (2026-07-17) | 8.731 | Delta fino a oggi per tutti i 63 comuni (vedi `update_recent_data.py` sopra) |

I numeri "1.7M record" citati in README/PROJECT_SUMMARY restano una stima
pianificata (verosimilmente basata su dati orari, non giornalieri).

- `data/external/municipalities.csv` + tabella `municipalities` nel DB:
  1180 comuni piemontesi reali, geometrie tutte valide (`ST_IsValid`),
  nomi corretti (encoding fix del 2026-07-15). `elevation_m` popolato solo
  per i comuni con dati di temperatura (Open-Meteo Elevation API, 177 dal
  2026-07-18 — oltre i 100 comuni l'API rifiuta una richiesta unica, vedi
  [Pipeline ETL](etl-pipeline.md) per il fix a lotti); `population`
  popolato per tutti i 1180 comuni il 2026-07-16 (vedi sotto).
- Tabella `temperature`: **1.716.094 righe, 177 comuni** (8 capoluoghi +
  169 extra), dal 2000 **fino a oggi** (non più fermo al 31/12/2025).

## `download_population.py` — popolazione residente reale per tutti i 1180 comuni (2026-07-16)

**Motivazione**: covariata esplicativa mancante per il paper scientifico
(vedi [Articolo scientifico](paper-scientifico.md)) —
`municipalities.population` era `NULL` dall'inizio del progetto.

**Percorso trovato dopo un'indagine con diversi vicoli ciechi** (dettaglio
completo in [Articolo scientifico](paper-scientifico.md)):
- L'API SDMX nuova di ISTAT (`esploradati.istat.it`) ha la struttura
  giusta (stessi codici `istat_code`) ma non restituisce osservazioni per
  il dataset `DCIS_POPORESBIL1`.
- Il vecchio portale `dati.istat.it` è dismesso (redirect a un avviso).
- **`demo.istat.it`** è invece un sistema separato e attivo, con un file
  ZIP scaricabile per provincia
  (`https://demo.istat.it/data/posas/POSAS_{anno}_it_{codice}_{nome}.zip`,
  nessuna chiave/account), CSV con una riga per comune/età/sesso — la riga
  con età=999 è il totale per comune. Verificato che i codici comune nel
  CSV coincidono esattamente con `municipalities.istat_code`.

> **Bug incontrato durante l'implementazione**: la colonna età viene letta
> da pandas come stringa (non intero, per via di alcune righe non
> puramente numeriche nel file), quindi il filtro sulla riga di totale va
> scritto come confronto a stringa (`== '999'`), non a intero (`== 999`,
> che restituiva sempre 0 righe) — scoperto testando prima su un file
> scaricato a mano prima di lanciare lo script su tutte le 8 province.

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

**Motivazione**: seconda covariata esplicativa mancante per il paper
scientifico (vedi [Articolo scientifico](paper-scientifico.md)), dopo la
popolazione.

**Decisione presa con l'utente**: niente API CLMS con token JWT (troppo
complessa per un dataset che si aggiorna ogni ~6 anni) — account EU Login
gratuito su `land.copernicus.eu`, poi download manuale via "Download by
area" (ritaglio sul Piemonte invece di tutta Europa), formato vettoriale
GeoPackage.

**Due tentativi prima del file giusto**: il primo file fornito dall'utente
(`U2018_CLC2018_V2020_20u1_doc/`) era solo documentazione/legenda (PDF,
metadata XML), senza geometrie — cartella eliminata dopo aver salvato solo
`data/external/clc_legend.csv` (tabella dei codici CLC, utile per la
categorizzazione). Il file dati vero
(`U2018_CLC2018_V2020_20u1.gpkg`, 136 MB, EPSG:3035, 52.794 poligoni,
campo `Code_18` = codice CLC a 3 cifre) è arrivato al secondo giro.

**Metodo**: `src/data_acquisition/process_land_cover.py` — overlay
geopandas tra le geometrie di tutti i 1180 comuni (riproiettate in
EPSG:3035, la stessa proiezione equal-area di CLC, per calcoli di area
corretti — stessa lezione già imparata per `area_km2`) e i poligoni CLC.
Percentuali aggregate alle 5 categorie di Livello 1 (primo carattere del
codice a 3 cifre: 1=urbano, 2=agricolo, 3=forestale/seminaturale, 4=zone
umide, 5=corpi idrici; i codici speciali 990/995/999 finiscono in
"other"). Overlay completo sui 1180 comuni eseguito in ~16 secondi.
Risultati in `municipality_land_cover` (vedi [Modello Dati](data-model.md)).

**Nota temporale**: CLC2018 è uno scatto del 2018, usato come covariata
statica contro temperature 2000-2025 e popolazione stimata 2026 — pratica
comune per l'uso del suolo (cambia lentamente, un'epoca CLC copre ~6
anni), ma da dichiarare esplicitamente come limite nel paper, non da
nascondere. Vedi [Stato del Progetto](project-status.md).

## NDVI (Copernicus Global Land Service) — verde da satellite (2026-07-17)

**Motivazione**: terza covariata esplicativa per il paper scientifico
(vedi [Articolo scientifico](paper-scientifico.md)), complementare a
`municipality_land_cover` — CORINE dà classi discrete di uso del suolo,
l'NDVI dà una misura continua di densità della vegetazione (utile anche
*dentro* una classe, es. un comune "urbano" con molti alberi vs uno
senza).

**Decisione presa con l'utente**, stessa logica costi/benefici già
applicata a CORINE: scartato Sentinel-2 vero via Google Earth Engine o
Copernicus Data Space Ecosystem (CDSE) Statistical API (10m di
risoluzione ma account aggiuntivo, cloud-masking, rischio di friction già
visto con altre API Copernicus/ISTAT del progetto), a favore di
**Copernicus Global Land Service (CGLS) NDVI 300m V3**: prodotto già
calcolato (composito 10-giornaliero, dal 2014 a oggi), GeoTIFF, nessuna
elaborazione di bande grezze.

> **Falso allarme in corso di ricerca — HR-VPP a 10m**: durante la
> navigazione del Copernicus Browser è emersa una casella "PROJECTION &
> RESOLUTION" con opzioni UTM/LAEA a varie risoluzioni, combinata con un
> filtro testuale "Dataset identifier=NDVI" — appariva come se puntasse a
> un secondo prodotto CLMS realmente a 10m (**HR-VPP**, derivato da
> Sentinel-2 vero), scartato inizialmente solo per complessità d'accesso.
> Sembrava un'opzione migliore del piano originale (10m invece di 300m)
> trovata "gratis". Si è rivelato un **vicolo cieco**: navigando l'albero
> delle sotto-categorie non esisteva alcuna voce HR-VPP effettivamente
> cercabile — le opzioni UTM/LAEA nel pannello filtri sono opzioni
> generiche del sotto-sistema di ricerca, non backed da prodotti
> realmente indicizzati in questo catalogo (ricerca sempre "0 prodotti
> trovati", probabilmente serve un altro portale tipo WEkEO, non
> verificato). Tornati al piano originale (CGLS 300m V3).

**Difficoltà reali con l'interfaccia Copernicus Browser** (scheda
"Search", non "Visualise" — quest'ultima non elenca affatto le collezioni
CLMS): il selettore "Time Range" non rispondeva al click diretto sul testo
del placeholder — sbloccato cliccando esattamente sul primo carattere per
attivare il segmento e digitando le cifre da tastiera, non un calendario a
popup come atteso. Senza un intervallo di date impostato, la ricerca
restituiva sempre "0 prodotti" nonostante il prodotto fosse disponibile.

**Il file scaricato è globale, non ritagliato sul Piemonte**: a
differenza di CLC (che aveva un tool "Download by area" dedicato), questo
prodotto su CDSE non offre un ritaglio lato server — il file scaricato
(Cloud Optimized GeoTIFF, zip) è un'**unica griglia mondiale da ~3.3 GB**,
con 4 raster distinti (NDVI, NOBS, QFLAG, UNC) — estratto solo il file
NDVI (~1.29 GB).

**Formato dati — verificato empiricamente, non solo da documentazione**:
raster GeoTIFF a 8 bit, EPSG:4326, griglia 120960×47040 pixel (~333m di
lato reale, nonostante il nome commerciale "300m"). Scala/offset **letti
direttamente dai metadati embedded nel file**
(`rasterio.open(...).scales`/`.offsets`, non dedotti da un PDF): DN 0-250
→ NDVI reale via `NDVI = DN * 0.004 - 0.08` (range -0.08..0.92). I
**valori di flag trovati online erano sbagliati**: i tag reali del file
riportano `{252, 253, 254, 255} = {Unknown, Snow, Water, Missing}`, non
`{251=missing, 252=cloud, 253=snow, 254=sea, 255=background}` come
suggerito da fonti generiche. **Lezione coerente con l'encoding ISTAT**:
verificare sempre sui byte/metadati reali del file, non fidarsi della
sola documentazione.

**Metodo**: `src/data_acquisition/process_ndvi.py` — zonal stats via
`rasterstats` (non overlay vettoriale come CLC, qui la sorgente è un
raster) tra le geometrie comunali e il raster NDVI, con `all_touched=True`
per includere anche i pixel solo parzialmente coperti dai comuni più
piccoli. Il file è globale (leggerlo tutto in memoria richiederebbe
decine di GB di RAM): lo script legge solo una **finestra**
(`rasterio.windows.from_bounds`) sul bounding box dei comuni piemontesi —
lettura in ~3 secondi indipendentemente dalla dimensione del file
scaricato. Popola `municipality_ndvi` (vedi [Modello Dati](data-model.md)):
`ndvi_mean/min/max/stddev`, `pct_valid_pixels`, `vegetation_class`.

**Esecuzione reale** (composito 10-giornaliero 2026-07-01/2026-07-10):
**1180/1180 comuni popolati**, nessun errore. Valori verificati a
campione: Vercelli 0.62 NDVI medio ("dense", coerente con le risaie —
67-84% agricolo già trovato da CORINE, verdi/allagate a luglio); Torino
0.40 ("moderate"); Bardonecchia/Formazza 0.44-0.49 con deviazione
standard alta (0.26-0.28) — comuni alpini con enorme escursione
altimetrica, `pct_valid_pixels` 98-99%. Distribuzione sui 1180 comuni:
643 dense, 461 very_dense, 76 moderate, 0 sparse/no_vegetation.

## Download collaborativo da una seconda macchina — 35 comuni extra (2026-07-17)

**Contesto**: sessione svolta da una collaboratrice (non il titolare del
progetto) su una macchina **diversa** da quella dove vive il database
reale — nessun accesso a Postgres, nessun `.venv`/`.env` locali, nessun
file in `data/raw`/`data/processed` (tutti esclusi da Git per design,
vedi `.gitignore`). Il titolare aveva chiesto aiuto per scaricare altri
comuni oltre ai 63 già coperti, ma non era raggiungibile per condividere
la lista di quali comuni mancassero.

**Ricostruzione della copertura esistente senza accesso al DB**: i 3
progetti QGIS (`qgis_projects/*.qgz`, con relative preview PNG in
`qgis_projects/previews/`) **sono** tracciati in Git, a differenza dei
dati grezzi.
- `temperature_heatmap.png` mostra i comuni con dati reali colorati contro
  uno sfondo grigio (query live `municipality_id IN (SELECT DISTINCT
  municipality_id FROM temperature)`, vedi
  `qgis_projects/build_maps.py:164`) — ma il testo delle etichette è
  illeggibile (bug noto, font mancante in ambiente headless, vedi
  [Mappe GIS](gis-maps.md)), quindi il PNG da solo non basta a
  identificare i comuni per nome.
- **Metodo usato** (verificabile, non un'ipotesi): rasterizzati tutti i
  1180 poligoni comunali (da `data/external/istat_confini/`, tracciato in
  Git) sulla stessa griglia 1000×800 usata da QGIS (`combined_extent` +
  `scale(1.05)`, extent adattato all'aspect ratio dell'output — replicato
  leggendo `qgis_projects/build_maps.py`), poi classificato ogni comune
  come "con dati" se una quota rilevante (>15%) dei suoi pixel nel PNG è
  significativamente diversa dal grigio di sfondo.
- **Risultato**: esattamente 63 comuni classificati (combacia col numero
  documentato), separazione netta tra "coperti" e "non coperti" (nessun
  caso ambiguo vicino alla soglia), tutti gli 8 capoluoghi (sicuramente
  coperti) classificati correttamente. Alta confidenza, non certezza
  assoluta — è un'inferenza dall'immagine, non una query diretta al DB.

Sui comuni risultanti "non coperti", rieseguito **lo stesso algoritmo** di
`select_extra_municipalities()`/`compute_target_per_province()`/
`farthest_point_sample()` di `download_extra_municipalities.py` per
selezionare 20 nuovi comuni (poi estesi oltre i 20, vedi sotto).

**Download**: lanciato `WeatherDataDownloader.download_for_coordinates()`
a lotti di 20, stesso pattern (8s tra richieste, salvataggio incrementale)
già collaudato dal titolare. Il primo lotto di 20 è riuscito al 100%.

> **Bug reale trovato nei lotti successivi** (richiesta esplicita:
> "scaricali fino a quando non ti blocca"): il codice che aggiornava
> l'insieme "comuni già coperti" tra un lotto e l'altro confrontava
> `PRO_COM_T` (letto da CSV, **inferito `int64` da pandas** — zeri
> iniziali persi, es. `6005` invece di `006005`) con `istat_code`
> convertito a stringa zero-paddata — tipi diversi, il confronto falliva
> quasi sempre. **Effetto**: l'algoritmo del secondo lotto ha
> ri-selezionato quasi gli stessi 20 comuni del primo prima di arrivare a
> comuni davvero nuovi, **scaricandoli due volte**. Scoperto confrontando
> righe attese (9.695/comune × N) vs righe osservate nel CSV finale;
> corretto con un `drop_duplicates(subset=['province','date'])` — le
> righe duplicate erano identiche (stesse coordinate/date), nessun dato
> perso. **Lezione**: qualunque colonna di soli cifre letta da CSV con
> `pandas.read_csv` senza `dtype=str` esplicito perde gli zeri iniziali —
> stesso tipo di bug (non la stessa causa) dell'encoding ISTAT già
> documentato sopra.

Il rate limit giornaliero (vedi sezione dedicata sopra) è scattato dopo
**55 richieste "pesanti" totali in giornata** (20 corrette + 20 duplicate
+ 15 nuove, prima di bloccarsi su "Santena" dopo 5 tentativi con backoff
fino a 80s) — coerente con la soglia di ~19-20 *nuove* richieste pesanti
già osservata dal titolare: il bug ha semplicemente sprecato parte della
quota su richieste ridondanti, facendo scattare il blocco prima del
dovuto.

**Risultato netto**: **35 comuni nuovi** scaricati da una macchina senza
accesso al DB, poi **importati nel DB del titolare lo stesso giorno**
(63 → 98 comuni, 950.110 righe totali in `temperature`). Vedi
[Pipeline ETL](etl-pipeline.md#import-dei-35-comuni-extra-dalla-seconda-macchina-2026-07-17)
per il dettaglio dell'import (risoluzione `istat_code` → `municipality_id`,
pulizia, ricalcolo a valle di ondate/viste KPI/analisi).

## Seconda sessione collaborativa + download diretto — 98 → 177 comuni (2026-07-18)

La stessa collaboratrice ha ripetuto l'esercizio il giorno dopo, ma
**senza dover ricostruire nulla dai PNG QGIS**: nel frattempo il titolare
aveva creato [Comuni già coperti](comuni-coperti.md), pensata proprio per
questo — la collaboratrice ha fatto `git pull`, letto la pagina, e usato
l'elenco esatto (nome + codice ISTAT) come input diretto per lo stesso
campionamento "farthest-point" già collaudato. Risultato: **57 comuni**
scaricati con successo prima del blocco giornaliero (bloccata su
"Cannobio"), consegnati in `temperature_data_extra_helper_batch2.csv` —
questa volta senza il bug `int`/`str` della sessione precedente
(verificato: zero righe duplicate).

**File stantio ricevuto per errore**: insieme a `batch2`, nella stessa
consegna era presente anche `temperature_data_extra_helper_35comuni.csv`
— identico byte per byte nelle dimensioni al file già importato ed
eliminato il giorno prima (339.325 righe, stessi 35 codici ISTAT, stesso
intervallo di date). La voce di log della collaboratrice per questa
sessione cita solo `batch2` come file prodotto: quasi certamente una
copia locale rimasta sul suo disco da prima del `git pull`, finita per
errore nello stesso invio. **Scartato senza importarlo**, dopo aver
verificato (non solo ipotizzato) che tutti e 35 quei comuni fossero già
in `temperature` — un secondo import avrebbe duplicato silenziosamente
339mila righe, dato che `temperature` non ha un vincolo di unicità su
`(municipality_id, date)`. Lezione pratica: **verificare sempre il
contenuto di un file consegnato contro lo stato attuale del DB prima di
importarlo**, anche quando il nome del file sembra nuovo o la richiesta
dell'utente lo dà per scontato.

**Download diretto, stesso giorno**: dopo aver importato `batch2` (98 →
155 comuni), lanciato `download_extra_municipalities.py --count 40`
direttamente (non da una macchina esterna, ma dallo stesso ambiente con
accesso al DB). La selezione già esclude per costruzione qualunque comune
presente in `temperature` al momento della query — quindi nessuna
sovrapposizione possibile né con i 155 preesistenti né con i 57 appena
importati dalla collaboratrice, verificato comunque a posteriori (zero
codici ISTAT in comune). Il rate limit giornaliero, già parzialmente
consumato dalla collaboratrice nella stessa giornata, è scattato dopo
**22 comuni riusciti** su 40 — ma con un sintomo diverso dai blocchi
precedenti: nessun errore visibile, il processo Python è rimasto "vivo"
ma **fermo per oltre 12 minuti** senza scrivere nuovi comuni nel CSV
incrementale e con tempo CPU praticamente piatto, più coerente con un
blocco silenzioso nei cicli di retry che con un fallimento pulito.
Interrotto manualmente dopo aver verificato che i 22 comuni già ottenuti
erano completi (9.696 righe ciascuno — il salvataggio incrementale scrive
un comune alla volta, quindi l'interruzione a metà non ha corrotto nulla
di già scritto). 155 → **177 comuni**.

**Osservazione aggiornata sul limite giornaliero**: la soglia non sembra
un numero fisso di richieste — 19-20 la prima volta (2026-07-17), 57 per
la collaboratrice e solo 22 per il titolare **lo stesso giorno**. Ipotesi
più plausibile (non confermata): la quota è legata al volume di dati
scaricato o al momento della giornata in cui si preme, non a un contatore
piatto di chiamate — coerente con l'osservazione già fatta il 2026-07-17
che le richieste piccole (`update_recent_data.py`) non incontravano mai
il limite mentre quelle da 26 anni sì.

Vedi [Pipeline ETL](etl-pipeline.md#comuni-extra--57-dalla-collaboratrice--22-scaricati-direttamente-2026-07-18)
per il dettaglio completo di import, ricalcolo a valle e consolidamento
file, e [Comuni già coperti](comuni-coperti.md) per l'elenco aggiornato
dei 177 comuni.

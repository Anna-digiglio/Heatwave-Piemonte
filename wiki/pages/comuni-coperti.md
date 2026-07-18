# Comuni già coperti — guida per nuovi download collaborativi

**A cosa serve questa pagina**: elenco di tutti i comuni che hanno **già**
temperature reali in `temperature` (tabella del DB), da consultare
**prima** di scaricare nuovi dati da Open-Meteo — sia per chi lavora da
una seconda macchina senza accesso diretto al DB del titolare (vedi
[Fonti Dati](data-sources.md#download-collaborativo-da-una-seconda-macchina--35-comuni-extra-2026-07-17)
per il precedente di questo tipo), sia per chiunque scarichi nuovi lotti
in autonomia. Evita di ripetere lo stesso lavoro due volte o, peggio, di
scaricare due volte lo stesso comune sprecando quota di rate limit
giornaliero (vedi [Fonti Dati](data-sources.md) per il limite scoperto il
2026-07-17).

**Stato al 2026-07-18**: **98 comuni coperti su 1180** (8 capoluoghi di
provincia + 90 extra), 2000-01-01 → oggi.

## Comuni già coperti (NON riscaricare questi)

### Alessandria (13/187 comuni coperti)

| Comune | Codice ISTAT |
|---|---|
| Alessandria | 006003 |
| Alice Bel Colle | 006005 |
| Bosio | 006022 |
| Carrega Ligure | 006034 |
| Casalnoceto | 006040 |
| Fubine Monferrato | 006076 |
| Gremiasco | 006083 |
| Grondona | 006085 |
| Merana | 006093 |
| Molare | 006095 |
| Moncestino | 006099 |
| Novi Ligure | 006114 |
| Villanova Monferrato | 006185 |

### Asti (9/117 comuni coperti)

| Comune | Codice ISTAT |
|---|---|
| Asti | 005005 |
| Cisterna d'Asti | 005040 |
| Coazzolo | 005041 |
| Maranzana | 005061 |
| Moncucco Torinese | 005070 |
| Robella | 005092 |
| Serole | 005104 |
| Viarigi | 005115 |
| Vinchio | 005120 |

### Biella (5/74 comuni coperti)

| Comune | Codice ISTAT |
|---|---|
| Biella | 096004 |
| Caprile | 096013 |
| Cavaglià | 096016 |
| Gifflenga | 096027 |
| Villa del Bosco | 096078 |

### Cuneo (22/247 comuni coperti)

| Comune | Codice ISTAT |
|---|---|
| Acceglio | 004001 |
| Aisone | 004002 |
| Alto | 004005 |
| Bagnasco | 004008 |
| Bagnolo Piemonte | 004009 |
| Bastia Mondovì | 004014 |
| Briga Alta | 004031 |
| Cuneo | 004078 |
| Entracque | 004084 |
| Genola | 004096 |
| Grinzane Cavour | 004100 |
| Montà | 004133 |
| Pianfei | 004165 |
| Pietraporzio | 004167 |
| Pontechianale | 004172 |
| Roburent | 004186 |
| Roccabruna | 004187 |
| Saliceto | 004201 |
| Santo Stefano Belbo | 004213 |
| Sommariva del Bosco | 004222 |
| Stroppo | 004224 |
| Torre San Giorgio | 004228 |

### Novara (8/87 comuni coperti)

| Comune | Codice ISTAT |
|---|---|
| Borgolavezzaro | 003023 |
| Castelletto sopra Ticino | 003043 |
| Cerano | 003049 |
| Ghemme | 003073 |
| Momo | 003100 |
| Novara | 003106 |
| Pettenasco | 003116 |
| San Nazzaro Sesia | 003134 |

### Torino (31/312 comuni coperti)

| Comune | Codice ISTAT |
|---|---|
| Bardonecchia | 001022 |
| Barone Canavese | 001023 |
| Bruino | 001038 |
| Carema | 001057 |
| Carignano | 001058 |
| Castelnuovo Nigra | 001067 |
| Ceres | 001072 |
| Ceresole Reale | 001073 |
| Chiusa di San Michele | 001081 |
| Claviere | 001087 |
| Favria | 001101 |
| Fiano | 001104 |
| Gravere | 001117 |
| Marentino | 001144 |
| Piverone | 001196 |
| Pomaretto | 001198 |
| Pralormo | 001203 |
| Roletto | 001222 |
| Rorà | 001226 |
| Salbertrand | 001232 |
| Samone | 001235 |
| San Giorio di Susa | 001245 |
| Sauze di Cesana | 001258 |
| Sparone | 001267 |
| Torino | 001272 |
| Torrazza Piemonte | 001273 |
| Usseglio | 001282 |
| Valprato Soana | 001288 |
| Verrua Savoia | 001294 |
| Vigone | 001299 |
| Volpiano | 001314 |

### Verbano-Cusio-Ossola (4/74 comuni coperti)

| Comune | Codice ISTAT |
|---|---|
| Formazza | 103031 |
| Macugnaga | 103039 |
| Verbania | 103072 |
| Villadossola | 103075 |

### Vercelli (6/82 comuni coperti)

| Comune | Codice ISTAT |
|---|---|
| Alagna Valsesia | 002002 |
| Carisio | 002032 |
| Moncrivello | 002079 |
| Rimella | 002113 |
| Valduggia | 002152 |
| Vercelli | 002158 |

## Come scaricare nuovi comuni (Open-Meteo, storico 2000 → oggi)

**Fonte**: Open-Meteo Archive API (`https://archive-api.open-meteo.com/v1/archive`),
nessuna chiave richiesta. **Limite scoperto sul campo**: oltre al rate
limit "al minuto", esiste un **limite giornaliero** — con richieste
"pesanti" (26 anni di storico in una volta) ci si blocca dopo circa
19-20 comuni in una giornata (vedi [Fonti Dati](data-sources.md) per il
racconto completo). Consiglio pratico: scaricare **a lotti piccoli** (10-20
comuni), fermarsi appena arriva un errore `429`/messaggio di quota
esaurita, e riprendere il giorno dopo — non serve a niente insistere,
la quota si resetta il giorno successivo.

**Quali comuni scegliere**: qualunque comune **non presente** nelle
tabelle sopra. Non serve seguire un criterio particolare — anche una
scelta libera va bene, purché non scarichi due volte lo stesso comune
(anche per errore: il progetto non ha un vincolo di unicità su
`(comune, data)`, un doppio import duplicherebbe silenziosamente le
righe). Se si vuole essere sistematici, si può prendere un comune a
testa per provincia diversa, per continuare a distribuire la copertura
sul territorio invece di concentrarla in una sola zona.

### Formato del file da consegnare

Un CSV con **queste colonne esatte** (stesso ordine non obbligatorio, ma
nomi e contenuto sì):

| Colonna | Contenuto | Note |
|---|---|---|
| `date` | data (`YYYY-MM-DD`) | |
| `temp_max` | temperatura massima giornaliera (°C) | |
| `temp_min` | temperatura minima giornaliera (°C) | |
| `temp_mean` | temperatura media giornaliera (°C) | |
| `precipitation` | precipitazione giornaliera (mm) | |
| `province` | **nome del comune** (non della provincia!) | es. `Ceva`, non `Cuneo` |
| `data_source` | `OpenMeteo` | fisso, per tutte le righe |
| `istat_code` | codice ISTAT del comune, **6 cifre** | **fondamentale**: salvarlo come testo/stringa, non come numero — un foglio di calcolo o uno script che lo legge come numero perde gli zeri iniziali (es. `006005` diventa `6005`), rendendo il comune impossibile da abbinare correttamente al database. Se usi Excel: formatta la colonna come "Testo" prima di incollare i codici. Se usi pandas: `pd.read_csv(..., dtype={'istat_code': str})` e mai convertirla in `int`. |
| `province_name` | nome della provincia (es. `Cuneo`) | |

Il codice ISTAT del comune si trova cercando il comune su
`https://www.istat.it` o in qualunque elenco ufficiale dei comuni
italiani — è lo stesso codice usato ovunque nel progetto per collegare
le righe di temperatura al comune giusto nel database.

**Dove consegnare il file**: fuori da Git (i dati grezzi non sono
tracciati nel repository per dimensione, vedi `.gitignore`) — stesso
canale già usato in precedenza (email/drive), non `git push`.

## Nota per chi importa (di solito il titolare o l'IA)

Il file consegnato non ha ancora `municipality_id` (chi scarica da una
macchina senza accesso al DB non può risolverlo). Prima di caricarlo in
`temperature` serve:
1. Pulizia con `DataCleaner.clean_data()` (`src/data_processing/clean_data.py`)
2. Join `istat_code` → `municipality_id` contro la tabella `municipalities`
   (già `UNIQUE` su `istat_code`)
3. Caricamento con `DatabaseLoader.insert_temperature_for_municipalities()`
4. Ricalcolo a valle: `TRUNCATE heatwave_events` + `identify_heatwaves()`,
   `REFRESH MATERIALIZED VIEW` su entrambe le viste KPI, tutti i moduli di
   `src/analysis/`, mappe QGIS

Vedi [Pipeline ETL](etl-pipeline.md#import-dei-35-comuni-extra-dalla-seconda-macchina-2026-07-17)
per un esempio completo di questo stesso identico flusso, eseguito il
2026-07-17 sui 35 comuni della sessione precedente — stessi passi,
stessi bug da evitare (istat_code letto come stringa, non intero).

**Dopo l'import, ricordarsi di aggiornare questa pagina** con i nuovi
comuni coperti, altrimenti il prossimo giro di download rischia di
sovrapporsi.

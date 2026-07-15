# Dashboard Streamlit

**Sorgenti**: `dashboard/app.py`, `dashboard/pages/*.py`, `dashboard/components/*.py`,
`config.yaml` (sezione `dashboard`)

Stato: **implementata ed eseguita il 2026-07-15**, su dati reali. Costruita
inizialmente su 8 comuni (75.976 righe di temperatura, 51 ondate), estesa lo
stesso giorno a 44 comuni (417.868 righe, 145 ondate — vedi
[ETL](etl-pipeline.md)), poi **ampliata sostanzialmente nel contenuto delle
3 pagine di analisi** (vedi sezione dedicata sotto), su richiesta esplicita
dell'utente di un contenuto molto più ricco per ciascuna pagina più una
sidebar di filtri globali. Verificata senza browser reale via
`streamlit.testing.v1.AppTest` (vedi sotto) e poi avviata live
(`streamlit run dashboard/app.py`), raggiungibile su `http://localhost:8501`.

## Struttura reale

```
dashboard/
├── app.py                          # entry point = pagina Home (overview, KPI, card di navigazione)
├── pages/
│   ├── 02_analisi_temporale.py     # trend, anomalie, stagionalità, boxplot per quinquennio, STL
│   ├── 03_analisi_spaziale.py      # coropletiche per provincia, trend per comune, fasce altitudinali, isola di calore, cluster, Moran's I
│   ├── 04_ondate_di_calore.py      # frequenza/intensità/cumulato, mappa concentrazione, heatmap calendario
│   └── 05_download_dati.py         # export CSV (dati puliti + risultati di analisi)
└── components/
    ├── __init__.py                 # bootstrap sys.path (vedi bug sotto)
    ├── constants.py                # palette colori, soglie fasce altitudinali, capoluoghi, riferimenti letteratura (2026-07-15)
    ├── filters.py                  # sidebar comune (intervallo anni + provincia), persistita via st.session_state (2026-07-15)
    ├── heatwave_definitions.py     # definizione alternativa (percentile) di ondata di calore, solo per confronto metodologico (2026-07-15)
    ├── queries.py                  # accesso dati (DB + CSV di output), cache_data
    └── maps.py                     # conversione WKT → GeoJSON per folium
```

**Scostamento deliberato dal piano**: niente `pages/01_home.py` separato —
`app.py` stesso è la home page, che è la convenzione standard di Streamlit
(l'entry point mostra già il contenuto della prima pagina). Niente
`components/charts.py` separato — i grafici Plotly sono scritti
direttamente nelle pagine che li usano.

Configurazione da `config.yaml`: titolo (`dashboard.title`) passato a
`st.set_page_config`; porta 8501 passata da riga di comando
(`--server.port 8501`), non c'è un modo diretto per leggerla da
`config.yaml` all'avvio di `streamlit run`.

## Filtri globali e navigazione (2026-07-15)

- **Sidebar comune** (`components/filters.py::render_sidebar_filters()`):
  slider intervallo anni (2000-2025) e multiselect provincia, richiamata in
  cima a ogni pagina (home inclusa). Usa `st.session_state` per persistere
  la scelta dell'utente quando naviga da una pagina all'altra (Streamlit
  esegue ogni pagina come script indipendente, i widget non sono condivisi
  automaticamente — solo il `session_state` lo è). Non aggiunta a
  "Download Dati": i filtri non avrebbero alcun effetto lì (i file scaricabili
  sono CSV completi), e mostrare un filtro senza effetto sarebbe fuorviante.
- **Home con card di navigazione**: sostituiti i link testuali con 3
  `st.container(border=True)` affiancati (uno per pagina di analisi), ognuno
  con titolo, una frase di sintesi e `st.page_link()` per la navigazione
  reale (non solo testo).
- **Palette coerente** (`components/constants.py`): scala sequenziale
  `RdYlBu_r` (blu→rosso) per ogni valore assoluto di temperatura in tutte le
  mappe/grafici; scala divergente `RdBu_r` centrata sullo zero solo per
  *variazioni* (trend, anomalie) — le due non vanno mai confuse, dato che
  nella prima il colore è un valore assoluto e nella seconda una velocità di
  cambiamento. Rosso "d'allarme" riservato ad anomalie/eventi critici, non
  usato come colore di sfondo generico.

## Contenuto delle pagine (dati reali)

### Home
Intro in linguaggio semplice, sidebar filtri, 3 card di navigazione,
spiegazione di cosa conta come "ondata di calore", metriche generali (righe
di temperatura, periodo, comuni con dati reali, ondate identificate) con
didascalie, mappa dei comuni (filtrata per provincia) e tabella trend di
riscaldamento (filtrata allo stesso modo).

### Analisi Temporale (`02_analisi_temporale.py`) — ampliata il 2026-07-15
Tab **Panoramica**: 4 metriche in alto (pendenza sul periodo selezionato,
significatività, trend Mann-Kendall di riferimento sull'intero 2000-2025,
temperatura media dell'ultimo anno); serie annuale max/media/min con **retta
di regressione sovrapposta**, ricalcolata dal vivo sul periodo scelto in
sidebar (non il CSV precalcolato, che copre sempre tutto il 2000-2025);
grafico delle **anomalie** rispetto a una baseline configurabile
dall'utente (default: primo decennio disponibile per il comune); confronto
tra le **4 stagioni meteorologiche** (DJF/MAM/JJA/SON) anno per anno, con
pendenza per stagione, per vedere quale si scalda più in fretta; **boxplot
per quinquennio** sulla serie giornaliera, per mostrare l'evoluzione della
variabilità e non solo della media; un piccolo widget di confronto con
**valori di riferimento pubblicati in letteratura** (IPCC AR6, rapporti
ISPRA) — dichiarati esplicitamente come non calcolati da questo progetto e
non scaricati in tempo reale, solo per dare un contesto di scala. Tab
**Dettaglio tecnico**: test Mann-Kendall/Sen's slope sull'intero periodo,
scomposizione STL, nota di metodologia.

### Analisi Spaziale (`03_analisi_spaziale.py`) — ampliata il 2026-07-15
Tab **Panoramica**: 4 metriche (provincia più calda, provincia con trend più
rapido, comune più in quota, comuni con dati nel filtro attuale); **mappa
coropletica per provincia** (temperatura media nel periodo selezionato),
confine reale ottenuto aggregando via PostGIS (`ST_Union`) le geometrie di
tutti i 1180 comuni di ciascuna provincia, non solo i 44 con dati; **mappa
del trend** (punti per comune, colormap divergente centrata sullo zero,
`lr_slope_per_decade` da `trend_analysis.csv`); confronto per **fascia
altitudinale** (pianura/collina/montagna, soglie 300/700 m su elevazione
reale da Open-Meteo, vedi sotto); confronto **isola di calore urbana**
(Torino città vs media dei comuni rurali della sua stessa provincia).
Tab **Dettaglio tecnico**: cluster climatici K-means (k=3) e indice di
Moran (contenuto già esistente, spostato qui), nota di metodologia sui
limiti delle sezioni sopra (fasce altitudinali semplificate, confronto UHI
illustrativo, mappa trend non ricalcolata sul filtro anni).

### Ondate di Calore (`04_ondate_di_calore.py`) — ampliata il 2026-07-15
4 metriche in alto (n. ondate nel filtro attuale, n. ondate nell'ultimo
anno della finestra, durata media, intensità media). Tab **Panoramica**:
grafico a barre a doppio asse (n. eventi + durata media per anno);
intensità media per anno; **conteggio cumulato** dal 2000 per mostrare se il
fenomeno accelera; mappa di concentrazione geografica (coropletica per
comune, quante ondate nel filtro attuale); **heatmap "calendario"** (anno ×
giorno dell'anno, colore = quanti comuni in ondata quel giorno) per vedere
se gli eventi si spostano verso primavera/autunno. Tab **Dettaglio
tecnico**: confronto con una **definizione alternativa** di ondata di
calore a soglia percentile (relativa al singolo comune, non fissa per
tutti — vedi sotto), nota di metodologia. Sotto le tab, invariate: tabella
statistiche per comune ed elenco ondate.

### Download Dati
Invariata: ogni file ha una descrizione in linguaggio semplice di cosa
contiene, oltre al bottone di export per i CSV di `data/processed/`,
`data/external/` e `output/`.

## Due decisioni di merito prese durante l'ampliamento (2026-07-15)

- **Definizione di ondata di calore, canonica vs alternativa**: la richiesta
  iniziale chiedeva di "implementare una funzione per identificare le
  ondate di calore" con una soglia percentile. Il progetto ha già una
  definizione canonica, usata ovunque nel resto del sito (`identify_heatwaves()`
  nel database, soglia fissa 35°C/3gg — vedi [Modello Dati](data-model.md)):
  sostituirla avrebbe reso incoerenti tutti i numeri già mostrati altrove
  (145 ondate in home, statistiche per comune, ecc.). Scelta: la
  soglia percentile è implementata come funzione pura
  (`components/heatwave_definitions.py::identify_heatwaves_percentile()`)
  e usata **solo** nel tab "Dettaglio tecnico" della pagina Ondate di
  Calore, come confronto metodologico calcolato al volo per il comune
  selezionato — non tocca il database né gli altri numeri del sito.
- **Elevazione reale invece di un placeholder**: `municipalities.elevation_m`
  era `NULL` per tutti i comuni (mai popolato, voce aperta in
  [Stato del Progetto](project-status.md)). Necessario per il confronto per
  fascia altitudinale richiesto nella pagina Analisi Spaziale. Chiesto
  esplicitamente all'utente se scaricare il dato reale o mostrare un
  placeholder "non disponibile": scelto di scaricarlo davvero (Open-Meteo
  Elevation API, 44 chiamate, pochi secondi) — vedi
  [Fonti Dati](data-sources.md) e [Modello Dati](data-model.md).

Tutte le pagine continuano a mostrare avvisi/info (`st.warning`/`st.info`)
sulla granularità limitata (44 comuni su 1180) dove rilevante.

**Aggiornamento 2026-07-15 (leggibilità per non addetti ai lavori,
sessione precedente)**: aggiunto un riquadro `st.expander("ℹ️ Come si legge
questa pagina")` a inizio di ogni pagina di analisi, con spiegazioni in
linguaggio semplice dei metodi statistici usati, più didascalie
(`st.caption`) sotto ogni grafico/metrica principale. Con l'ampliamento
successivo, ogni nuovo grafico ha ricevuto lo stesso trattamento (2-3 righe
di "cosa guardare" sopra ciascuno, non solo sui grafici preesistenti).

## Come verificare senza aprire un browser

`streamlit.testing.v1.AppTest` esegue davvero lo script Streamlit
in-process e permette di ispezionare eccezioni ed elementi renderizzati:

```python
from streamlit.testing.v1 import AppTest
at = AppTest.from_file('dashboard/app.py', default_timeout=30)
at.run()
assert not list(at.exception)
```

Un semplice `curl http://localhost:8501` **non basta**: Streamlit è
un'app client-rendered (SPA), quindi la risposta HTTP grezza è solo il
"guscio" statico — il contenuto vero (metriche, tabelle, titoli) non è nel
markup HTML iniziale e va verificato con `AppTest` o un browser reale.

## Bug trovati ed eseguendo la dashboard per la prima volta (2026-07-15)

- **`ModuleNotFoundError: No module named 'components'`**: Streamlit
  esegue gli script con `exec()`, non con l'invocazione standard
  `python script.py` — quindi la cartella dello script **non** viene
  aggiunta automaticamente a `sys.path` come farebbe l'interprete normale.
  Fix: bootstrap esplicito (`sys.path.insert(0, ...)`) in cima a `app.py` e
  a ogni pagina in `pages/`, prima di importare da `components`.
- **`folium.GeoJson()` non accetta WKT grezzo**: passargli direttamente la
  stringa WKT letta dal DB fa sì che `folium`/`branca` provino ad aprirla
  come se fosse un percorso file (`OSError: Invalid argument`). Fix:
  `components/maps.py::wkt_to_geojson()` converte WKT → dict GeoJSON via
  `shapely.wkt.loads` + `shapely.geometry.mapping` prima di passarlo a
  `folium.GeoJson`.
- **`use_container_width` deprecato**: la versione di Streamlit installata
  (1.58.0) l'ha già superato come data di rimozione annunciata — sostituito
  con `width='stretch'` in tutte le occorrenze.

## Dipendenze

Tutte già in `requirements.txt` (`streamlit`, `streamlit-folium`, `folium`,
`plotly`). **Allineate il 2026-07-15** alle versioni effettivamente
installate nel `.venv` (streamlit 1.58.0, non più 1.29.0 pinnato — vedi
[Stato del Progetto](project-status.md) per l'elenco completo del drift
risolto in tutto `requirements.txt`, non solo per la dashboard). Le mappe
coropletiche aggiunte il 2026-07-15 usano `branca.colormap.LinearColormap`
(già presente come dipendenza transitiva di `folium`, non serve aggiungerla
a `requirements.txt`).

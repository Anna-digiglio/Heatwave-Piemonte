# Dashboard Streamlit

**Sorgenti**: `dashboard/app.py`, `dashboard/pages/*.py`, `dashboard/components/*.py`,
`config.yaml` (sezione `dashboard`)

Stato: **implementata ed eseguita il 2026-07-15**, su dati reali (75.976
righe di temperatura, 51 ondate di calore, risultati di `src/analysis/`).
Verificata senza browser reale via `streamlit.testing.v1.AppTest` (vedi
sotto) e poi avviata live (`streamlit run dashboard/app.py`), raggiungibile
su `http://localhost:8501`.

## Struttura reale

```
dashboard/
├── app.py                          # entry point = pagina Home (overview & KPI)
├── pages/
│   ├── 02_analisi_temporale.py     # trend (Mann-Kendall/regressione) + STL per comune
│   ├── 03_analisi_spaziale.py      # mappa Folium, cluster climatici, Moran's I
│   ├── 04_ondate_di_calore.py      # statistiche ed elenco heatwave_events
│   └── 05_download_dati.py         # export CSV (dati puliti + risultati di analisi)
└── components/
    ├── __init__.py                 # bootstrap sys.path (vedi bug sotto)
    ├── queries.py                  # accesso dati (DB + CSV di output), cache_data
    └── maps.py                     # conversione WKT → GeoJSON per folium
```

**Scostamento deliberato dal piano**: niente `pages/01_home.py` separato —
`app.py` stesso è la home page, che è la convenzione standard di Streamlit
(l'entry point mostra già il contenuto della prima pagina). Niente
`components/charts.py` separato — i grafici Plotly sono scritti
direttamente nelle pagine che li usano (troppo pochi per giustificare
un'astrazione condivisa oggi).

Configurazione da `config.yaml`: titolo (`dashboard.title`) passato a
`st.set_page_config`; porta 8501 passata da riga di comando
(`--server.port 8501`), non c'è un modo diretto per leggerla da
`config.yaml` all'avvio di `streamlit run`.

## Contenuto delle pagine (dati reali)

- **Home**: intro in linguaggio semplice su cosa fa il progetto, spiegazione
  di cosa conta come "ondata di calore" in un riquadro espandibile, metriche
  generali (righe di temperatura, periodo, comuni con dati reali, ondate
  identificate) con didascalie, mappa dei 8 comuni capoluogo, tabella trend
  di riscaldamento.
- **Analisi Temporale**: riquadro "come si legge questa pagina" (Mann-Kendall
  vs regressione lineare, cosa mostra la STL), selezione comune, serie
  giornaliera max/media/min, scomposizione STL (trend/stagionalità/residuo)
  con didascalia che spiega ciascuna componente.
- **Analisi Spaziale**: riquadro esplicativo su K-means e indice di Moran in
  linguaggio semplice, mappa dei cluster climatici (K-means, k=3), indice di
  Moran con interpretazione discorsiva (`st.success`/`st.info` a seconda
  della significatività) oltre al numero, avviso esplicito sul limite
  campionario (8 unità spaziali).
- **Ondate di Calore**: riquadro esplicativo su durata/intensità, frequenza
  per anno con didascalia interpretativa, statistiche per comune, elenco
  filtrabile delle 51 ondate.
- **Download Dati**: ogni file ha una descrizione in linguaggio semplice di
  cosa contiene, non solo il nome, oltre al bottone di export per i CSV di
  `data/processed/`, `data/external/` e `output/`.

Tutte le pagine mostrano avvisi (`st.warning`) sulla granularità limitata
(8 comuni capoluogo su 1180) dove rilevante, invece di lasciarla implicita.

**Aggiornamento 2026-07-15 (leggibilità per non addetti ai lavori)**: su
richiesta esplicita dell'utente, aggiunto un riquadro `st.expander("ℹ️ Come
si legge questa pagina")` a inizio di ogni pagina di analisi, con
spiegazioni in linguaggio semplice dei metodi statistici usati (senza
richiedere che il visitatore conosca già Mann-Kendall, STL o Moran's I),
più didascalie (`st.caption`) sotto ogni grafico/metrica principale che ne
riassumono il significato pratico. Obiettivo: rendere il sito comprensibile
anche a chi non conosce il progetto (es. un recruiter), non solo a chi ha
già letto la wiki.

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
risolto in tutto `requirements.txt`, non solo per la dashboard).

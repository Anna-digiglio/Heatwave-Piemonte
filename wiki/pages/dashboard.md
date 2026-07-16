# Dashboard Streamlit

**Sorgenti**: `dashboard/Home.py`, `dashboard/pages/*.py`, `dashboard/components/*.py`,
`config.yaml` (sezione `dashboard`)

Stato: **implementata ed eseguita il 2026-07-15**, su dati reali. Costruita
inizialmente su 8 comuni (75.976 righe di temperatura, 51 ondate), estesa lo
stesso giorno a 44 comuni (417.868 righe, 145 ondate — vedi
[ETL](etl-pipeline.md)), poi **ampliata sostanzialmente nel contenuto delle
3 pagine di analisi** (vedi sezione dedicata sotto), su richiesta esplicita
dell'utente di un contenuto molto più ricco per ciascuna pagina, con
filtri (poi spostati da una sidebar globale a widget inline per pagina,
vedi sotto). Verificata senza browser reale via
`streamlit.testing.v1.AppTest` (vedi sotto) e poi avviata live
(`streamlit run dashboard/Home.py`), raggiungibile su `http://localhost:8501`.
**Rinominata da `app.py` a `Home.py` il 2026-07-15** su richiesta
dell'utente (vedi sotto).

## Struttura reale

```
dashboard/
├── Home.py                         # entry point = pagina Home (overview, KPI, card di navigazione)
├── pages/
│   ├── 02_analisi_temporale.py     # trend, anomalie, stagionalità, boxplot per quinquennio, STL
│   ├── 03_analisi_spaziale.py      # coropletiche per provincia, trend per comune, fasce altitudinali, uso del suolo, popolazione, cluster, Moran's I
│   ├── 04_ondate_di_calore.py      # frequenza/intensità/cumulato, mappa concentrazione, heatmap calendario
│   └── 05_download_dati.py         # export CSV (dati puliti + risultati di analisi)
└── components/
    ├── __init__.py                 # bootstrap sys.path (vedi bug sotto)
    ├── constants.py                # palette colori, soglie fasce altitudinali, capoluoghi, riferimenti letteratura, etichette Mann-Kendall (2026-07-15)
    ├── filters.py                  # filtri anni/provincia, inline per pagina (non più sidebar dal 2026-07-15)
    ├── heatwave_definitions.py     # definizione alternativa (percentile) di ondata di calore, solo per confronto metodologico (2026-07-15)
    ├── styling.py                  # CSS condiviso, iniettato in ogni pagina (2026-07-15)
    ├── queries.py                  # accesso dati (DB + CSV di output), cache_data
    └── maps.py                     # conversione WKT → GeoJSON per folium

.streamlit/
└── config.toml                     # tema Streamlit nativo (colori, font, raggio angoli) — 2026-07-15
```

**Scostamento deliberato dal piano**: niente `pages/01_home.py` separato —
`Home.py` stesso è la home page, che è la convenzione standard di Streamlit
(l'entry point mostra già il contenuto della prima pagina; il nome
`Home.py`, non `app.py`, è la convenzione più diffusa nelle app Streamlit
multipage — vedi nota sotto). Niente `components/charts.py` separato — i
grafici Plotly sono scritti direttamente nelle pagine che li usano.

**Rinominato `app.py` → `Home.py` il 2026-07-15**, su richiesta esplicita
dell'utente ("dobbiamo trovare un altro nome per la pagina principale, non
si può chiamare app"). Rinominato con `git mv` (storia Git preservata),
aggiornati i riferimenti nei docstring (`dashboard/Home.py`,
`dashboard/components/__init__.py`) e in questa pagina. **Non toccati**
`README.md`/`PROJECT_SUMMARY.md`/`docs/*.md`: per `CLAUDE.md` sono sorgenti
di pianificazione immutabili, quindi citano ancora il comando
`streamlit run dashboard/app.py` — ormai stale, il comando corretto è
`streamlit run dashboard/Home.py`. Verificato con `AppTest` sul nuovo path
(nessuna eccezione) e riavviato il server live sulla nuova entry point.

Configurazione da `config.yaml`: titolo (`dashboard.title`) passato a
`st.set_page_config`; porta 8501 passata da riga di comando
(`--server.port 8501`), non c'è un modo diretto per leggerla da
`config.yaml` all'avvio di `streamlit run`.

## Filtri: da sidebar globale a inline per pagina (2026-07-15)

Prima versione: una sidebar comune (`render_sidebar_filters()`, slider anni +
multiselect provincia) richiamata in cima a ogni pagina, home inclusa.
L'utente ha fatto notare che sembrava per lo più inutile ("non so cosa
possiamo aggiungere a lato") — su molte pagine i filtri non aggiungevano
valore reale o duplicavano controlli già presenti nel corpo della pagina.
**Rimossa interamente la sidebar**; `components/filters.py` ora espone due
funzioni pensate per essere richiamate *inline*, solo dove il filtro serve
davvero:

- `render_year_range_filter(key)` — slider anni, con `key` univoca per
  pagina (necessaria perché non c'è più uno stato condiviso globale: ogni
  pagina ha il proprio, Streamlit lo persiste da solo tramite `key` per
  tutta la sessione, senza bisogno di gestire `st.session_state` a mano
  come richiedeva la sidebar condivisa).
- `render_province_filter(key)` — multiselect provincia, stessa logica.
  **Default vuoto** (2026-07-16, fix a seguito di un altro feedback
  dell'utente): la primissima versione default va a `all_provinces`,
  riempiendo il riquadro con tutti gli 8 tag già selezionati fin dal primo
  sguardo — "non facilmente capibile", secondo l'utente. Ora il box parte
  vuoto (`default=[]`, con `placeholder="Tutte le province con dati"`) e
  il fallback già esistente nella funzione (`return provinces or
  all_provinces`) fa sì che "nessuna selezione" continui a significare
  "tutti i 44 comuni", senza dover mai spuntare/digitare nulla per lo stato
  di default — un click sul box serve solo se si vuole restringere,
  scegliendo dal menu (mai scrivendo a mano il nome di una provincia).

**Dove sono rimasti, dove sono stati tolti**:
- **Home**: nessun filtro — mostra sempre tutti i 44 comuni (una pagina di
  overview non trae beneficio da un filtro).
- **Analisi Temporale**: solo l'intervallo anni (inline, sotto il
  selettore comune/checkbox Piemonte) — è l'unico filtro usato davvero
  nella pagina (regressione, anomalie, stagioni, boxplot). Il filtro
  provincia è stato tolto: serviva solo a restringere la lista dei 44
  comuni nel menu a tendina, un beneficio marginale.
- **Analisi Spaziale**: intervallo anni **e** provincia, entrambi inline
  in cima alla pagina — qui il filtro provincia ha un senso reale (la
  pagina è esplicitamente sulla geografia: mappe coropletiche, fasce
  altitudinali, isola di calore, tutte hanno senso se ristrette a un
  sottoinsieme di province).
- **Ondate di Calore**: stessa scelta di Analisi Spaziale — entrambi i
  filtri, inline, perché frequenza/intensità/mappa di concentrazione
  cambiano davvero in base al periodo e alle province scelte.
- **Download Dati**: nessun filtro (invariato) — i file scaricabili sono
  CSV completi, un filtro qui non avrebbe alcun effetto.

- **Home con card di navigazione**: sostituiti i link testuali con 3
  `st.container(border=True, height=280)` affiancati (uno per pagina di
  analisi), ognuno con titolo, una frase di sintesi e `st.page_link()` per
  la navigazione reale (non solo testo). Altezza **fissa** (2026-07-16):
  senza `height` esplicito ogni card si dimensiona sul proprio contenuto,
  quindi 3 didascalie di lunghezza anche solo leggermente diversa
  producono 3 card di altezza diversa — non risolvibile in modo affidabile
  tarando a mano la lunghezza del testo (il punto di a-capo dipende dalla
  larghezza reale della colonna a schermo, non dal conteggio caratteri).
- **Palette coerente** (`components/constants.py`): scala sequenziale
  `RdYlBu_r` (blu→rosso) per ogni valore assoluto di temperatura in tutte le
  mappe/grafici; scala divergente `RdBu_r` centrata sullo zero solo per
  *variazioni* (trend, anomalie) — le due non vanno mai confuse, dato che
  nella prima il colore è un valore assoluto e nella seconda una velocità di
  cambiamento. Rosso "d'allarme" riservato ad anomalie/eventi critici, non
  usato come colore di sfondo generico.

## Contenuto delle pagine (dati reali)

### Home
Intro in linguaggio semplice, 3 card di navigazione, metriche generali
(righe di temperatura, periodo, comuni con dati reali, ondate identificate)
con didascalie, mappa dei 44 comuni e tabella trend di riscaldamento —
nessun filtro (vedi sopra).

**Spiegazione "cos'è un'ondata di calore" spostata (2026-07-16)**: era un
riquadro `st.expander` a sé nella home. Su richiesta dell'utente, rimossa
da qui — la home è una pagina di overview, non il posto giusto per una
spiegazione di metodologia che appartiene a una pagina specifica — e
integrata nel riquadro "ℹ️ Come si legge questa pagina" già esistente in
`04_ondate_di_calore.py`, insieme alla sfumatura che nella home era presente
ma nella pagina Ondate mancava ("i climatologi usano spesso soglie che
variano da località a località, non un valore fisso").

**Mappa colorata per trend, non più tutta rossa (2026-07-16)**: la mappa
mostrava tutti i 44 comuni con lo stesso rosso fisso (serviva solo a
localizzarli, non trasmetteva alcuna informazione). Su segnalazione
dell'utente ("perché non dividerla per gravità come le altre?"), ricolorata
per `lr_slope_per_decade` (stesso `trend_analysis.csv` già usato dalla
tabella accanto), con la stessa colormap divergente e la stessa legenda a
5 fasce (`render_gradient_legend()`) della mappa trend di Analisi Spaziale
— coerenza visiva tra le due pagine invece di due modi diversi di
rappresentare lo stesso tipo di dato.

### Analisi Temporale (`02_analisi_temporale.py`) — ampliata il 2026-07-15
Tab **Panoramica**: 4 metriche in alto (pendenza sul periodo selezionato,
significatività, trend Mann-Kendall di riferimento sull'intero 2000-2025,
temperatura media dell'ultimo anno); serie annuale max/media/min con **retta
di regressione sovrapposta**, ricalcolata dal vivo sul periodo scelto con
lo slider anni della pagina (non il CSV precalcolato, che copre sempre
tutto il 2000-2025);
grafico delle **anomalie** rispetto a una baseline **fissa** (primo
decennio disponibile per il comune, non configurabile — vedi nota sotto);
confronto
tra le **4 stagioni meteorologiche** (DJF/MAM/JJA/SON) anno per anno, con
pendenza per stagione, per vedere quale si scalda più in fretta; **boxplot
per quinquennio** sulla serie giornaliera, per mostrare l'evoluzione della
variabilità e non solo della media; un piccolo widget di confronto con
**valori di riferimento pubblicati in letteratura** (IPCC AR6, rapporti
ISPRA) — dichiarati esplicitamente come non calcolati da questo progetto e
non scaricati in tempo reale, solo per dare un contesto di scala. Tab
**Dettaglio tecnico**: test Mann-Kendall/Sen's slope sull'intero periodo,
scomposizione STL, nota di metodologia.

**Testo esplicativo esteso nel tab Dettaglio tecnico (2026-07-16)**: su
richiesta esplicita dell'utente ("non capisco cosa c'è scritto, è poco
chiara"), riscritte in linguaggio discorsivo, senza riferimenti al codice,
le spiegazioni di: Mann-Kendall (confronta ogni coppia di anni, conta
quante volte il più recente è più caldo del più vecchio), MK p-value
(probabilità che il risultato sia solo caso), Sen's slope (mediana delle
pendenze tra tutte le coppie di punti, robusta agli anni anomali),
Regressione °C/decade (la retta di tendenza classica, più sensibile agli
estremi ma standard nei report climatici) — con una sintesi finale su
come i 4 numeri si completano a vicenda. Stessa estensione per la STL:
spiegato prima *perché* si scompone una serie giornaliera rumorosa (il
segnale di riscaldamento, lento, è nascosto sotto oscillazioni stagionali
e giornaliere molto più grandi), poi cosa mostra ciascuno dei 3 grafici
(trend = tendenza di fondo ripulita; stagionalità = ciclo che si ripete
identico ogni anno, non un cambiamento nel tempo; residuo = giornate
anomale non spiegate dagli altri due). Riscritta anche la sezione
"Metodologia" in forma di domande e risposte (perché due pendenze diverse,
perché le stagioni meteorologiche e non astronomiche, perché la baseline è
fissa, cosa sono i riferimenti nazionale/globale) invece dell'elenco
puntato originale, giudicato poco chiaro dall'utente.

**Opzione aggregata "Piemonte"** (2026-07-15): una checkbox `🌍 Intero
Piemonte` accanto al selettore "Comune" (che si disabilita quando la
checkbox è attiva, invece di convivere come voce nella stessa lista —
prima versione scartata su richiesta dell'utente, vedi log). Quando
attiva, ogni grafico/metrica della pagina (serie annuale, anomalie,
stagioni, boxplot, STL, Mann-Kendall) viene calcolato sulla **media
aritmetica non pesata** dei 44 comuni con dati reali, invece che su un
singolo comune — con un `st.info` esplicito che chiarisce non essere una
stima ufficiale della temperatura regionale (richiederebbe pesare per
area/popolazione e includere tutti i 1180 comuni, non solo i 44
monitorati; questa pagina non ha più un filtro provincia, vedi sezione
"Filtri" più sopra — la media è sempre sui 44 comuni). Mann-Kendall/regressione sull'intero periodo per l'aggregato
sono ricalcolati al volo con le stesse funzioni pure di
`src/analysis/trend_analysis.py` (`mann_kendall_trend()`/`linear_trend()`),
non lette da `trend_analysis.csv` (che ha una riga per comune, non per
l'aggregato); stesso discorso per la STL, ricalcolata al volo con
`decompose()` di `src/analysis/seasonal_analysis.py` invece di leggere un
CSV precalcolato inesistente per l'aggregato.

### Analisi Spaziale (`03_analisi_spaziale.py`) — ampliata il 2026-07-15
Tab **Panoramica**: 4 metriche (provincia più calda, provincia con trend più
rapido, comune più in quota, comuni con dati nel filtro attuale); **mappa
coropletica per provincia** (temperatura media nel periodo selezionato),
confine reale ottenuto aggregando via PostGIS (`ST_Union`) le geometrie di
tutti i 1180 comuni di ciascuna provincia, non solo i 44 con dati; **mappa
del trend** (punti per comune, colormap divergente centrata sullo zero,
`lr_slope_per_decade` da `trend_analysis.csv`); **legenda a fasce sotto
entrambe le mappe** (2026-07-15, `components/maps.py::render_gradient_legend()`)
— non il gradiente continuo di default di branca, ma 5 fasce discrete con
swatch del colore realmente usato, range numerico ed etichetta di
gravità/velocità esplicita (es. "Nella media", "Riscaldamento rapido"),
richiesta dall'utente per capire subito cosa significa ogni colore senza
dover interpretare una colorbar continua; confronto per **fascia
altitudinale** (pianura/collina/montagna, soglie 300/700 m su elevazione
reale da Open-Meteo, vedi sotto).

**Uso del suolo, popolazione e temperatura (2026-07-16, sostituisce il
vecchio confronto "isola di calore urbana")**: il confronto originale
(Torino città vs media dei comuni rurali della sua provincia, dichiarato
esplicitamente "solo illustrativo") è stato sostituito con contenuto basato
sui dati reali di uso del suolo/popolazione aggiunti lo stesso giorno (vedi
[Modello Dati](data-model.md), tabella `municipality_land_cover`) — su
richiesta esplicita dell'utente ("procedi con Aggiungere popolazione/uso
del suolo alla dashboard"):
- **Mappa uso del suolo dominante**: tutti i 1180 comuni (non solo i 44 con
  temperatura), colori vicini alla palette ufficiale CORINE
  (`LAND_COVER_COLORS` in `components/constants.py`, presi da
  `data/external/clc_legend.csv`).
- **Mappa densità di popolazione**: tutti i 1180 comuni, scala
  logaritmica (altrimenti Torino schiaccia la scala).
- **Scatter temperatura vs uso del suolo/popolazione**: solo i comuni con
  temperatura, con un selettore (`st.radio`) tra % urbano, % industriale/
  commerciale, densità di popolazione; colore = fascia altitudinale (per
  poter valutare a occhio se l'effetto regge a parità di quota); metrica
  di correlazione di Pearson mostrata con caveat esplicito ("non
  controllata per quota", il vero modello resta pianificato in
  `paper/manoscritto.md` §3.5, non ancora costruito). Verificato con
  `AppTest` un valore reale di correlazione +0.30 (% urbano vs
  temperatura, tutti i comuni) — plausibile, non sospetto.

**Bug corretto durante lo sviluppo**: le query di geometrie/uso del suolo
condividono la colonna `province_name` — un primo merge tra le due
produceva `province_name_x`/`province_name_y` invece del nome atteso
(`KeyError` scoperto subito con `AppTest`, non in produzione), risolto
escludendo la colonna duplicata da un lato del merge prima di unirle.

Tab **Dettaglio tecnico**: cluster climatici K-means (k=3) e indice di
Moran (contenuto già esistente, spostato qui), nota di metodologia sui
limiti delle sezioni sopra (fasce altitudinali semplificate, confronto UHI
illustrativo, mappa trend non ricalcolata sul filtro anni).

**Testo esplicativo esteso nel tab Dettaglio tecnico (2026-07-16)**: stessa
richiesta e stesso trattamento già fatto per Analisi Temporale ("non capisco
cosa c'è scritto, è poco chiara"). K-means spiegato passo per passo (si
fissa in anticipo il numero di gruppi, k=3 — scelta pratica per avere zone
descrivibili a parole, non calcolata con un metodo statistico tipo elbow —
poi l'algoritmo assegna ogni comune al centro più vicino sulla base di
temperatura/giorni caldi *standardizzati*, sposta i centri, ripete),
chiarito esplicitamente che il raggruppamento non guarda la posizione
geografica dei comuni (se i cluster risultano compatti sulla mappa è un
risultato, non un'ipotesi di partenza). **Suddivisione dinamica dei 3
cluster**: invece di descriverli con etichette fisse ("alpino"/"pianura"/
"intermedio", fragili se l'analisi viene ri-eseguita e la numerazione dei
cluster cambia), il codice ora ordina i 3 gruppi trovati dal più fresco al
più caldo in base alla temperatura media reale e genera la descrizione al
volo (temperatura media, giorni sopra 30°C, elenco comuni) — sempre corretta
anche se `spatial_analysis.py` venisse ri-eseguito con un'assegnazione di
cluster diversa.

**Aggiornamento 2026-07-16**: l'utente ha notato che l'assegnazione delle
etichette 0/1/2 non seguiva "una logica di ordinamento" — sklearn assegna
le etichette grezze di K-means in un ordine arbitrario, senza legame con
la temperatura. Corretto **alla fonte**, non solo nel testo della
dashboard: `climate_clustering()` in `src/analysis/spatial_analysis.py`
ora rinumera le etichette per temperatura media crescente prima di
salvarle (0 = più fresco, 2 = più caldo — vedi
[Analisi Statistica](statistical-analysis.md)). La logica di
ordinamento-per-temperatura già scritta lato dashboard (paragrafo sopra)
resta com'era — ora è ridondante rispetto al dato già ordinato alla fonte,
ma non dannosa, ed è comunque una difesa in più se in futuro l'analisi
cambiasse. Aggiornati anche i colori: `CLUSTER_COLORS` in
`components/constants.py` passa da 3 colori categorici senza relazione
con la temperatura a blu→arancio→rosso (stessa logica della colormap di
temperatura usata altrove nel sito), e lo stesso schema colori è stato
applicato anche alla mappa QGIS `hotspot_analysis.qgz`
(`qgis_projects/build_maps.py`), rigenerata di conseguenza.

Indice di Moran: aggiunta la distinzione esplicita
rispetto ai cluster K-means (Moran guarda la geografia, K-means no), spiegato
il calcolo (peso inversamente proporzionale alla distanza tra comuni,
combinato con quanto ciascuno si discosta dalla media) e perché il p-value
viene da una permutazione (si mescolano le temperature a caso migliaia di
volte e si confronta il valore osservato con quelli casuali) invece che da
una formula diretta. **Metodologia** riscritta in domande e risposte, come
per Analisi Temporale.

### Ondate di Calore (`04_ondate_di_calore.py`) — ampliata il 2026-07-15
4 metriche in alto (n. ondate nel filtro attuale, n. ondate nell'ultimo
anno della finestra, durata media, intensità media). Tab **Panoramica**:
grafico a barre a doppio asse (n. eventi + durata media per anno);
intensità media per anno, con **legenda a 5 fasce** (2026-07-16, "Bassa" →
"Estrema" — i colori delle barre vengono campionati dalla stessa
colorscale Plotly del grafico, `plotly.colors.sample_colorscale()`, non
approssimati con una colormap diversa: legenda e barre garantite
identiche); **conteggio cumulato** dal 2000 per mostrare se il
fenomeno accelera; mappa di concentrazione geografica (coropletica per
comune, quante ondate nel filtro attuale, con **legenda a 5 fasce**
2026-07-16 — "Poche" → "Molto alto", stessa funzione
`render_gradient_legend()` delle altre mappe, qui con `integer=True` per
non mostrare range decimali su un conteggio di eventi); **heatmap "calendario"** (anno ×
giorno dell'anno, colore = quanti comuni in ondata quel giorno) per vedere
se gli eventi si spostano verso primavera/autunno. Tab **Dettaglio
tecnico**: confronto con una **definizione alternativa** di ondata di
calore a soglia percentile (relativa al singolo comune, non fissa per
tutti — vedi sotto), nota di metodologia. Sotto le tab, invariate: tabella
statistiche per comune ed elenco ondate.

**Testo esplicativo esteso nel tab Dettaglio tecnico (2026-07-16)**: stesso
trattamento già applicato ad Analisi Temporale e Analisi Spaziale ("stessa
cosa... con lo stesso pattern delle altre due pagine"). Spiegato in
linguaggio discorsivo perché esiste una definizione alternativa a soglia
percentile (la soglia fissa 35°C tratta tutti i comuni allo stesso modo,
penalizzando i comuni di montagna che raramente la raggiungono anche in
estati eccezionali per i loro standard), cos'è un percentile e come si
calcola in pratica (ordinare tutte le temperature massime storiche di un
comune, il 90° percentile è il valore sotto cui sta il 90% dei giorni —
diverso per ogni comune, a differenza dei 35°C fissi). **Metodologia**
riscritta in domande e risposte (perché il resto del sito usa comunque la
soglia fissa e non sostituisce mai i numeri ufficiali con quelli
percentile, perché la durata minima resta 3 giorni in entrambe le
definizioni per un confronto equo, cosa aggrega esattamente la heatmap
calendario) — stesso trattamento delle altre due pagine.

### Download Dati
Invariata: ogni file ha una descrizione in linguaggio semplice di cosa
contiene, oltre al bottone di export per i CSV di `data/processed/`,
`data/external/` e `output/`.

## Baseline delle anomalie: da configurabile a fissa (2026-07-15)

La prima versione lasciava scegliere all'utente inizio/fine della baseline
tramite due `number_input`. L'utente ha fatto notare che non aveva senso
lasciarla configurabile (aggiunge un dubbio — "che periodo scelgo?" — senza
un reale beneficio per chi guarda la pagina per capire il fenomeno, non per
esplorare scenari) e ha chiesto un parere: d'accordo con l'osservazione,
rimossi i due widget. Baseline ora **fissa** al primo decennio disponibile
per il comune selezionato (scelta standard in climatologia quando non è
disponibile il periodo di riferimento convenzionale 1961-1990/1991-2020 —
qui i dati partono dal 2000). Il testo sopra il grafico spiega ora
esplicitamente, in linguaggio semplice: cos'è un'anomalia, come si calcola,
perché quella baseline (non le altre) e come leggere le barre rosse/blu.

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

## Etichette leggibili per l'esito di Mann-Kendall (2026-07-15)

`pymannkendall` restituisce testualmente `'increasing'`/`'decreasing'`/
`'no trend'`. Mostrato così in dashboard, `'no trend'` viene facilmente
letto come "il clima è stabile qui", mentre significa "con 26 anni di dati
non c'è abbastanza evidenza statistica per dire se c'è un trend" — un
limite del test, non un'affermazione sul clima. Aggiunta
`components/constants.py::format_mk_trend()` (dizionario
`MK_TREND_LABELS`) che traduce l'esito in etichette con icona:
`📈 In aumento` / `📉 In diminuzione` / `🔍 Nessun trend chiaro`. Applicata
ovunque compare `mk_trend`: metrica in alto e tab "Dettaglio tecnico" di
`02_analisi_temporale.py`, tabella comparativa in `Home.py`.

## Tema e rifiniture estetiche (2026-07-15)

Su segnalazione esplicita dell'utente ("estetica bruttissima", testo delle
etichette lunghe come "🔍 Nessun trend chiaro" tagliato a metà dentro
`st.metric`):

- **`.streamlit/config.toml`** (nuovo): tema nativo Streamlit invece di CSS
  sparso — palette coerente (blu `#2563eb` come colore primario, sfondi e
  bordi neutri), supporto sia chiaro che scuro (`[theme]`/`[theme.dark]`,
  con sezioni `[theme.sidebar]`/`[theme.dark.sidebar]` dedicate), angoli
  arrotondati (`baseRadius`), bordo sui widget (`showWidgetBorder`), e una
  `chartCategoricalColors` allineata alla palette già usata nei grafici
  (`components/constants.py`). **Le chiavi non sono state copiate a
  memoria**: verificate una per una contro
  `.venv/Lib/site-packages/streamlit/config.py` della versione
  effettivamente installata (1.58.0), perché alcune (`baseRadius`,
  `showWidgetBorder`, `chartCategoricalColors`, le sezioni `[theme.dark]`)
  sono relativamente recenti e non esistono in versioni più vecchie di
  Streamlit.
- **`components/styling.py`** (nuovo, `inject_custom_css()`): la causa
  reale del testo tagliato è che `st.metric` applica `white-space: nowrap`
  + `text-overflow: ellipsis` al valore — pensato per numeri corti, non per
  etichette testuali come "Nessun trend chiaro" o nomi di comune lunghi
  come "Verbano-Cusio-Ossola". Il tema da solo non tocca questo dettaglio
  (è CSS applicato dal componente, non un colore/font del tema), quindi
  serve un piccolo override mirato: `white-space: normal` sul selettore
  `[data-testid="stMetricValue"]` (verificato — grep nei bundle JS di
  Streamlit installati, non un selettore indovinato — che questo
  `data-testid` esiste davvero in questa versione), così il testo va a
  capo su due righe invece di sparire. Chiamata una volta per pagina,
  subito dopo `st.set_page_config()`, in `Home.py` e in tutte le pagine di
  `pages/`.
- **Deliberatamente non fatto**: non sono stati cercati selettori CSS per
  "abbellire" i riquadri di `st.container(border=True)` (card della home) —
  Streamlit li renderizza con classi generate dinamicamente
  (`st-emotion-cache-*`), non con un `data-testid` stabile; un selettore
  indovinato si sarebbe rotto al primo aggiornamento di Streamlit. Il loro
  aspetto (angoli arrotondati, bordo) viene comunque dal nuovo
  `baseRadius`/`borderColor` del tema, che si applica "alla maggior parte
  degli elementi UI" a livello di framework, senza bisogno di CSS fragile.

**Verifica**: tutte le pagine compilate (`py_compile`) e ri-verificate con
`AppTest` (nessuna eccezione) dopo l'aggiunta di `inject_custom_css()`;
server live riavviato (i cambi a `.streamlit/config.toml` richiedono un
riavvio completo, non bastano l'hot-reload di Streamlit) e verificato con
un solo processo in ascolto sulla porta 8501 (vedi bug dei processi
duplicati sotto).

## Come verificare senza aprire un browser

`streamlit.testing.v1.AppTest` esegue davvero lo script Streamlit
in-process e permette di ispezionare eccezioni ed elementi renderizzati:

```python
from streamlit.testing.v1 import AppTest
at = AppTest.from_file('dashboard/Home.py', default_timeout=30)
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
  Fix: bootstrap esplicito (`sys.path.insert(0, ...)`) in cima a `Home.py`
  (allora `app.py`) e a ogni pagina in `pages/`, prima di importare da
  `components`.
- **`folium.GeoJson()` non accetta WKT grezzo**: passargli direttamente la
  stringa WKT letta dal DB fa sì che `folium`/`branca` provino ad aprirla
  come se fosse un percorso file (`OSError: Invalid argument`). Fix:
  `components/maps.py::wkt_to_geojson()` converte WKT → dict GeoJSON via
  `shapely.wkt.loads` + `shapely.geometry.mapping` prima di passarlo a
  `folium.GeoJson`.
- **`use_container_width` deprecato**: la versione di Streamlit installata
  (1.58.0) l'ha già superato come data di rimozione annunciata — sostituito
  con `width='stretch'` in tutte le occorrenze.
- **Processi Streamlit residui dopo la rinomina `app.py` → `Home.py`**: dopo
  il rename, l'utente continuava a vedere in browser
  `FileNotFoundError: dashboard\app.py` nonostante il server fosse stato
  riavviato puntando a `Home.py`. Causa: sessioni di verifica precedenti
  avevano lasciato **4 processi Streamlit avviati in background** ancora
  vivi sulla stessa porta 8501 (due dei quali puntavano ancora al vecchio
  `app.py`, cancellato) — il tentativo di stop di un turno precedente aveva
  chiuso solo un PID, non tutti. Diagnosticato con
  `Get-CimInstance Win32_Process | Where CommandLine -match streamlit`
  (mostra la riga di comando completa per PID, non solo il nome immagine),
  non riproducibile con `AppTest` (che non avvia un vero server HTTP).
  Risolto terminando tutti i processi trovati e riavviandone uno solo,
  verificato con `Get-NetTCPConnection -LocalPort 8501` che un solo PID
  fosse in ascolto.

## Dipendenze

Tutte già in `requirements.txt` (`streamlit`, `streamlit-folium`, `folium`,
`plotly`). **Allineate il 2026-07-15** alle versioni effettivamente
installate nel `.venv` (streamlit 1.58.0, non più 1.29.0 pinnato — vedi
[Stato del Progetto](project-status.md) per l'elenco completo del drift
risolto in tutto `requirements.txt`, non solo per la dashboard). Le mappe
coropletiche aggiunte il 2026-07-15 usano `branca.colormap.LinearColormap`
(già presente come dipendenza transitiva di `folium`, non serve aggiungerla
a `requirements.txt`).

# Articolo scientifico — piano e stato

**Sorgenti**: decisione dell'utente in conversazione (2026-07-16), non
derivata da codice. Letteratura raccolta via ricerca web nella stessa
sessione. Riferimenti incrociati: [Stato del progetto](project-status.md),
[Analisi statistica e spaziale](statistical-analysis.md),
[Fonti dati](data-sources.md).

Questa pagina traccia l'obiettivo di trasformare il progetto in un articolo
scientifico, target una rivista o conferenza peer-reviewed (non solo
portfolio). È una pagina di **pianificazione**, diversa dalle altre pagine
della wiki che descrivono codice esistente — va aggiornata mano a mano che
il piano diventa lavoro reale (a quel punto il dettaglio tecnico andrà anche
nelle pagine di dominio, es. `data-model.md`/`data-sources.md` quando
arriveranno nuove tabelle/fonti).

## Decisione (2026-07-16)

L'idea originale dell'utente: correlare le zone più calde/meno calde del
Piemonte alle cause (grandi città, industria, riscaldamento domestico).
Data la scelta tra un taglio solo descrittivo e uno anche esplicativo, e tra
portfolio/preprint/rivista vera, l'utente ha scelto:

- **Ambizione**: articolo completo, descrittivo **+** esplicativo (non solo
  uno dei due).
- **Target**: rivista o conferenza peer-reviewed vera, non solo un documento
  da portfolio.

## Perché non è solo "scrivere quello che abbiamo"

Il DB oggi ha temperatura giornaliera 2000-2025, elevazione (solo per i
comuni con temperatura), geometrie amministrative per tutti i 1180 comuni,
Moran's I e clustering K-means già calcolati e statisticamente significativi
(vedi [Analisi statistica](statistical-analysis.md)). **Non ha ancora** uso
del suolo, popolazione (`municipalities.population` è `NULL` su tutti i 1180
comuni) o dati industriali — cioè esattamente le variabili esplicative
richieste dall'idea originale. Il confronto "isola di calore urbana" già
presente in dashboard (`03_analisi_spaziale.py`) è dichiarato esplicitamente
"solo illustrativo" (Torino vs media provincia), non un vero studio UHI.

## Le 5 fasi del piano

1. **Validazione contro dati stazione reali (ARPA Piemonte)** — priorità
   alta. Le temperature Open-Meteo sono derivate da reanalisi/modello, non
   osservazioni dirette; un revisore lo contesterebbe per primo.
   `ArpaPiemonteDownloader` esiste già in `src/data_acquisition/download_data.py`
   ma **l'URL configurato (`config.yaml`, `arpa_piemonte.url`) risponde 404**
   (verificato il 2026-07-16, HTTP diretto) — stesso tipo di bug placeholder
   già trovato per l'URL ISTAT dei confini comunali il 2026-07-04. I dati
   reali non hanno un endpoint CSV/API diretto: stanno dietro un'interfaccia
   a mappa (`webgis.arpa.piemonte.it/.../map_meteoweb`, pagina
   "Banca Dati Storica") o una richiesta manuale ("Richiesta dati meteo
   idro nivologici"). Va investigato se l'interfaccia a mappa espone un'API
   JSON sottostante (come successo in passato con altri bug di questo
   progetto), altrimenti resta una fase a maggior costo di quanto previsto.
2. **Estendere il campione di comuni con temperatura** oltre gli attuali
   44/1180, per dare potenza statistica a una regressione multivariata **—
   in corso**: l'utente sta estendendo la copertura a 300 comuni tramite
   `src/data_acquisition/download_extra_municipalities.py` (vedi
   [Fonti dati](data-sources.md) per il dettaglio della corsa a 44; questa
   nuova corsa a 300 va documentata separatamente quando completa e caricata
   nel DB).
3. **Acquisire le covariate esplicative mancanti**:
   - Uso del suolo (Copernicus CORINE Land Cover) — overlay via PostGIS
     sulle geometrie comunali già presenti per tutti i 1180 comuni, per
     ottenere % superficie urbana/artificiale, agricola, forestale per
     comune. Non richiede nuovi download di temperatura.
   - Popolazione residente — **fatto il 2026-07-16**. Dopo due vicoli ciechi
     (l'API SDMX `esploradati.istat.it` ha la struttura giusta — stessi
     codici `istat_code`, dataflow Piemonte-specifico identificato
     `22_315_DF_DCIS_POPORESBIL1_3` — ma non restituisce osservazioni reali
     per questo dataset; il portale legacy `dati.istat.it` è dismesso,
     redirect a un avviso di decommissioning), trovato `demo.istat.it`
     (sistema attivo e separato, ZIP scaricabile per provincia, nessun
     account) — vedi [Fonti dati](data-sources.md) per il dettaglio
     completo. Script `src/data_acquisition/download_population.py`,
     eseguito su tutte le 8 province: **1180/1180 comuni aggiornati**
     (`municipalities.population`), non solo quelli con temperatura.
     Valori verificati plausibili (Torino 6580 ab/km², Formazza alpina
     3.1 ab/km²).
   - CORINE Land Cover — **fatto il 2026-07-16**. Via manuale (non API,
     vedi sopra la motivazione): l'utente ha scaricato
     `U2018_CLC2018_V2020_20u1.gpkg` (52.794 poligoni, EPSG:3035) via
     "Download by area" su `land.copernicus.eu`. Overlay geopandas
     (`src/data_acquisition/process_land_cover.py`, ~16 secondi per tutti
     i 1180 comuni) → nuova tabella `municipality_land_cover` con %
     urbano/agricolo/forestale/zone umide/acqua per comune. Risultati
     verificati plausibili: Torino 75% urbano, Verbania 41% acqua (sul
     Lago Maggiore), Vercelli/Alessandria/Cuneo/Asti 67-84% agricolo,
     Bardonecchia/Formazza >94% forestale. Vedi [Fonti dati](data-sources.md)
     per il dettaglio completo (inclusi i due tentativi prima del file
     giusto: la prima cartella era solo documentazione, senza geometrie).
   - Entrambe indipendenti dall'estensione a 300 comuni: operano su tutti i
     1180 comuni già in `municipalities`, non solo su quelli con
     temperatura.
4. **Modellazione statistica** — **prima iterazione fatta il 2026-07-17**
   (`src/analysis/spatial_regression.py`), non appena popolazione/CORINE/NDVI
   sono state tutte disponibili per i 63 comuni con temperatura. OLS
   classico (elevazione+popolazione+%urbano+NDVI, VIF tutti <5) →
   Moran's I sui residui ancora significativo (I=0.081, p=0.001) → modello
   a **errore spaziale** (via `spreg`/`libpysal`, regola di Anselin non
   ambigua: LM-error fortemente significativo anche robusto, LM-lag no).
   Risultato piu' rilevante a n=63: **% urbano diventa significativo con
   il segno atteso solo nel modello spaziale** (l'OLS classico lo
   mascherava) — prima conferma quantitativa, seppur provvisoria (n=63, da
   rifare al crescere del campione), dell'ipotesi originale del paper.
   NDVI resta significativo ma con segno controintuitivo (piu' verde →
   piu' caldo), da indagare. **Rieseguito lo stesso giorno (pomeriggio) su
   n=98** dopo l'import di 35 comuni extra da una seconda macchina (vedi
   [Fonti dati](data-sources.md)): a campione piu' ampio **% urbano non e'
   piu' significativo** (p=0.334, coefficiente ancora positivo ma piccolo)
   — il risultato di n=63 non si e' confermato. NDVI resta significativo
   con lo stesso segno controintuitivo. Onesto registrare il cambio invece
   di tenere solo il risultato "piu' favorevole": con un campione ancora
   piccolo per la spatial econometrics, questo genere di risultato non
   robusto al variare di n va aspettato e discusso nel paper stesso, non
   nascosto. Dettaglio completo, incluso il caveat sulla sensibilita'
   alla matrice pesi spaziale, in
   [Analisi statistica](statistical-analysis.md).
5. **Percorso di pubblicazione realistico senza affiliazione accademica**:
   preprint (arXiv/EarthArXiv, gratuito e citabile subito) → conferenza SISC
   (Società Italiana per le Scienze del Clima, barriera d'ingresso bassa per
   ricercatori indipendenti/studenti) → eventualmente rivista (candidate:
   *Urban Climate*, *Theoretical and Applied Climatology*, *Climate*/
   *Atmosphere* di MDPI con richiesta di waiver sull'APC).

## Letteratura raccolta (2026-07-16)

Da citare, organizzata per ruolo nel paper:

- **Definizione di ondata di calore/metriche**: Perkins & Alexander (2013,
  J. Climate, *On the Measurement of Heat Waves*) — definizione a
  percentile 90°, già discussa nel tab "Dettaglio tecnico" della dashboard
  (vedi [Dashboard](dashboard.md), `components/heatwave_definitions.py`);
  Nairn & Fenwick, *The Excess Heat Factor* — metrica alternativa
  all'`intensity_index` del progetto.
- **UHI a Torino/Piemonte** (il più vicino a quello che vuole fare
  l'utente): Garzena et al. (2019, *Weather*/Wiley) — 147 anni di dati,
  Torino vs stazioni rurali; *An innovative approach to select
  urban-rural sites for UHI analysis: the case of Turin* (Urban Climate) —
  metodologia di selezione siti; *Characterization of the Urban Heat and
  Dry Island effects in the Turin metropolitan area* (Urban Climate) — 20
  anni di dati orari ARPA Piemonte; studio numerico su UHI a Torino durante
  l'ondata di calore 2019 (pattern termici e circolazione locale, incluso
  il Foehn).
- **Uso del suolo → temperatura** (template metodologico per la fase 3-4):
  *Surface urban heat islands in Italian metropolitan cities: Tree cover
  and impervious surface influences* (Sci. Total Environ.) — quantifica
  +4°C di SUHI ogni +10% di superficie impermeabile, regressione con
  CORINE Land Cover su città italiane; Frontiers, *Mapping urban heatwaves
  and islands: the reverse effect of Salento's "white cities"* — caso
  controintuitivo utile per la discussione su fattori mitiganti.
- **Contesto climatico regionale/nazionale** (per l'introduzione): +7.5
  giorni/decade di ondate di calore in Italia; +134% eventi di caldo
  estremo estivo nel trentennio 1991-2020 vs 1961-1990 nel Nord
  Italia/Arco Alpino; *Changes in large-scale circulation behind the
  increase in extreme heat events in the Apennines* (2025); variabilità
  termica Po Valley da radiosondaggi (arXiv).

## Idee da esplorare (non implementate, tracciate il 2026-07-16)

Discusse con l'utente, non ancora avviate — l'utente ha scelto di procedere
prima con la scomposizione urbana (vedi sopra) e di aspettare i 300 comuni
prima del resto.

**1. Aggiungere popolazione/uso del suolo alla dashboard — fatto il
2026-07-16.** Mappa uso del suolo dominante e mappa densità di popolazione
(tutti i 1180 comuni), più uno scatter temperatura/uso del
suolo/popolazione con selettore di variabile, che sostituisce il vecchio
confronto "isola di calore urbana" (Torino vs media provincia, dichiarato
"solo illustrativo"). Dettaglio completo in [Dashboard](dashboard.md).

**2. Altre covariate esplicative candidate**, in ordine di sforzo
crescente:
- NDVI/verde da satellite — **fatto (2026-07-17)**. Scartato Sentinel-2
  vero (10m, via Google Earth Engine o Copernicus Data Space Ecosystem
  Statistical API) a favore di Copernicus Global Land Service NDVI 300m V3
  (prodotto gia' calcolato, stesso pattern low-effort di CLC), decisione
  presa con l'utente — un'apparente scorciatoia verso un prodotto NDVI
  10m reale (HR-VPP) si e' rivelata un vicolo cieco (non raggiungibile dal
  Copernicus Browser). `municipality_ndvi` popolata per tutti i 1180
  comuni. Dettaglio completo (incluse le difficolta' reali del portale di
  download e la verifica empirica scala/offset/flag sul file) in
  [Fonti dati](data-sources.md) e [Modello dati](data-model.md).
- Pendenza ed esposizione del versante da un DEM (es. Copernicus GLO-30) —
  più dettagliato della sola elevazione del centroide già disponibile; un
  versante esposto a sud scalda diversamente da uno a nord, specie in
  montagna.
- Distanza dal Po/dai laghi — più precisa dell'attuale `pct_water` (che è
  0 per la maggior parte dei comuni pur essendo vicini all'acqua senza
  contenerla).
- Densità stradale/edificato da OpenStreetMap — proxy di traffico/
  urbanizzazione; il progetto ha già un `OpenStreetMapDownloader` in
  `src/data_acquisition/download_data.py`, mai attivato di default (vedi
  [Fonti dati](data-sources.md)).

## Manoscritto

Lo scheletro vero e proprio del paper (Abstract/Intro/Metodi/Risultati/
Discussione/Bibliografia, con marcatori **[FATTO]**/**[DA FARE]** per
distinguere cosa si basa su risultati reali già calcolati da cosa dipende
da lavoro non ancora completato) vive in `paper/manoscritto.md`, non in
questa pagina wiki — questa pagina resta il livello di pianificazione/
tracciamento, il file in `paper/` è il contenuto del paper stesso. Creato
il 2026-07-16, in italiano (da tradurre in inglese solo a ridosso della
sottomissione).

## Prossimi passi

Vedi [Stato del progetto](project-status.md) per lo stato operativo
aggiornato di ETL/analisi. Con popolazione, uso del suolo e ora anche NDVI
fatti (2026-07-16/17), e con una prima iterazione del modello statistico
fatta il 2026-07-17 (vedi punto 4 sopra), restano aperti:
(a) l'estensione del campione di comuni con temperatura (in corso lato
utente, gradualmente — 44→63→98 al 2026-07-17, vedi
[Fonti dati](data-sources.md)) — priorita' alta anche per la
modellazione: n=98 resta piccolo per la spatial econometrics (e il
risultato sull'% urbano non e' stato stabile passando da 63 a 98, vedi
punto 4 sopra), il campione crescente andra' rilanciato attraverso
`spatial_regression.py` via via che arrivano nuovi comuni;
(b) la validazione ARPA (mai risolta, vedi fase 1 sopra) — resta la
priorita' piu' alta in assoluto, dato che le temperature Open-Meteo sono
dati di rianalisi/modello (spazialmente "lisci" per costruzione), il che
potrebbe spiegare parte dell'autocorrelazione residua ancora vista nel
modello spaziale;
(c) approfondire il segno controintuitivo di NDVI nel modello (vedi punto
4) prima di scriverlo nel manoscritto come risultato consolidato.
Il file `paper/manoscritto.md` va aggiornato in parallelo.

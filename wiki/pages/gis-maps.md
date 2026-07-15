# Mappe GIS (QGIS)

**Sorgenti**: `qgis_projects/build_maps.py`, `qgis_projects/create_temporal_view.py`,
`qgis_projects/*.qgz`

Stato: **implementate ed eseguite il 2026-07-15**, generate via PyQGIS
(non manualmente da QGIS Desktop) e verificate con render offscreen prima
di consegnarle, dato che aprirle visivamente richiede QGIS Desktop
(strumento che l'IA non può usare direttamente).

| Mappa | Descrizione | Stato |
|---|---|---|
| `temperature_heatmap.qgz` | Coropletica della temperatura media 2000-2025 sugli 8 comuni capoluogo | ✅ generata e verificata |
| `hotspot_analysis.qgz` | Cluster climatici K-means (k=3, da `spatial_analysis.py`) | ✅ generata e verificata |
| `evolution_animation.qgz` | Animazione temporale 2000-2025 (controllo temporale nativo QGIS) | ✅ generata e verificata (frame 2000 vs 2025 confermano il riscaldamento) |
| Heatwave Index (composito intensità/frequenza) | Non implementata | ⬜ pianificata, non fatta in questa sessione |

**Nota di granularità**: tutte le mappe mostrano gli **8 comuni capoluogo
con dati reali** a colori, sopra uno sfondo grigio con tutti i 1180 comuni
piemontesi (da `data/external/istat_municipalities.geojson`/tabella
`municipalities`), per essere onesti sulla copertura reale invece di
nasconderla. Vedi [ETL](etl-pipeline.md) per la motivazione.

## Come sono state generate

`qgis_projects/build_maps.py` è uno script **PyQGIS**, eseguito con
l'interprete Python *bundled* di QGIS (non il venv del progetto):

```
"C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat" qgis_projects\build_maps.py
```

Inizializza `QgsApplication` in modalità headless (`QT_QPA_PLATFORM=offscreen`,
niente GUI), costruisce i layer (da PostgreSQL/PostGIS + join con i CSV di
`output/` prodotti da `src/analysis/`), applica lo stile, e salva ogni
progetto come `.qgz`. Prerequisito: `python -m qgis_projects.create_temporal_view`
(venv del progetto) per creare `kpi_temporal_view`, usata dalla mappa 3
(vedi sotto).

## Verifica senza aprire QGIS Desktop

Analogamente a `streamlit.testing.v1.AppTest` per la dashboard, `build_maps.py`
renderizza ogni progetto offscreen in PNG (`qgis_projects/previews/*.png`)
via `QgsMapRendererParallelJob`, permettendo un'ispezione visiva diretta
dei colori/dati senza QGIS Desktop. Per la mappa temporale, sono stati
renderizzati due frame (2000 e 2025) e confrontati: differiscono
chiaramente (2025 uniformemente più rosso/caldo di 2000), confermando che
il filtro temporale funziona davvero, non solo che il layer esiste.

**Limite di questa verifica**: l'ambiente Qt "offscreen" usato per il
render non ha alcun font di sistema registrato
(`QFontDatabase().families()` restituisce una lista vuota) — le etichette
dei comuni appaiono come rettangoli tratteggiati invece che testo nelle
anteprime PNG. Verificato che non è un problema di configurazione delle
etichette (stesso risultato con `QPainter` puro, senza QGIS) ma un limite
del backend di rendering headless. Le etichette sono comunque configurate
correttamente nel progetto salvato: **quando aperto in QGIS Desktop
normale (rendering non headless) dovrebbero apparire come testo**, ma
questo va confermato aprendo i file .qgz tu stessa — è l'unica parte che
non ho potuto verificare end-to-end.

## Bug trovati costruendo le mappe (2026-07-15)

- **Nome di campo joinato sbagliato**: `QgsVectorLayerJoinInfo.setPrefix('')`
  fa sì che i campi del CSV joinato mantengano il **nome originale**, non
  un prefisso `nome_layer_` come assunto inizialmente — il renderer
  referenziava campi inesistenti (`spatial_analysis_temp_mean_avg` invece
  di `temp_mean_avg`), fallendo silenziosamente (nessun colore visibile,
  nessun errore Python). Trovato confrontando `layer.fields()` prima e
  dopo il join.
- **Subquery SQL come `table=` in `QgsDataSourceUri` non funziona**:
  passare `table="(SELECT ...) AS alias"` (con o senza `setDataSource()`
  vs `setTable()`) fa sì che QGIS metta tra virgolette l'**intera stringa**
  come un unico identificatore invece di eseguirla come SQL — il layer
  risulta invalido con **nessun messaggio d'errore visibile** dalle normali
  API Python (`layer.error()` vuoto). Diagnosticato solo collegandosi al
  message log di QGIS (`QgsApplication.messageLog().messageReceived`), che
  ha rivelato l'errore Postgres reale
  (`la relazione "(SELECT ... non esiste`). **Fix**: creata una vista
  Postgres reale (`kpi_temporal_view`, via
  `qgis_projects/create_temporal_view.py`) invece di una subquery inline —
  una vista in catalogo si comporta come qualunque tabella, senza ambiguità.
- **Nessun font nell'ambiente offscreen**: vedi sopra.
- **Pagina bianca aprendo i `.qgz` in QGIS Desktop** (segnalato dall'utente
  dopo aver aperto i file): `QgsProject.write()` non salva alcuna
  estensione di vista (`<mapcanvas>`/`DefaultViewExtent`) a meno di
  impostarla esplicitamente — il render offscreen usato per le anteprime
  imposta l'estensione solo su `QgsMapSettings` (transiente, non salvata
  nel progetto), quindi i progetti salvati aprivano senza sapere su quale
  area centrare la mappa. Fix: `set_project_view_extent()` in
  `build_maps.py` imposta `project.viewSettings().setDefaultViewExtent(...)`
  sull'estensione combinata dei layer prima di salvare, per ciascuno dei 3
  progetti. Verificato leggendo l'XML del `.qgz` salvato (`DefaultViewExtent`
  ora presente coi confini reali del Piemonte).
- **Etichette mancanti in `evolution_animation.qgz`** (segnalato
  dall'utente dopo aver aperto tutti e 3 i file — le etichette si vedevano
  correttamente nelle prime due mappe ma non nella terza): non un problema
  di rendering, semplicemente `add_labels()` non era mai stata chiamata
  sul layer temporale in `build_evolution_animation()` — dimenticata,
  non un bug di configurazione. Fix: aggiunta con espressione
  `"name" || ' (' || round("temp_mean_annual", 1) || '°C)'`, così la
  temperatura mostrata in etichetta cambia insieme al colore a ogni anno
  dell'animazione. Verificato leggendo l'XML del `.qgz` salvato (nodo
  `<labeling type="simple">` ora presente, prima assente).

## Prossimi passi

- Aprire i 3 `.qgz` in QGIS Desktop per confermare visivamente le
  etichette (unico aspetto non verificabile in modo automatico)
- Eventualmente costruire la mappa "Heatwave Index" (non fatta in questa
  sessione)
- Se si vuole coprire più degli 8 comuni capoluogo, serve prima scaricare
  temperature reali per altri comuni (vedi [Analisi Statistica](statistical-analysis.md))

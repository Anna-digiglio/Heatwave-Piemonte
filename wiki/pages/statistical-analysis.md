# Analisi statistica e spaziale (`src/analysis/`)

**Sorgenti**: `src/analysis/trend_analysis.py`, `src/analysis/heatwave_stats.py`,
`src/analysis/seasonal_analysis.py`, `src/analysis/spatial_analysis.py`,
`src/analysis/spatial_regression.py`, `src/analysis/validate_arpa.py`.

## Validazione contro ARPA Piemonte (2026-07-18, estesa il 2026-07-19, copertura completa il 2026-07-23)

Fase 1 del piano paper ([Articolo scientifico](paper-scientifico.md)),
priorità più alta — le temperature usate in tutto il resto di questa pagina
sono stime Open-Meteo (rianalisi/modello), non osservazioni dirette.
`src/analysis/validate_arpa.py` confronta, per i comuni con una stazione
ARPA reale corrispondente (vedi [Fonti dati](data-sources.md) per come sono
stati trovati/scaricati), le due serie sullo stesso `(comune, data)`.

**Aggiornamento 2026-07-23 — copertura ARPA completa, 218/218 comuni**:
dopo il giro unico di import (177→599 comuni Open-Meteo, vedi [Comuni già
coperti](comuni-coperti.md)), **tutti i 218 comuni con stazione ARPA
attiva hanno ora anche Open-Meteo** — il campione di validazione è
completo, non più un sottoinsieme (era 51 il 2026-07-18, 108 il
2026-07-19, ora 218/218).

**Risultato aggregato su `temp_max`** (2.068.072 coppie di osservazioni,
2000-2026):

| Metrica | Valore |
|---|---|
| Correlazione di Pearson (r), media sui 218 comuni | **0.968** |
| Bias medio (Open-Meteo − ARPA) | **-1.52 °C** |
| MAE medio | 2.50 °C |
| RMSE medio | 2.98 °C |

La correlazione è molto alta — Open-Meteo segue bene la variabilità
giorno-per-giorno reale — ma c'è un **bias sistematico negativo**:
Open-Meteo sottostima le temperature massime reali di circa 1.5°C in
media, con un range molto ampio per comune (da +4.35°C a Sampeyre a
**-7.69°C a Cossogno**, entrambi comuni alpini/prealpini — il bias non è
uniforme nemmeno in direzione). Il bias medio (-1.52°C) resta pressoché
invariato attraverso tutti e 3 gli allargamenti del campione (-1.71°C →
-1.59°C → -1.52°C), conferma solida che non è un artefatto di un campione
piccolo.

**Il bias correla con l'elevazione** (r=-0.296, p=0.000009, n=218,
ricontrollato sul campione completo incrociando `output/arpa_validation.csv`
con `municipalities.elevation_m` — correlazione leggermente più debole ma
significatività fortissima con il campione pieno): più alto il comune,
più negativo il bias — cioè più Open-Meteo sottostima le massime reali.
Interpretazione plausibile (non a livello di certezza): un prodotto di
rianalisi rappresenta una cella di griglia, non un punto — in rilievo
alpino complesso questo media esposizioni/quote diverse dentro la stessa
cella, smussando le temperature estreme che una stazione puntuale osserva
davvero. Questo è coerente con l'autocorrelazione spaziale residua già
vista nel modello a errore spaziale (vedi sotto) — un dato di rianalisi
"liscio per costruzione" può contribuire a quel residuo, come già
ipotizzato in [Articolo scientifico](paper-scientifico.md) prima ancora di
avere questo controllo empirico.

### Bias sui giorni davvero caldi (2026-07-18, aggiornato 2026-07-23)

Il bias medio sopra è calcolato su tutti i giorni dell'anno — ma il
progetto misura ondate di calore, non temperatura media. Ristretto ai
giorni **realmente caldi** (soglia su `arpa_temp_max`, ARPA come verità di
terra, tutti i 218 comuni aggregati):

| Condizione | n giorni | Bias | MAE | RMSE | r |
|---|---|---|---|---|---|
| Tutti i giorni | 2.047.067 | -1.47°C | 2.51°C | 3.25°C | 0.948 |
| ARPA temp_max > 30°C | 110.357 | -2.38°C | 2.60°C | 3.20°C | **0.618** |
| ARPA temp_max > 35°C | 8.808 | -2.64°C | 2.82°C | 3.44°C | **0.375** |

Il bias medio non peggiora drammaticamente sui giorni caldi (-1.47°C →
-2.64°C), ma la **correlazione crolla** (0.948 → 0.375): Open-Meteo continua
a sottostimare di circa la stessa quantità, ma perde quasi completamente la
capacità di distinguere *quali* giorni estremi lo sono davvero di più
rispetto ad altri, proprio nella fascia che definisce le ondate di calore.
Pattern confermato su tutti e 3 gli allargamenti del campione (0.956 →
0.400 → 0.393 → 0.375 sui giorni >35°C).

### Confronto a livello di evento: quante ondate di calore "vere" mancano? (2026-07-18, aggiornato 2026-07-23)

Il test più diretto: `identify_heatwaves()` (stessa logica del DB — ≥3
giorni consecutivi con temp_max > 35°C — reimplementata in Python su
`arpa_temperature` in `identify_heatwaves_from_series()`) applicata ai dati
ARPA (verità di terra) per i 218 comuni, confrontata con le ondate già in
`heatwave_events` (da Open-Meteo) per **gli stessi comuni**, per
sovrapposizione temporale (non serve che le date coincidano esattamente).

| | Conteggio |
|---|---|
| Ondate reali (ARPA) | **1.185** |
| Ondate rilevate da Open-Meteo | **459** |
| Precision (delle ondate OM, quante sono confermate da ARPA) | 63.6% |
| Recall (delle ondate reali, quante OM cattura) | **25.2%** |

Risultato più rilevante di tutta la validazione — e questa volta
**migliorato** rispetto al campione intermedio: recall 16.4% (108 comuni,
2026-07-19) → **25.2%** (218 comuni, campione ARPA completo). Non è
monotono: era 31.4% sui 51 comuni originali, sceso a 16.4% con i 57
aggiunti (comuni scelti per avere ARPA, non per caratteristiche
climatiche), risalito a 25.2% col completamento a 218. La spiegazione più
plausibile è semplice: il valore sui 51/108 comuni era una stima rumorosa
su un campione piccolo e non rappresentativo (selezionato per
disponibilità di stazione ARPA, non casualmente) — il valore a campione
completo (218/218, l'intero universo ARPA disponibile) è il più
affidabile dei tre. Resta comunque **basso in assoluto**: Open-Meteo
rileva circa un quarto delle ondate di calore realmente accadute,
coerente col bias negativo sistematico. Anche le ondate che Open-Meteo
rileva non sono tutte "vere": il 36.4% (100% - 63.6% precision, stabile)
non trova riscontro in un evento ARPA sovrapposto nello stesso comune.
Implicazione diretta per il paper: le **2.192 ondate totali già contate su
599 comuni sono quasi certamente un sottoconteggio sostanziale** del
fenomeno reale, non solo un numero "conservativo" — da dichiarare
esplicitamente come limite quantificato (fattore ~4×, non ~3× come si
poteva pensare prima), non solo qualitativo. Dettaglio per evento in
`output/arpa_heatwave_events.csv`; bias per condizione in
`output/arpa_hot_day_bias.csv`.

### Il trend di riscaldamento regge sui dati di stazione reali (2026-07-18, aggiornato 2026-07-23)

A differenza dell'accuratezza giornaliera e del conteggio delle ondate
(entrambi problematici, vedi sopra), **il trend di riscaldamento resta
robusto alla fonte dei dati** anche sul campione ARPA completo — ma con
una sfumatura nuova rispetto ai due aggiornamenti precedenti (vedi sotto).
Rieseguiti Mann-Kendall + regressione lineare (stesse funzioni pure di
`trend_analysis.py`) sulla media annuale ARPA per i 218 comuni, confrontati
con `output/trend_analysis.csv` (Open-Meteo) già calcolato:

| Metrica | Valore |
|---|---|
| Segno della pendenza concorde ARPA/Open-Meteo | **92.7%** (202/218 comuni) |
| Trend ARPA significativo (p<0.05) | 175/218 |
| Trend Open-Meteo significativo (p<0.05) | 201/218 |
| Entrambi significativi | 160/218 |
| Differenza media di pendenza (OM − ARPA) | **+0.148 °C/decade** (sd=0.475) |

**Nota importante**: il segno della differenza media di pendenza si è
**invertito** rispetto ai due aggiornamenti precedenti (-0.095°C/decade a
51 comuni, -0.096°C/decade a 108, ora **+0.148°C/decade** a 218) — prima
Open-Meteo sottostimava leggermente il trend rispetto ad ARPA, ora lo
sovrastima leggermente. La differenza resta piccola rispetto alla
dispersione dei trend stessi, ma l'inversione di segno con un campione
più che raddoppiato (non solo un cambio di magnitudine) è un segnale che
questo confronto specifico non si era ancora stabilizzato ai campioni
precedenti — da trattare con cautela nel paper: il messaggio qualitativo
("i due trend sono simili") tiene, il numero preciso di scarto no.
Concordanza di segno invece stabile e alta in tutti e 3 i campioni
(88.2% → 90.7% → 92.7%).

<details>
<summary>Numeri superati (51 e 108 comuni, tenuti per confronto storico)</summary>

| Metrica | 2026-07-18 (51) | 2026-07-19 (108) | 2026-07-23 (218) |
|---|---|---|---|
| Segno della pendenza concorde | 88.2% (45/51) | 90.7% (98/108) | 92.7% (202/218) |
| Trend ARPA significativo (p<0.05) | 43/51 | 94/108 | 175/218 |
| Trend Open-Meteo significativo (p<0.05) | 40/51 | 91/108 | 201/218 |
| Entrambi significativi | 35/51 | 80/108 | 160/218 |
| Differenza media di pendenza (OM − ARPA) | -0.095 °C/decade | -0.096 °C/decade | **+0.148 °C/decade** |

Il segno della differenza di pendenza si inverte proprio tra il secondo e
il terzo campione — vedi la nota sopra. La concordanza di segno resta
invece stabile e in crescita in tutti e 3 gli allargamenti.

**Implicazione per il paper**: il risultato principale ("riscaldamento
diffuso e significativo, segno concorde tra le fonti nel 92.7% dei casi")
non è un artefatto della fonte dati Open-Meteo — a differenza del
conteggio delle ondate di calore, che invece va corretto/qualificato
esplicitamente, e a differenza dello scarto medio di pendenza, la cui
inversione di segno consiglia di riportare solo il risultato qualitativo
(concordanza di segno), non la cifra esatta dello scarto, finché non si
osserva se si stabilizza a campioni futuri. Dettaglio per comune in
`output/arpa_trend_comparison.csv`.

</details>

**Caveat**: la stazione ARPA scelta per ciascun comune è quella più vicina
per *quota* al centroide comunale, non necessariamente rappresentativa
dell'intero territorio comunale (specie nei comuni alpini estesi, dove la
stazione può essere un rifugio a un'altitudine molto diversa dal fondovalle
abitato). ~2% dei valori ARPA sono nulli (sensori più vecchi con copertura
non uniforme) — esclusi dal confronto via `dropna()` per coppia, non
imputati. Dettaglio per comune in `output/arpa_validation.csv`.

Implementata ed eseguita per la prima volta su dati reali il 2026-07-15,
dopo che la pipeline ETL (vedi [ETL](etl-pipeline.md)) aveva reso
disponibili 75.976 righe di temperatura, 51 ondate di calore e le viste
KPI popolate.

**Granularità**: 8 comuni capoluogo → 44 comuni (2026-07-15) → 63 comuni
(2026-07-17 mattina) → 98 comuni (2026-07-17 pomeriggio, dopo l'import di
35 comuni scaricati da una seconda macchina) → 155 comuni (2026-07-18
mattina, altri 57 dalla stessa collaboratrice) → **177 comuni (2026-07-18,
+22 scaricati direttamente)** — sempre con lo stesso campionamento
"farthest-point" per copertura spaziale, vedi [ETL](etl-pipeline.md). Dal
2026-07-17 il periodo coperto arriva anche **fino a oggi**, non più fermo
al 31/12/2025. → **234 comuni (2026-07-19)** → **599 comuni (2026-07-23)**,
ultimo giro di import (vedi [Comuni già coperti](comuni-coperti.md) e
[Stato del progetto](project-status.md)). I numeri delle sezioni per
modulo sotto sono aggiornati alla versione a 177 comuni (con confronto
storico); i risultati aggiornati a 599 comuni sono raccolti nella sezione
["Aggiornamento — da 177 a 599 comuni"](#aggiornamento-2026-07-24--da-177-a-599-comuni-via-234)
poco più sotto, per evitare di riscrivere ogni sezione storica.

## Aggiornamento 2026-07-17 — da 44 a 63 comuni, dati fino ad oggi

Richiesta esplicita dell'utente: coprire tutti i 1180 comuni piemontesi e
portare i dati fino ad oggi. Obiettivo ridimensionato insieme all'utente
dopo aver scoperto (nel modo peggiore) che **Open-Meteo ha un limite
giornaliero di richieste**, non solo "al minuto" come già documentato —
vedi [Fonti Dati](data-sources.md) per il racconto completo. Risultato
netto: **+19 comuni** (44→63) più l'estensione temporale a tutti e 63
fino a oggi, ottenuti in modo sostenibile con lotti piccoli invece che un
tentativo unico in blocco.

**Risultati ricalcolati (63 comuni, 2000 - oggi)**:

- **Trend**: 54/63 comuni con trend significativo (p<0.05), da -0.63 a
  +1.31 °C/decade. Novità: **Briga Alta è l'unico comune con un
  raffreddamento significativo** (-0.63°C/decade, p=0.0014) — un
  risultato controcorrente rispetto al resto del campione, non ancora
  indagato a fondo (possibili cause: microclima locale, breve serie
  rispetto alla variabilità, o semplice rumore anche se il p-value è
  basso — un solo comune anomalo su 63 non permette conclusioni, ma è
  onesto segnalarlo invece di ometterlo).
- **Ondate di calore**: **190 ondate totali** (145 fino al 2025 + 16
  nuove nel solo 2026, primi 7 mesi dell'anno — coerente con un'estate
  2026 già calda). La disponibilità di dati 2026 ha anche fatto emergere
  un bug (vedi sotto).
- **Moran's I = 0.1319** (atteso sotto casualità: -0.016), **p=0.001 —
  ancora più significativo che con 44 comuni** (era 0.1006, p=0.002).
- **Cluster K-means (k=3)**, ricomposizione con i 19 comuni nuovi:

  | Cluster | Temp. media | N. comuni | Esempi |
  |---|---|---|---|
  | 0 — alpino | 3.7°C | 14 | Acceglio, Aisone, Alagna Valsesia, Bardonecchia, Briga Alta, Ceresole Reale, Claviere, Entracque, Formazza, Gravere, Macugnaga, Rorà, Sauze di Cesana, Usseglio |
  | 1 — intermedio | 11.4°C | 30 | Biella, Cuneo, Verbania e la maggioranza dei comuni pedemontani/collinari, più molti dei 19 nuovi |
  | 2 — pianura calda | 13.1°C | 18 | Alessandria, Asti, Torino, Vercelli, Novara e altri comuni di pianura |

> **Bug reale trovato e corretto grazie al dato 2026**:
> `frequency_by_year()` in `heatwave_stats.py` aveva un
> `reindex(range(2000, 2026))` fisso nel codice — un anno finale
> hardcoded che, con dati fermi al 2025, non aveva mai fatto danni, ma
> che con l'arrivo dei dati 2026 **scartava in silenzio le 16 ondate di
> quest'anno** dal grafico a barre della dashboard (nessun errore,
> semplicemente sparivano). Scoperto confrontando il conteggio diretto da
> `heatwave_events` (190) con l'output della funzione (174, mancavano
> esattamente le 16 del 2026). Fix: range dinamico
> (`df['year'].min()`/`.max()`) invece di limiti fissi nel codice —
> stesso tipo di bug, root cause diversa, del reindex già visto altrove
> nel progetto (vincoli "temporanei" scritti come costanti fisse che
> invecchiano male). Stesso bug trovato e corretto anche nella dashboard
> (`components/filters.py`: `YEAR_MIN, YEAR_MAX = 2000, 2025` fisso, reso
> dinamico dalla data reale in `temperature`).

## Aggiornamento 2026-07-17 (pomeriggio) — da 63 a 98 comuni

Import dei 35 comuni scaricati la mattina stessa da una seconda macchina
(collaboratrice senza accesso al DB del titolare, vedi
[ETL](etl-pipeline.md) e [Fonti Dati](data-sources.md)): pulizia +
risoluzione `istat_code` → `municipality_id`, caricamento in `temperature`
(63 → 98 comuni, 950.110 righe), elevazione ri-scaricata per tutti i
comuni con dati, `TRUNCATE` + `identify_heatwaves()`, refresh viste KPI,
poi rieseguiti tutti e 5 i moduli di `src/analysis/` (inclusa
`spatial_regression.py`, prima esecuzione dopo la sua introduzione lo
stesso giorno).

**Risultati ricalcolati (98 comuni, 2000 - oggi)**:

- **Trend**: 86/98 comuni con trend significativo (p<0.05). **Briga Alta
  resta l'unico comune con raffreddamento significativo**
  (-0.63°C/decade, p=0.0014, invariato rispetto alla versione a 63
  comuni) — tra i 12 comuni non significativi, nessun altro mostra un
  segno negativo: sono tutti "no trend" (p tra 0.06 e 0.77), non
  raffreddamenti mascherati. Estremo positivo: Castelnuovo Nigra
  (+1.45°C/decade, p<0.001).
- **Ondate di calore**: **331 ondate totali** (da 190). Alessandria resta
  il comune con più ondate (15), seguita da Casalnoceto (14, uno dei 35
  nuovi) e Asti (13). 45/98 comuni non hanno mai raggiunto 3 giorni
  consecutivi sopra i 35°C (prevalentemente comuni alpini/di alta quota).
- **STL (scomposizione stagionale)**: ampiezza stagionale 27.4-35.3°C.
  Trend in aumento in 95/98 comuni (da 62/63) — oltre a Briga Alta, i 35
  nuovi comuni hanno portato alla luce altri due casi non in aumento
  (Grondona -0.21°C, Pietraporzio 0.00°C), entrambi coerenti con un
  Mann-Kendall "no trend" (non significativi), a differenza di Briga Alta
  che resta l'unico raffreddamento sia significativo sia sostanziale. Vedi
  dettaglio nella sezione dedicata sotto.
- **Moran's I = 0.1523** (atteso sotto casualità: -0.0105), **p=0.001 su
  999 permutazioni** — leggero miglioramento rispetto a 63 comuni
  (0.1319, p=0.001): il segnale di autocorrelazione spaziale resta stabile
  e significativo al crescere del campione.
- **Cluster K-means (k=3)**, ricomposizione con i 35 comuni nuovi:

  | Cluster | Temp. media | N. comuni | Esempi |
  |---|---|---|---|
  | 0 — alpino | 5.2°C | 31 | Acceglio, Aisone, Bardonecchia, Briga Alta, Carrega Ligure, Ceresole Reale, Formazza, Macugnaga, Rorà, Usseglio, Valprato Soana |
  | 1 — intermedio | 12.2°C | 40 | Biella, Cuneo, Verbania e la maggioranza dei comuni pedemontani/collinari, inclusi molti dei 35 nuovi (Bosio, Gremiasco, Villadossola, ecc.) |
  | 2 — pianura calda | 13.1°C | 26 | Alessandria, Asti, Torino, Vercelli, Novara e altri comuni di pianura, inclusi i nuovi Casalnoceto, Cerano, Fubine Monferrato |

- **Regressione spaziale (`spatial_regression.py`, prima riesecuzione)**:
  a n=98 il quadro cambia rispetto alla prima iterazione a n=63 — vedi
  sezione dedicata sotto per il dettaglio completo. In sintesi: **% urbano
  non è più significativo** (era p=0.011 a n=63, ora p=0.334), mentre NDVI
  resta significativo con lo stesso segno controintuitivo. Un promemoria
  concreto che risultati su campioni ancora piccoli per la spatial
  econometrics possono non essere stabili al crescere di n — motivo in
  più per continuare a estendere la copertura prima di trarre conclusioni
  nel paper.

## Aggiornamento 2026-07-18 — da 98 a 177 comuni

Due estensioni nello stesso giorno: 57 comuni scaricati da una seconda
collaboratrice (stessa macchina esterna della sessione precedente, questa
volta usando direttamente [Comuni già coperti](comuni-coperti.md) come
riferimento invece di doverla ricostruire dai PNG QGIS) portano 98 → 155,
poi un download diretto di altri 22 comuni porta 155 → **177**. Vedi
[ETL](etl-pipeline.md) per il racconto completo, incluso un file stantio
scartato prima dell'import (una ri-consegna involontaria di dati già
presenti) e un bug reale corretto in `fetch_elevation.py` (l'Elevation
API rifiuta oltre 100 coordinate in un'unica richiesta).

**Risultati ricalcolati (177 comuni, 2000 - oggi)**:

- **Trend**: 159/177 comuni con trend significativo (p<0.05). **Briga
  Alta resta l'unico comune con raffreddamento significativo**
  (-0.63°C/decade, p=0.0014, identico alle versioni precedenti) — nessun
  altro comune tra i non significativi mostra un segno negativo
  sostanziale. Estremo positivo: Castelnuovo Nigra (+1.45°C/decade,
  p<0.001), seguito a ruota da Rifreddo (+1.42°C/decade), uno dei comuni
  aggiunti oggi.
- **Ondate di calore**: **640 ondate totali** (da 331). Il comune con più
  ondate cambia per la prima volta: **Bassignana, Bozzole e Tortona** (16
  ciascuno, tutti e tre tra i comuni aggiunti oggi), davanti ad
  Alessandria (15, che deteneva il primato dalle versioni precedenti).
  97/177 comuni non hanno mai raggiunto 3 giorni consecutivi sopra i 35°C.
- **STL (scomposizione stagionale)**: ampiezza stagionale 27.4-35.3°C.
  Trend in aumento in 172/177 comuni (da 95/98) — oltre a Briga Alta,
  Grondona e Pietraporzio, emersi altri due casi non in aumento tra i
  comuni nuovi (Limone Piemonte -0.45°C, Castelmagno -0.23°C), tutti "no
  trend" non significativi per Mann-Kendall. **Briga Alta resta l'unico
  raffreddamento sia significativo sia sostanziale, confermato per la
  terza estensione consecutiva.** Vedi dettaglio nella sezione dedicata
  sotto.
- **Moran's I = 0.1695** (atteso sotto casualità: -0.006), **p=0.001 su
  999 permutazioni** — ulteriore leggero miglioramento rispetto a 98
  comuni (0.1523, p=0.001): il segnale resta stabile e significativo.
- **Cluster K-means (k=3)**, ricomposizione con i 79 comuni nuovi (57 +
  22):

  | Cluster | Temp. media | N. comuni |
  |---|---|---|
  | 0 — alpino | 5.4°C | 47 |
  | 1 — intermedio | 12.0°C | 78 |
  | 2 — pianura calda | 13.2°C | 52 |

- **Regressione spaziale (`spatial_regression.py`, seconda riesecuzione)**:
  a n=177 **anche NDVI smette di essere significativo** (p=0.58, era
  p=0.007 a n=98), oltre a % urbano (già non significativo da n=98,
  p=0.19 a n=177). Per NDVI **non è solo il p-value a spostarsi: il
  coefficiente stesso crolla dell'85%** (da +1.089 a +0.161 tra n=98 e
  n=177) — segno che l'effetto visto a n=98 era probabilmente in parte un
  artefatto di un campione ancora piccolo, non solo rumore attorno a una
  soglia. % urbano invece ha un coefficiente piccolo ma stabile in
  entrambe le versioni (+0.0056 → +0.0063): lì è cambiato solo il
  p-value, coerente con un effetto debole ma reale che richiede più
  potenza statistica per emergere. Solo l'elevazione resta un predittore
  robusto e stabile in tutte e tre le versioni (n=63/98/177). Vedi
  sezione dedicata sotto per il dettaglio completo e la tabella di
  confronto.

## Aggiornamento 2026-07-24 — da 177 a 599 comuni (via 234)

Il giro unico di import del 2026-07-23 ([Comuni già coperti](comuni-coperti.md),
[Stato del progetto](project-status.md)) ha portato la copertura Open-Meteo
177 → 234 (2026-07-19) → **599 comuni**, con `refresh_dashboard.py`
(rilancia tutti e 5 i moduli di `src/analysis/` in sequenza) rieseguito
sull'intero campione finale il 2026-07-23 pomeriggio. Questa sezione
riporta i risultati aggiornati, scritta il giorno dopo l'import (il codice
era già aggiornato, mancava solo la sintesi in questa pagina — vedi
`wiki/log.md` per il dettaglio della sessione di sincronizzazione).

**Il passaggio intermedio a 234 comuni (2026-07-19) non ha una sezione
dedicata in questa pagina** (fu documentato solo in
[Stato del progetto](project-status.md) e nel testo della dashboard): il
modello a errore spaziale a n=234 aveva reso **% urbano di nuovo
significativo** (p=0.031, coefficiente +0.0083, segno atteso) e NDVI non
significativo (p=0.66) — citato qui solo come punto di confronto, non
verificabile a ritroso perché i file `output/` di quella run sono stati
sovrascritti dalle esecuzioni successive.

- **Trend (`trend_analysis.py`)**: **556/599 comuni (92.8%)** con trend di
  riscaldamento significativo (p<0.05), pendenza da -0.62 a +1.51
  °C/decade (Prarostino il più ripido, seguito da Angrogna +1.50 e
  Traversella +1.46). **Cambio degno di nota**: la claim ripetuta per tre
  estensioni consecutive ("Briga Alta resta l'unico comune con
  raffreddamento significativo") **non è più vera** — a 599 comuni compare
  un secondo caso, **Argentera** (-0.40°C/decade, p=0.041). Briga Alta
  resta comunque il caso più marcato (-0.62°C/decade, p=0.015).
- **Ondate di calore (`heatwave_stats.py`)**: **2.192 ondate totali** (da
  640 a n=177). Il comune con più ondate cambia ancora una volta:
  **Molino dei Torti e Castellazzo Bormida, 17 ciascuno** (pari merito),
  davanti ai precedenti leader Bassignana/Bozzole/Tortona (16 a n=177).
- **STL (`seasonal_analysis.py`)**: componente di trend in aumento in
  **589/599 comuni (98.3%)**. I 10 comuni non in aumento sono, in ordine
  di variazione totale: Briga Alta (-1.54°C), **Argentera (-0.46°C, nuovo
  rispetto a n=177)**, Limone Piemonte (-0.45°C), Sambuco (-0.33°C, nuovo),
  Castelmagno (-0.21°C), Grondona (-0.19°C), Borghetto di Borbera (-0.18°C,
  nuovo), Fabbrica Curone (-0.04°C, nuovo), Ormea (-0.01°C, nuovo), Perlo
  (-0.01°C, nuovo) — coerente con Argentera che emerge anche in
  Mann-Kendall come secondo caso di raffreddamento significativo. Ampiezza
  stagionale 27.4-36.4°C (leggero allargamento verso l'alto rispetto a
  27.4-35.3°C a n=177).
- **Moran's I e clustering (`spatial_analysis.py`)**: **Moran's I = 0.2115**
  (atteso sotto casualità: -0.0015), **p=0.001 su 999 permutazioni** —
  ulteriore miglioramento rispetto a 177 comuni (0.1695, p=0.001): il
  segnale di autocorrelazione spaziale resta stabile e sempre più
  significativo al crescere del campione. Cluster K-means (k=3):

  | Cluster | Temp. media | N. comuni |
  |---|---|---|
  | 0 — alpino | 6.2°C | 152 |
  | 1 — intermedio | 11.9°C | 249 |
  | 2 — pianura calda | 13.2°C | 198 |

- **Regressione spaziale (`spatial_regression.py`)**: vedi la sezione
  dedicata più sotto per il dettaglio completo (tabella di confronto
  n=63/98/177/599 e discussione del ribaltamento di significatività
  %urbano/NDVI).

**In sintesi**: l'estensione a 599 comuni conferma ulteriormente i
risultati già robusti (riscaldamento diffuso, autocorrelazione spaziale
reale) e introduce due correzioni oneste rispetto a claim precedenti
ripetute più volte come stabili — un secondo comune in raffreddamento
(Argentera) e un nuovo ribaltamento di significatività nel modello a
errore spaziale (%urbano/NDVI, vedi sotto) — nessuna delle due invalida le
conclusioni principali del progetto, ma vanno riportate nel paper come
parte della cronologia di convergenza del campione, non nascoste.

## `trend_analysis.py` — trend di riscaldamento

CLI: `python -m src.analysis.trend_analysis`

- `load_annual_temperature()` — legge `temp_mean_annual` per comune/anno
  da `kpi_annual_by_municipality`
- `mann_kendall_trend()` — test di Mann-Kendall
  (`pymannkendall.original_test`): rileva se c'è un trend monotono, senza
  assumere normalità
- `linear_trend()` — regressione lineare (`scipy.stats.linregress`): stima
  la pendenza in °C/anno e °C/decade
- Output: `output/trend_analysis.csv`

**Risultato reale (2000-2025, 44 comuni)**: 38 comuni su 44 mostrano un
trend crescente statisticamente significativo (p<0.05), tra +0.3 e +1.4
°C/decade (Bagnolo Piemonte il più ripido). Coerente con il segnale di
riscaldamento osservato nel Nord Italia — e ora osservato in modo diffuso
su tutto il territorio piemontese, non solo negli 8 capoluoghi (risultato
originario a 8 comuni: 7/8 significativi, +0.4/+1.0 °C/decade).

## `heatwave_stats.py` — statistiche sulle ondate di calore

CLI: `python -m src.analysis.heatwave_stats`

- `backfill_intensity_and_mean_temp()` — popola
  `heatwave_events.intensity_index` (= `(max_temp - heat_threshold) *
  duration_days`) e `mean_temp` (media di `temperature.temp_mean` nel
  periodo dell'ondata), lasciati `NULL` da `identify_heatwaves()` (vedi
  [Modello Dati](data-model.md))
- `summary_by_municipality()` — conteggio, durata media/max, intensità
  media/max per comune
- `frequency_by_year()` — conteggio ondate per anno (anni senza ondate
  inclusi come 0); **estesa il 2026-07-15** per includere anche
  `avg_duration_days`/`avg_intensity` per anno, non solo il conteggio —
  usate dal grafico a barre a doppio asse della pagina "Ondate di
  Calore" della dashboard
- Output: `output/heatwave_stats_by_municipality.csv`,
  `output/heatwave_frequency_by_year.csv`

**Risultato reale (44 comuni)**: 145 ondate totali (51 sugli 8 capoluoghi
originari + 94 sui 36 comuni extra). Alessandria resta il comune con più
ondate (14), seguita dal nuovo comune Casalnoceto (13) e Asti (11).
Diversi comuni alpini tra i 36 extra (Formazza, Macugnaga, Acceglio,
Alagna Valsesia, Bardonecchia, Ceresole Reale, Rorà, Aisone) non hanno mai
raggiunto 3 giorni consecutivi sopra i 35°C nel periodo (0 ondate),
coerente con la loro quota/clima alpino — lo stesso vale per Biella e
Verbania tra gli 8 capoluoghi originari.

## `seasonal_analysis.py` — scomposizione stagionale (STL)

CLI: `python -m src.analysis.seasonal_analysis`

- `load_daily_series()` — serie giornaliera continua di `temp_mean` per
  comune (nessun gap nei dati reali: verificato che `asfreq('D')` non
  introduce `NaN`)
- `decompose()` — STL decomposition (`statsmodels.tsa.seasonal.STL`,
  `period=365`, `robust=True`) in trend / stagionalità / residuo
- Output: `output/seasonal_decomposition/{comune}_stl.csv` (serie completa
  giorno per giorno), `output/seasonal_trend_summary.csv` (riepilogo)

**Risultato reale (44 comuni)**: ampiezza stagionale 27-34°C, più ampia
nei comuni alpini/di alta quota (Bardonecchia 34.3°C, Macugnaga 33.4°C,
Formazza 32.6°C — inverni più rigidi) e più contenuta nei comuni di
pianura vicino ai laghi/pedemontani (Verbania 27.8°C, Ghemme 27.9°C).
Componente di trend in aumento in 43 comuni su 44 (unica eccezione:
Carrega Ligure, -0.04°C, sostanzialmente piatta), direzione coerente con
Mann-Kendall/regressione lineare (l'entità numerica differisce
leggermente per via della metodologia diversa: STL confronta due medie
annuali sulla componente smussata, la regressione lineare usa tutti i 26
anni).

**Rieseguita il 2026-07-17 su 63 comuni** (~27 minuti, eseguita in
background per via del tempo di calcolo su 63 serie giornaliere estese
fino ad oggi): componente di trend in aumento in **62 comuni su 63**.
L'unica eccezione è ora **Briga Alta** (-1.56°C di variazione totale di
trend), uno dei 19 comuni aggiunti — **stesso identico comune** segnalato
come raffreddamento significativo da Mann-Kendall/regressione lineare
(-0.63°C/decade, p=0.0014). Le due metodologie, completamente
indipendenti (STL confronta medie smussate a inizio/fine periodo,
Mann-Kendall+regressione guardano l'intera serie annuale), **concordano
sullo stesso comune anomalo** — un indizio che il segnale è reale e non
un artefatto di un singolo metodo, pur restando un solo caso su 63 che
non permette conclusioni forti sulle cause.

**Rieseguita di nuovo lo stesso giorno (pomeriggio) su 98 comuni**, dopo
l'import dei 35 comuni extra da una seconda macchina (~56 minuti in
background, 18:39→19:35 — più lenta della stima iniziale di ~40 minuti,
coerente con l'aumento non lineare del numero di serie da processare).
Ampiezza stagionale 27.4-35.3°C (Gravere/San Giorio di Susa/Claviere le
più ampie, comuni alpini di alta quota; Alto/Verbania/Momo le più
contenute). **Trend in aumento in 95 comuni su 98** (da 62/63) — tra i 35
nuovi comuni sono emersi altri **2 casi non in aumento** oltre a Briga
Alta: **Grondona** (-0.21°C, lieve) e **Pietraporzio** (0.00°C,
sostanzialmente piatta). Nessuno dei due è però un raffreddamento
*significativo* per Mann-Kendall/regressione lineare (entrambi "no
trend", p=0.22 e p=0.27 — vedi tabella comuni non significativi sopra):
le due metodologie restano coerenti anche qui, dato che "variazione STL
quasi nulla" e "nessun trend rilevato da Mann-Kendall" descrivono la
stessa realtà con strumenti diversi. **Briga Alta resta l'unico caso di
raffreddamento sia significativo (Mann-Kendall) sia sostanziale (STL)** —
l'aggiunta di più comuni non ha smentito questo risultato, lo ha solo
affiancato a due casi più deboli (piatti, non significativi).

**Rieseguita una terza volta il 2026-07-18 su 177 comuni** (~112 minuti in
background, 11:24→13:16 — il job ha continuato a scrivere risultati per
diversi minuti dopo una notifica di completamento prematura del tool,
verificato ignorandola e controllando direttamente il timestamp di
`output/seasonal_trend_summary.csv` prima di considerarlo davvero
concluso, stesso problema già visto il 2026-07-17). Ampiezza stagionale
27.4-35.3°C, range sostanzialmente invariato (Gravere 35.3°C resta
l'estremo alto, Alto 27.4°C il nuovo estremo basso). **Trend in aumento
in 172 comuni su 177** (da 95/98) — tra i 79 comuni aggiunti nella
giornata sono emersi altri **2 casi non in aumento** oltre ai 3 già noti
(Briga Alta, Grondona, Pietraporzio): **Limone Piemonte** (-0.45°C) e
**Castelmagno** (-0.23°C). Tutti e 4 i casi minori (Limone Piemonte,
Castelmagno, Grondona, Pietraporzio) restano "no trend" non significativi
per Mann-Kendall (p tra 0.14 e 0.47) — **Briga Alta resta l'unico e solo
caso di raffreddamento sia significativo sia sostanziale**, confermato
per la terza volta su tre estensioni successive del campione: un segnale
sempre più difficile da liquidare come rumore casuale, dato quante volte
è sopravvissuto a un campione che cambia composizione.

## `spatial_analysis.py` — Moran's I e clustering climatico

CLI: `python -m src.analysis.spatial_analysis`

- `build_inverse_distance_weights()` — matrice pesi spaziali W, inverso
  della distanza haversine tra i centroidi dei comuni, row-standardized
- `morans_i()` / `morans_i_permutation_test()` — indice di Moran calcolato
  a mano (nessuna dipendenza aggiuntiva tipo `libpysal`/`esda`);
  significatività via **test di permutazione** (999 permutazioni) anziché
  l'approssimazione normale asintotica classica, più robusta con un
  campione piccolo
- `climate_clustering()` — K-means (k=3) su temperatura media, giorni
  >30°C, giorni >35°C standardizzati. **Etichette rinumerate per
  temperatura crescente (2026-07-16)**: le etichette grezze di sklearn
  (0/1/2) sono assegnate in un ordine arbitrario, senza legame con quanto
  è caldo il gruppo — su richiesta dell'utente ("non c'è una logica di
  ordinamento"), rimappate così che il cluster **0 sia sempre il più
  fresco e il 2 sempre il più caldo**, una convenzione stabile anche se
  l'analisi viene ri-eseguita e sklearn assegna le etichette grezze in un
  ordine diverso.
- Output: `output/spatial_analysis.csv`, `output/morans_i_summary.csv`

**Aggiornamento 2026-07-15 — da 8 a 44 comuni**: il campione iniziale di
8 unità spaziali (i soli capoluoghi) era sotto la soglia comunemente
citata come minima per un'analisi di autocorrelazione spaziale robusta
(tipicamente 20-30 unità), e infatti dava un risultato non significativo.
Estesa la copertura a 44 comuni (vedi [ETL](etl-pipeline.md) per come
sono stati scelti) su richiesta esplicita dell'utente, proprio per
superare questo limite. Risultato:

- **Moran's I = 0.1006** (atteso sotto casualità: -0.0244), **p=0.002 su
  999 permutazioni — statisticamente significativo** (era -0.096,
  p=0.732, non significativo, con 8 comuni). I comuni geograficamente
  vicini hanno temperature realmente più simili tra loro di quanto ci si
  aspetterebbe per caso: il segnale climatico ha una struttura spaziale
  reale, non è rumore geografico. Con 44 unità il test ha ora la
  sensibilità per rilevarlo.
- Clustering K-means (k=3), ora molto più nitido geograficamente
  (etichette 0/1/2 = dal più fresco al più caldo, vedi sopra):

  | Cluster | Temp. media | Comuni |
  |---|---|---|
  | 0 — alpino | 3.8°C | Acceglio, Aisone, Alagna Valsesia, Bardonecchia, Ceresole Reale, Formazza, Macugnaga, Rorà — tutti di alta quota, ai margini montani nord e sud-ovest della regione |
  | 1 — intermedio | 11.1°C | Comuni pedemontani/collinari (Biella, Cuneo, Verbania, ecc.) |
  | 2 — pianura calda | 12.9°C | Alessandria, Asti, Torino, Vercelli e altri comuni della pianura centro-orientale |

  Verificato visivamente anche nelle mappe QGIS (`hotspot_analysis.qgz`,
  vedi [Mappe GIS](gis-maps.md)): il pattern geografico è visibilmente
  coerente (blu=alpino ai margini montani, rosso=pianura calda al
  centro-est — stessa palette blu→rosso della dashboard, non più colori
  categorici arbitrari), non più solo un'etichetta statistica.

Restano comunque solo 44 dei 1180 comuni piemontesi — un'analisi ancora
più esaustiva richiederebbe temperature per un sottoinsieme più ampio
(vedi [ETL](etl-pipeline.md)), ma il salto qualitativo da "campione troppo
piccolo per dire qualcosa" a "risultato statisticamente significativo" è
già stato fatto.

> **Aggiornamento 2026-07-16 — etichette cluster riordinate alla fonte**:
> l'utente ha notato che l'assegnazione delle etichette 0/1/2 non seguiva
> "una logica di ordinamento" — sklearn assegna le etichette grezze di
> K-means in un ordine arbitrario, senza legame con la temperatura.
> Corretto **alla fonte**, non solo nel testo della dashboard:
> `climate_clustering()` ora rinumera le etichette per temperatura media
> crescente prima di salvarle (0 = più fresco, 2 = più caldo). Aggiornati
> anche i colori: `CLUSTER_COLORS` in `components/constants.py` passa da
> 3 colori categorici senza relazione con la temperatura a
> blu→arancio→rosso (stessa logica della colormap di temperatura usata
> altrove nel sito), applicato anche alla mappa QGIS
> `hotspot_analysis.qgz`, rigenerata di conseguenza.

## `spatial_regression.py` — modello esplicativo (temperatura ~ covariate)

CLI: `python -m src.analysis.spatial_regression`

Prima fase quantitativa verso il modello del paper scientifico (fase 4 del
piano, vedi [Articolo scientifico](paper-scientifico.md)), eseguita il
2026-07-17 non appena le 3 covariate esplicative (popolazione, uso del
suolo CORINE, NDVI — vedi [Fonti Dati](data-sources.md)) sono state tutte
disponibili in DB per i 63 comuni con temperatura.

### Fase 1 — OLS classico + check di adeguatezza

- `load_regression_data()` — join tra `kpi_annual_by_municipality`
  (`temp_mean_avg` 2000-oggi), `municipalities` (elevazione, densità di
  popolazione = popolazione/area), `municipality_land_cover`
  (`pct_urban`), `municipality_ndvi` (`ndvi_mean`)
- `compute_vif()` — Variance Inflation Factor per covariata (tutte <5,
  nessuna multicollinearità grave tra le 4 variabili)
- `fit_ols()` — OLS via `statsmodels`
- Check di adeguatezza: Moran's I sui **residui** OLS (riusa
  `build_inverse_distance_weights()`/`morans_i_permutation_test()` di
  `spatial_analysis.py`, pesi inverso-distanza) — se ancora significativo,
  un OLS classico non è adeguato per l'inferenza

**Risultato Fase 1 (63 comuni)**: R²=0.979, dominato quasi interamente
dall'elevazione (-0.56°C/100m, p<0.001, fisicamente coerente col
gradiente altimetrico). Popolazione (p=0.698) e % urbano (p=0.897) **non
significativi**; NDVI significativo (p=0.028) ma con **segno
controintuitivo** (più verde → temperatura più alta, non più bassa —
sospetto confondimento con l'elevazione: la pianura agricola è insieme
molto verde a luglio e a bassa quota/calda). **Moran's I sui residui =
0.081, p=0.001 — ancora significativo**: l'OLS non è adeguato, serve un
modello spaziale vero.

### Fase 2 — modello spaziale (spreg/libpysal)

Non implementato a mano (a differenza di Moran's I in
`spatial_analysis.py`: qui la stima a massima verosimiglianza è più
delicata, si usa una libreria testata):

- `build_knn_weights()` — pesi spaziali KNN (k=5, row-standardized) via
  `libpysal.weights.KNN` — scelta diversa dall'inverso-distanza usato in
  Fase 1 (KNN evita nodi isolati/pesi degeneri con punti irregolari,
  standard per `spreg`)
- `run_lm_diagnostics()` — `spreg.OLS` con test del Moltiplicatore di
  Lagrange (LM-lag/LM-error) e versioni robuste, per decidere tra modello
  a lag o a errore spaziale
- `select_spatial_model()` — regola di decisione di Anselin (Anselin &
  Rey 1991): usa le versioni robuste dei test LM quando entrambi i test
  semplici sono significativi, per distinguere lag "vero" da errore
  "vero"
- `fit_spatial_model()` — stima `spreg.ML_Lag` o `spreg.ML_Error` a
  seconda dell'esito

**Risultato Fase 2 (63 comuni, KNN k=5)**: caso non ambiguo — LM-lag
p=0.351 (non significativo), LM-error p=0.0001 (fortemente significativo,
**robusto** anche a p=0.0002) → **modello a errore spaziale**.
Lambda=0.738 (p<0.001, forte dipendenza spaziale nell'errore, confermata).
Con questo modello:

- Elevazione resta dominante e significativa (-0.0055°C/m, p<0.001).
- **% urbano diventa significativo (p=0.011) con il segno atteso**
  (positivo: più urbano → più caldo) — l'ipotesi originale del paper
  (città/industria come fattore esplicativo) **trova conferma solo dopo
  la correzione spaziale**: l'OLS classico la mascherava, sotto/sovra-stimando
  l'effetto per aver ignorato la dipendenza spaziale nell'errore.
- Popolazione resta non significativa (p=0.116).
- NDVI resta significativo (p=0.0037) **con lo stesso segno
  controintuitivo** della Fase 1 — persiste anche dopo la correzione
  spaziale, quindi non è (solo) un artefatto legato all'autocorrelazione:
  da approfondire nel paper (ipotesi principale: NDVI a luglio cattura
  anche l'agricoltura irrigua di pianura, che è calda per via della bassa
  quota indipendentemente dal verde).

> **Caveat esplicito**: la scelta del modello spaziale dipende dalla
> definizione della matrice pesi (qui KNN k=5 per `spreg`,
> inverso-distanza per il check Fase 1) — un limite noto della spatial
> econometrics con campioni piccoli, da rivalutare quando il campione di
> comuni con temperatura crescerà (l'utente sta estendendo la copertura
> gradualmente, vedi [Fonti Dati](data-sources.md)).

### Aggiornamento 2026-07-17 (pomeriggio) — rieseguito su 98 comuni

Rilanciato lo stesso giorno dopo l'import dei 35 comuni extra da una
seconda macchina (63 → 98 comuni, vedi [ETL](etl-pipeline.md)) — esattamente
il caso d'uso per cui il caveat sopra era stato scritto ("da rivalutare
quando il campione crescerà").

**Fase 1 (OLS, n=98)**: R²=0.980, elevazione ancora dominante
(-0.0057°C/m, p<0.001). Popolazione (p=0.501) e % urbano (p=0.570) **non
significativi** nell'OLS classico (stesso quadro qualitativo di n=63).
NDVI significativo (p=0.007), stesso segno controintuitivo. Moran's I sui
residui OLS = 0.1189 (p=0.001) — ancora significativo, l'OLS resta
inadeguato per l'inferenza.

**Fase 2 (modello a errore spaziale, KNN k=5, n=98)**: stesso esito della
regola di Anselin (LM-error fortemente significativo anche robusto
p<0.0001, LM-lag non robusto p=0.929) → **errore spaziale**, lambda=0.803
(p<0.001).

| Variabile | n=63 (mattina) | n=98 (pomeriggio) |
|---|---|---|
| Elevazione | -0.0055°C/m, p<0.001 | -0.0057°C/m, p<0.001 — dominante in entrambi |
| Popolazione | p=0.116, non signif. | p=0.968, non signif. |
| **% urbano** | **p=0.011, significativo, segno atteso** | **p=0.334, non più significativo** (coefficiente ancora positivo ma piccolo) |
| NDVI | p=0.0037, signif., segno controintuitivo | p=0.0085, signif., stesso segno controintuitivo |

**Il risultato più rilevante del giorno precedente non si è confermato**:
a n=63 il modello a errore spaziale rendeva % urbano significativo con il
segno atteso (prima "conferma" quantitativa dell'ipotesi del paper su
città/urbanizzazione); a n=98 quello stesso effetto **scompare**. Non è
un errore di calcolo (stessa pipeline, stesso codice, solo più
osservazioni) — è la dimostrazione pratica del caveat già scritto sopra:
con un campione ancora piccolo per la spatial econometrics, un
coefficiente "appena significativo" può facilmente ribaltarsi aggiungendo
osservazioni. **Registrato onestamente come risultato non stabile**,
invece di riportare solo la versione più favorevole — questo genere di
instabilità va discusso esplicitamente nel paper (vedi
[Articolo scientifico](paper-scientifico.md)), non nascosto scegliendo
quale run citare. NDVI resta l'unica covariata (oltre all'elevazione) a
mostrarsi stabilmente significativa tra le due versioni, sempre con lo
stesso segno controintuitivo da approfondire.

### Aggiornamento 2026-07-18 — rieseguito su 177 comuni

Rilanciato di nuovo lo stesso giorno seguente, dopo due estensioni in
sequenza (98 → 155 → 177 comuni, vedi [ETL](etl-pipeline.md)).

**Fase 1 (OLS, n=177)**: elevazione ancora dominante e fortemente
significativa. Popolazione e % urbano non significativi nell'OLS
classico. Moran's I sui residui OLS = 0.1301 (p=0.001) — ancora
significativo, l'OLS resta inadeguato per l'inferenza.

**Fase 2 (modello a errore spaziale, KNN k=5, n=177)**: stesso esito
della regola di Anselin (LM-error fortemente significativo anche robusto
p<0.0001, LM-lag robusto p=0.073, non significativo) → **errore
spaziale**, lambda=0.854 (p<0.001) — la dipendenza spaziale nell'errore
si rafforza ulteriormente rispetto alle versioni precedenti.

| Variabile | n=63 | n=98 | n=177 |
|---|---|---|---|
| Elevazione | coef=-0.0055, p<0.001 | coef=-0.0057, p<0.001 | coef=-0.0058, p<0.001 — **unico predittore stabile: stesso segno, stessa grandezza, sempre significativo** |
| Popolazione | p=0.116, non signif. | coef≈0, p=0.968, non signif. | coef≈0, p=0.800, non signif. |
| **% urbano** | **p=0.011, significativo** (coefficiente non registrato in questa pagina) | coef=+0.0056, p=0.334, non signif. | coef=+0.0063, p=0.193, non signif. |
| **NDVI** | p=0.0037, signif. (coefficiente non registrato) | **coef=+1.089, p=0.0085, signif.** | coef=+0.161, p=0.581, non signif. |

**Non è solo il p-value a saltare sopra/sotto 0.05 — per NDVI il
coefficiente stesso si è quasi azzerato**: da +1.089 (n=98) a +0.161
(n=177), un crollo dell'85% nella stima puntuale, non solo nella sua
significatività. Se fosse semplice rumore statistico attorno a un
effetto reale stabile, ci si aspetterebbe che il coefficiente resti
all'incirca della stessa grandezza mentre solo l'errore standard si
restringe con più osservazioni (rendendo la stima *più* precisa, non
diversa). Invece la stima stessa si è spostata verso zero — indizio che
il "segnale" NDVI visto a n=98 fosse in parte un **artefatto di un
campione ancora piccolo e non rappresentativo** (i comuni aggiunti nei
lotti precedenti non erano una selezione casuale, e con l'elevazione che
da sola spiega ~98% della varianza resta pochissimo per NDVI/% urbano da
spiegare — la loro stima è quindi molto sensibile a quali comuni
specifici entrano nel campione). % urbano, al contrario, ha un
coefficiente che resta piccolo e stabile (+0.0056 → +0.0063) sia a n=98
sia a n=177: lì il cambiamento è stato solo nel p-value, coerente con un
effetto debole ma reale la cui significatività dipende dalla potenza
statistica disponibile.

**Interpretazione pratica**: questo non è un problema del modello (la
diagnostica — VIF, Moran's I sui residui, regola di Anselin — resta
metodologicamente solida in tutte e tre le versioni) ma un segnale
onesto sui limiti del campione attuale, di due tipi diversi per le due
covariate. **Per il paper**: l'unico risultato quantitativo robusto finora è l'effetto
dell'elevazione; qualunque affermazione su uso del suolo/vegetazione
richiede un campione più ampio prima di essere presentata con
confidenza (vedi [Articolo scientifico](paper-scientifico.md)).

> **Nota metodologica per le prossime estensioni**: da qui in avanti,
> rieseguire `spatial_regression.py` a ogni nuova estensione del campione
> resta utile, ma va trattato come un **esercizio di convergenza**, non
> come una nuova "notizia" a ogni giro — l'obiettivo non è più "% urbano
> è significativo oggi?" ma "il coefficiente si sta stabilizzando
> (segno/grandezza simili a run precedenti) o continua a spostarsi in
> modo sostanziale?". Un coefficiente che si stabilizza per 2-3 estensioni
> consecutive è un'evidenza molto più solida di una singola soglia
> p<0.05 superata per caso.

### Aggiornamento 2026-07-24 — rieseguito su 599 comuni (via 234)

Rilanciato di nuovo dopo il giro unico di import del 2026-07-23 (177 → 234
→ 599 comuni), come parte di `refresh_dashboard.py`. Il passaggio
intermedio a n=234 (2026-07-19, non documentato in dettaglio in questa
pagina all'epoca) aveva reso **% urbano di nuovo significativo** (p=0.031,
coefficiente +0.0083, segno atteso) con NDVI non significativo (p=0.66) —
citato qui solo come riferimento, i file `output/` di quella run non sono
più disponibili (sovrascritti dalle esecuzioni successive).

**Fase 1 (OLS, n=599)**: R²=0.973, elevazione ancora dominante
(-0.0058°C/m, p<0.001). Popolazione non significativa (p=0.110). **%
urbano è ora significativo anche nell'OLS classico** (coef=-0.0129,
p=0.003) ma con **segno negativo** — più urbanizzazione associata a
temperature *più basse*, l'opposto di quanto atteso fisicamente,
probabile confondimento residuo con l'elevazione non ancora corretto a
questo stadio. NDVI non significativo (p=0.162). Moran's I sui residui
OLS = 0.2094 (p=0.001) — ancora significativo, l'OLS resta inadeguato per
l'inferenza.

**Fase 2 (modello a errore spaziale, n=599)**: lambda=0.932 (p<0.001) — la
dipendenza spaziale nell'errore si rafforza ulteriormente rispetto a tutte
le versioni precedenti (0.738 → 0.803 → 0.854 → 0.932). Con questo
modello:

- Elevazione resta dominante e stabile: coef=-0.00593, p<0.001.
- Popolazione non significativa (p=0.834).
- **% urbano torna non significativo** (coef=+0.00198, p=0.370) — il
  segno torna positivo (atteso) ma perde di nuovo significatività,
  ribaltando il risultato di n=234.
- **NDVI diventa significativo** (p=0.012) con **coefficiente negativo**
  (-0.380) — per la prima volta il segno è quello fisicamente atteso (più
  vegetazione → temperatura più bassa), a differenza di tutte le versioni
  precedenti dove NDVI, quando significativo, aveva sempre un segno
  controintuitivo (più verde → più caldo, ipotizzato come confondimento
  con l'agricoltura irrigua di pianura).

| Variabile | n=63 | n=98 | n=177 | n=234 (rif. parziale) | n=599 |
|---|---|---|---|---|---|
| Elevazione | coef=-0.0055, p<0.001 | coef=-0.0057, p<0.001 | coef=-0.0058, p<0.001 | — | coef=-0.0059, p<0.001 — **unico predittore stabile in ogni versione** |
| Popolazione | p=0.116, non signif. | p=0.968, non signif. | p=0.800, non signif. | — | p=0.834, non signif. |
| **% urbano** | p=0.011, signif. | p=0.334, non signif. | p=0.193, non signif. | **p=0.031, signif.** (coef=+0.0083) | **p=0.370, non signif.** (coef=+0.0020) |
| **NDVI** | p=0.0037, signif. (segno contro.) | coef=+1.089, p=0.0085, signif. (segno contro.) | coef=+0.161, p=0.581, non signif. | p=0.66, non signif. (coef=+0.10) | **coef=-0.380, p=0.012, signif. (segno atteso, per la prima volta)** |
| Lambda (errore spaziale) | 0.738 | 0.803 | 0.854 | — | **0.932** |

**Lettura onesta**: dopo 5 rilanci successivi (n=63/98/177/234/599), **%
urbano e NDVI non hanno mai raggiunto due estensioni consecutive con lo
stesso esito** — significatività e persino il segno di NDVI continuano a
cambiare. L'unica conclusione quantitativa che regge in ogni singola
versione, senza eccezioni, è che **l'elevazione è il predittore dominante
e stabile** della temperatura media. Qualunque affermazione su uso del
suolo/vegetazione nel paper va presentata esplicitamente come non ancora
convergente, non come un risultato consolidato — indipendentemente da
quale sia l'ultima cifra disponibile al momento della scrittura.

Output: `output/spatial_regression.csv`,
`output/spatial_regression_summary.txt` (OLS+VIF+Moran's I residui),
`output/spatial_regression_spatial_model.txt` (diagnostica LM + modello
spaziale finale).

## Dipendenze aggiunte

`pymannkendall==1.4.3`, `scikit-learn==1.9.0`, `statsmodels==0.14.6`
(aggiunte a `requirements.txt` il 2026-07-15). Moran's I in
`spatial_analysis.py` è implementato a mano per evitare di aggiungere
dipendenze per un solo calcolo, dato il campione ridotto. `libpysal==4.15.0`/
`spreg==1.9.0` aggiunte invece il 2026-07-17 per il modello a errore/lag
spaziale vero e proprio in `spatial_regression.py` (qui la stima è
abbastanza delicata da preferire una libreria testata a un'implementazione
a mano).

## Bug incontrati durante l'implementazione

- `AVG()` di PostgreSQL su colonne intere (es. `days_gt_30c SMALLINT`)
  restituisce `NUMERIC`, letto da psycopg2 come `decimal.Decimal` — in
  conflitto con le colonne `float` quando si fanno operazioni pandas
  (`TypeError: unsupported operand type(s) for -: 'decimal.Decimal' and
  'float'`). Fix: cast esplicito `::float` nella query SQL.
- Query con nome comune interpolato via f-string in `seasonal_analysis.py`
  (bozza iniziale) — corretto in query parametrizzata (`sqlalchemy.text`
  con parametri), anche se il valore veniva comunque da una query interna
  fidata, non da input utente: pattern da evitare comunque.

**Estendendo a 44 comuni (2026-07-15)**:

- **`identify_heatwaves()` non è idempotente**: ri-eseguirla dopo aver
  aggiunto i 36 comuni extra avrebbe duplicato le 51 ondate già trovate
  per gli 8 capoluoghi (nessun controllo di esistenza prima
  dell'`INSERT`). Fix operativo: `TRUNCATE TABLE heatwave_events` prima
  di ri-eseguirla — sicuro perché è dato interamente derivato/ricalcolabile
  da `temperature`.
- **Bug di encoding storico scoperto per caso**: durante il download dei
  comuni extra, 2 nomi (Rorà, Cavaglià) sono usciti corrotti nel CSV. La
  causa non era nel nuovo codice, ma in un bug del 2026-07-04 mai notato
  prima (`encoding='cp1252'` invece di `'utf-8'` nella lettura dello
  shapefile ISTAT, che corrompeva il 100% dei nomi con caratteri
  accentati nel database — 28 comuni su 1180). Vedi
  [Fonti Dati](data-sources.md) per il dettaglio completo del fix.
- **Errore di connessione TLS non gestito dal retry esistente**: 5 dei 36
  comuni extra sono falliti al primo download per
  `ConnectionResetError`/`ProtocolError` (non un `429`) — il retry-on-429
  di `download_for_coordinates()` non copre questo caso, l'eccezione si
  propaga e la provincia/comune viene solo loggato e saltato. Risolto
  ri-scaricando manualmente i 5 comuni mancanti in una seconda passata,
  non ancora corretto nel codice (nessun retry generico su errori di
  rete transitori — voce aperta per il futuro).
- **`UnicodeEncodeError` ripetuto su console Windows**: ogni messaggio di
  log contenente "✓"/"✗" falliva silenziosamente sulla console (cp1252 di
  Windows non ha questi caratteri), con loguru che stampava un traceback
  di errore invece del messaggio — non bloccante ma molto rumoroso su run
  lunghi. Fix in `src/utils/logger.py`: `sys.stdout.reconfigure(encoding=
  'utf-8')` prima di configurare l'handler console.

## Prossimi passi

Queste analisi producono CSV in `output/` — usati in mappe GIS (QGIS) e
nella dashboard Streamlit (vedi [Mappe GIS](gis-maps.md),
[Dashboard](dashboard.md)), entrambe già aggiornate ai comuni più
recenti. Resta aperta la tabella `kpi` (che ha `annual_anomaly`, non
ancora calcolabile senza una baseline 1961-1990 — vedi
[Catalogo KPI](kpi-catalog.md)), e un retry più generico per errori di
rete transitori in `download_data.py` (vedi bug sopra).

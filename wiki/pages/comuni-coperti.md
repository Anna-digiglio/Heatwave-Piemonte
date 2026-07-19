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

**Stato al 2026-07-18 (aggiornato due volte in giornata)**: **177 comuni
coperti su 1180** (8 capoluoghi di provincia + 169 extra), 2000-01-01 →
oggi.

**Stato al 2026-07-19 (import comuni ARPA-target dalla collaboratrice)**:
**234 comuni coperti** — importati i 57 comuni consegnati dalla
collaboratrice (vedi sezione "Obiettivo reale" sotto per il dettaglio),
`temperature` ora a 2.268.823 righe. Ricalcolo a valle completo: elevazione
234/234, `heatwave_events` 640 → **770**, `kpi_annual_by_municipality`
**6.318 righe** (234 comuni × 27 anni), `kpi_annual_by_province` invariato
a 216. `download_arpa.py` rilanciato di conseguenza (su richiesta esplicita
dell'utente, dopo un primo fraintendimento): **108/234 comuni Open-Meteo
hanno anche ARPA** (era 51), la mappa Bias raddoppia di campione. Pipeline
di analisi completa rieseguita (`refresh_dashboard.py`, ~2h20min totali
con un'interruzione e ripartenza a metà) — vedi [Pipeline
ETL](etl-pipeline.md#import-dei-57-comuni-arpa-target-e-ricalcolo-completo-2026-07-19)
per il resoconto completo e [Analisi
statistica](statistical-analysis.md#validazione-contro-arpa-piemonte-2026-07-18-estesa-il-2026-07-19)
per i risultati aggiornati (bias -1.59°C, quasi invariato).

**Aggiornamento delta del 2026-07-19**: serie estesa fino al 2026-07-19 per
**177/177 comuni** via `update_recent_data.py` (nessun comune nuovo, solo
delta sui comuni già coperti — nessun blocco da quota Open-Meteo su questo
run, solo `ConnectionResetError` transitori). Primo passaggio: 167/177
riusciti, 10 falliti per connessione (Borgoratto Alessandrino, Cessole,
Fubine Monferrato, Marentino, Pietraporzio, Robella, Roletto, Usseglio,
Vigone, Vinchio); **retry mirato sugli stessi 10 riuscito 10/10**. Dati
scaricati ma **non ancora importati** in `temperature`, fermi in
`data/raw/temperature_data_recent.csv` in attesa di import manuale (pulizia
+ join + `insert_temperature_for_municipalities` + ricalcolo a valle, vedi
["Nota per chi importa"](#nota-per-chi-importa-di-solito-il-titolare-o-lia)
sotto).

**Download comuni extra — provincia di Torino (2026-07-19)**: su richiesta
esplicita dell'utente, oltre al delta si è provato a scaricare comuni
**nuovi** (non ancora in `temperature`) partendo dalla provincia di Torino
(266 mancanti su 312), storico completo 2000-01-01 → oggi, selezionati con
lo stesso criterio spaziale di
[`download_extra_municipalities.py`](#nota-per-chi-importa-di-solito-il-titolare-o-lia)
(farthest-point sampling dagli anchor già coperti). **Bloccato dalla quota
giornaliera Open-Meteo dopo soli 18 comuni** (contro i 57+ osservati nei
run di delta da 1-2 giorni): conferma empirica che la quota è legata al
**volume di dati** scaricato, non al numero di richieste — uno storico
completo (~9.700 righe/comune) consuma la quota molto più in fretta di un
delta giornaliero (1-2 righe/comune). Segnale di blocco: dopo alcuni
throttle "al minuto" recuperabili (backoff crescente, si risolvono da
soli), su `Vestignè` i 5 tentativi sono tutti falliti
(`RuntimeError: Rate limit persistente`) e il comune successivo
(`Montanaro`) ha iniziato subito a fallire allo stesso modo — a quel punto
il run è stato interrotto manualmente per non bruciare ore sui retry dei
~246 comuni restanti (ogni comune bloccato costa fino a ~155s di backoff
prima di passare al successivo).

Esito: **18 comuni scaricati con successo** (storico completo, non ancora
importati), 2 falliti per `ConnectionResetError` (Pragelato, Roure — da
riprovare, non è quota), 1 bloccato da quota (Vestignè), 1 interrotto a
metà retry quando il processo è stato fermato (Montanaro, esito
sconosciuto — da riprovare). Output in
`data/raw/temperature_data_extra_torino_2026-07-19.csv` (nome scelto per
non mischiarsi con il precedente `temperature_data_extra.csv` del
2026-07-18, già importato). Comuni scaricati in questa sessione:
Ala di Stura, Angrogna, Burolo, Carmagnola, Castagneto Po, Cuorgnè,
Groscavallo, Ingria, Maglione, Moncalieri, Oulx, Pancalieri, Piscina,
Prali, Prarostino, Riva presso Chieri, Val della Torre, Viù.

**Correzione (stessa giornata)**: il download di Torino sopra era partito
da un fraintendimento — l'obiettivo reale della richiesta dell'utente non
era "estendere la copertura spaziale genericamente", ma **scaricare
Open-Meteo per i comuni che hanno già una stazione ARPA attiva ma non
hanno ancora dati Open-Meteo**, per completare la mappa **Bias
Open-Meteo↔ARPA per comune** (oggi disponibile solo sui 51 comuni che
hanno entrambe le fonti, su 218 comuni ARPA totali). Vedi la sezione
dedicata subito sotto per la lista esatta e lo stato.

Per puro caso **9 dei 18 comuni di Torino scaricati sopra hanno anche
ARPA** (Ala di Stura, Angrogna, Carmagnola, Castagneto Po, Groscavallo,
Moncalieri, Oulx, Prali, Viù) e contano comunque per l'obiettivo reale,
anche se non erano stati scelti per quello. Gli altri 9 (Burolo, Cuorgnè,
Ingria, Maglione, Pancalieri, Piscina, Prarostino, Riva presso Chieri, Val
della Torre) restano utili per la copertura spaziale generale ma non
contribuiscono al confronto ARPA.

## Obiettivo reale: completare la mappa Bias Open-Meteo↔ARPA

**A cosa serve questa sezione**: dei **218 comuni con stazione ARPA
attiva**, solo **51** hanno anche dati Open-Meteo (vedi sezione sopra) —
gli altri **167** hanno ARPA ma **non** Open-Meteo, quindi non compaiono
nella mappa di confronto/bias. Per completarla serve scaricare Open-Meteo
(**storico completo 2000-01-01 → oggi**, non un delta — il bias si calcola
su serie storiche, non su un giorno) per questi 167 comuni.

**Stato al 2026-07-19 (mattina)**: di questi 167, **9 sono già stati
scaricati per caso** durante il tentativo (mal indirizzato) di stamattina
su Torino, vedi sopra — ma **non ancora importati** in `temperature`.
Restano **158 comuni** da scaricare ancora. Quota Open-Meteo di oggi già
bloccata (vedi sopra) — **da riprendere il giorno dopo il reset**, non lo
stesso giorno.

**Aggiornamento (stesso giorno, poco dopo)**: la collaboratrice (stessa
seconda macchina delle sessioni precedenti) ha consegnato **57 comuni**
scaricati direttamente dalla lista dei 167 sopra (round-robin per
provincia, non nell'ordine della tabella — vedi
[Pipeline ETL](etl-pipeline.md#comuni-extra-mirati-alla-validazione-arpa--158-comuni-target-2026-07-19)
per il dettaglio completo del suo download, bloccato anche lei dalla
quota dopo 57/158). **Importati nel DB** (pulizia + join `istat_code` →
`municipality_id` + `insert_temperature_for_municipalities` + ricalcolo a
valle completo, vedi sopra): **234 comuni** ora in `temperature`.
`download_arpa.py` rilanciato di conseguenza: 108/234 comuni con
Open-Meteo hanno anche una stazione ARPA attiva (i 51 di prima + tutti i
57 nuovi, confermando che la lista target era corretta al 100%) — vedi
[Fonti Dati](data-sources.md) per l'esito finale del download e il nuovo
numero di comuni utilizzabili nella mappa Bias.

**Restano 101 comuni** (167 - 9 Torino - 57 collaboratrice) dei 167
originali ancora da scaricare per completare la copertura Open-Meteo su
tutti i comuni ARPA — target per le prossime sessioni, dopo il reset della
quota giornaliera.

<details>
<summary>I 167 comuni ARPA senza Open-Meteo, per provincia (✅ = già scaricato oggi via Torino, non ancora importato)</summary>

| Provincia | Comune | Codice ISTAT | Scaricato oggi |
|---|---|---|---|
| Alessandria | Acqui Terme | 006001 |  |
| Alessandria | Arquata Scrivia | 006009 |  |
| Alessandria | Basaluzzo | 006012 |  |
| Alessandria | Brignano-Frascata | 006024 |  |
| Alessandria | Cabella Ligure | 006025 |  |
| Alessandria | Casale Monferrato | 006039 |  |
| Alessandria | Casaleggio Boiro | 006038 |  |
| Alessandria | Fabbrica Curone | 006067 |  |
| Alessandria | Garbagna | 006079 |  |
| Alessandria | Gavi | 006081 |  |
| Alessandria | Ovada | 006121 |  |
| Alessandria | Ponzone | 006136 |  |
| Alessandria | Roccaforte Ligure | 006146 |  |
| Alessandria | San Salvatore Monferrato | 006154 |  |
| Alessandria | Sardigliano | 006157 |  |
| Alessandria | Serralunga di Crea | 006159 |  |
| Alessandria | Sezzadio | 006161 |  |
| Alessandria | Vignale Monferrato | 006179 |  |
| Asti | Buttigliera d'Asti | 005012 |  |
| Asti | Castagnole delle Lanze | 005022 |  |
| Asti | Castell'Alfero | 005025 |  |
| Asti | Loazzolo | 005060 |  |
| Asti | Mombaldone | 005064 |  |
| Asti | Montaldo Scarampi | 005074 |  |
| Asti | Montechiaro d'Asti | 005075 |  |
| Asti | Nizza Monferrato | 005080 |  |
| Asti | Roccaverano | 005094 |  |
| Asti | San Damiano d'Asti | 005097 |  |
| Biella | Graglia | 096028 |  |
| Biella | Masserano | 096032 |  |
| Biella | Pettinengo | 096042 |  |
| Biella | Piatto | 096043 |  |
| Biella | Pray | 096050 |  |
| Biella | Salussola | 096058 |  |
| Biella | Valdilana | 096088 |  |
| Cuneo | Alba | 004003 |  |
| Cuneo | Argentera | 004006 |  |
| Cuneo | Baldissero d'Alba | 004010 |  |
| Cuneo | Barge | 004012 |  |
| Cuneo | Bellino | 004017 |  |
| Cuneo | Belvedere Langhe | 004018 |  |
| Cuneo | Boves | 004028 |  |
| Cuneo | Bra | 004029 |  |
| Cuneo | Brossasco | 004033 |  |
| Cuneo | Canosio | 004038 |  |
| Cuneo | Carrù | 004043 |  |
| Cuneo | Castelletto Uzzone | 004050 |  |
| Cuneo | Castellinaldo d'Alba | 004051 |  |
| Cuneo | Ceva | 004066 |  |
| Cuneo | Crissolo | 004077 |  |
| Cuneo | Demonte | 004079 |  |
| Cuneo | Dronero | 004082 |  |
| Cuneo | Elva | 004083 |  |
| Cuneo | Feisoglio | 004088 |  |
| Cuneo | Fossano | 004089 |  |
| Cuneo | Frabosa Soprana | 004090 |  |
| Cuneo | Garessio | 004095 |  |
| Cuneo | Marene | 004117 |  |
| Cuneo | Mombarcaro | 004124 |  |
| Cuneo | Mondovì | 004130 |  |
| Cuneo | Morozzo | 004144 |  |
| Cuneo | Neive | 004148 |  |
| Cuneo | Ormea | 004155 |  |
| Cuneo | Paesana | 004157 |  |
| Cuneo | Pamparato | 004159 |  |
| Cuneo | Paroldo | 004160 |  |
| Cuneo | Perlo | 004162 |  |
| Cuneo | Peveragno | 004163 |  |
| Cuneo | Priero | 004175 |  |
| Cuneo | Prunetto | 004178 |  |
| Cuneo | Roccaforte Mondovì | 004190 |  |
| Cuneo | Roddino | 004195 |  |
| Cuneo | Rodello | 004196 |  |
| Cuneo | Saluzzo | 004203 |  |
| Cuneo | Sampeyre | 004205 |  |
| Cuneo | San Damiano Macra | 004207 |  |
| Cuneo | Somano | 004221 |  |
| Cuneo | Treiso | 004230 |  |
| Cuneo | Valdieri | 004233 |  |
| Cuneo | Vernante | 004239 |  |
| Cuneo | Villanova Solaro | 004246 |  |
| Cuneo | Viola | 004249 |  |
| Novara | Ameno | 003002 |  |
| Novara | Armeno | 003006 |  |
| Novara | Cameri | 003032 |  |
| Novara | Paruzzaro | 003114 |  |
| Novara | Varallo Pombia | 003154 |  |
| Torino | Ala di Stura | 001003 | ✅ |
| Torino | Andrate | 001010 |  |
| Torino | Angrogna | 001011 | ✅ |
| Torino | Avigliana | 001013 |  |
| Torino | Balme | 001019 |  |
| Torino | Borgofranco d'Ivrea | 001030 |  |
| Torino | Borgone Susa | 001032 |  |
| Torino | Brosso | 001036 |  |
| Torino | Caluso | 001047 |  |
| Torino | Candia Canavese | 001050 |  |
| Torino | Carmagnola | 001059 | ✅ |
| Torino | Castagneto Po | 001064 | ✅ |
| Torino | Cesana Torinese | 001074 |  |
| Torino | Chiomonte | 001080 |  |
| Torino | Chivasso | 001082 |  |
| Torino | Coazze | 001089 |  |
| Torino | Colleretto Castelnuovo | 001091 |  |
| Torino | Condove | 001093 |  |
| Torino | Cumiana | 001097 |  |
| Torino | Druento | 001099 |  |
| Torino | Fenestrelle | 001103 |  |
| Torino | Front | 001109 |  |
| Torino | Giaglione | 001114 |  |
| Torino | Groscavallo | 001118 | ✅ |
| Torino | Lanzo Torinese | 001128 |  |
| Torino | Luserna San Giovanni | 001139 |  |
| Torino | Monastero di Lanzo | 001155 |  |
| Torino | Moncalieri | 001156 | ✅ |
| Torino | Oulx | 001175 | ✅ |
| Torino | Parella | 001179 |  |
| Torino | Perrero | 001186 |  |
| Torino | Pinerolo | 001191 |  |
| Torino | Pragelato | 001201 |  |
| Torino | Prali | 001202 | ✅ |
| Torino | Rivoli | 001219 |  |
| Torino | Ronco Canavese | 001224 |  |
| Torino | Sauze d'Oulx | 001259 |  |
| Torino | Sestriere | 001263 |  |
| Torino | Susa | 001270 |  |
| Torino | Trana | 001276 |  |
| Torino | Traversella | 001278 |  |
| Torino | Valchiusa | 001318 |  |
| Torino | Varisella | 001289 |  |
| Torino | Venaria Reale | 001292 |  |
| Torino | Venaus | 001291 |  |
| Torino | Verolengo | 001293 |  |
| Torino | Vialfrè | 001296 |  |
| Torino | Villafranca Piemonte | 001300 |  |
| Torino | Viù | 001313 | ✅ |
| Verbano-Cusio-Ossola | Antrona Schieranco | 103001 |  |
| Verbano-Cusio-Ossola | Baceno | 103006 |  |
| Verbano-Cusio-Ossola | Bannio Anzino | 103007 |  |
| Verbano-Cusio-Ossola | Bognanco | 103012 |  |
| Verbano-Cusio-Ossola | Cannobio | 103017 |  |
| Verbano-Cusio-Ossola | Ceppo Morelli | 103021 |  |
| Verbano-Cusio-Ossola | Cesara | 103022 |  |
| Verbano-Cusio-Ossola | Cossogno | 103023 |  |
| Verbano-Cusio-Ossola | Crodo | 103026 |  |
| Verbano-Cusio-Ossola | Domodossola | 103028 |  |
| Verbano-Cusio-Ossola | Druogno | 103029 |  |
| Verbano-Cusio-Ossola | Mergozzo | 103044 |  |
| Verbano-Cusio-Ossola | Montecrestese | 103046 |  |
| Verbano-Cusio-Ossola | Omegna | 103050 |  |
| Verbano-Cusio-Ossola | Pieve Vergonte | 103054 |  |
| Verbano-Cusio-Ossola | Premia | 103056 |  |
| Verbano-Cusio-Ossola | Stresa | 103064 |  |
| Verbano-Cusio-Ossola | Toceno | 103065 |  |
| Verbano-Cusio-Ossola | Trasquera | 103067 |  |
| Verbano-Cusio-Ossola | Trontano | 103068 |  |
| Verbano-Cusio-Ossola | Valle Cannobina | 103079 |  |
| Verbano-Cusio-Ossola | Varzo | 103071 |  |
| Vercelli | Albano Vercellese | 002003 |  |
| Vercelli | Alto Sermenza | 002170 |  |
| Vercelli | Boccioleto | 002014 |  |
| Vercelli | Carcoforo | 002029 |  |
| Vercelli | Cellio con Breia | 002171 |  |
| Vercelli | Lozzolo | 002072 |  |
| Vercelli | Rassa | 002110 |  |
| Vercelli | Tricerro | 002147 |  |
| Vercelli | Varallo | 002156 |  |

</details>

**Per la prossima sessione**: aspettare il reset della quota (il giorno
dopo, non lo stesso giorno) e scaricare storico completo 2000→oggi per i
158 comuni sopra non ancora marcati ✅ (usando lo stesso approccio di
`download_extra_municipalities.py`, ma filtrando esplicitamente su questa
lista invece che su un campionamento spaziale generico — qui serve
**tutta** la lista, non un sottoinsieme rappresentativo). Dato il limite
osservato oggi (~18-20 comuni a storico completo prima del blocco), serviranno
**8-9 sessioni giornaliere** per completarla tutta, salvo che la quota si
riveli più permissiva in altri giorni. **Attenzione a non sovrapporsi con
il file che arriverà dalla collega** (vedi sezione sotto): se anche lei
sta scaricando comuni extra in questi giorni, controllare i nomi prima di
importare per evitare doppioni.

## Comuni già coperti (NON riscaricare questi)

### Alessandria (28/187 comuni coperti)

| Comune | Codice ISTAT |
|---|---|
| Alessandria | 006003 |
| Alfiano Natta | 006004 |
| Alice Bel Colle | 006005 |
| Bassignana | 006013 |
| Borgoratto Alessandrino | 006019 |
| Bosio | 006022 |
| Bozzole | 006023 |
| Carrega Ligure | 006034 |
| Casalnoceto | 006040 |
| Casasco | 006041 |
| Cereseto | 006057 |
| Fraconalto | 006069 |
| Fubine Monferrato | 006076 |
| Gremiasco | 006083 |
| Grondona | 006085 |
| Isola Sant'Antonio | 006087 |
| Malvicino | 006090 |
| Merana | 006093 |
| Molare | 006095 |
| Moncestino | 006099 |
| Montaldeo | 006103 |
| Morsasco | 006112 |
| Novi Ligure | 006114 |
| Occimiano | 006115 |
| Predosa | 006140 |
| Sant'Agata Fossili | 006156 |
| Tortona | 006174 |
| Villanova Monferrato | 006185 |

### Asti (19/117 comuni coperti)

| Comune | Codice ISTAT |
|---|---|
| Asti | 005005 |
| Cerro Tanaro | 005036 |
| Cessole | 005037 |
| Cisterna d'Asti | 005040 |
| Coazzolo | 005041 |
| Cortazzone | 005047 |
| Maranzana | 005061 |
| Moncalvo | 005069 |
| Moncucco Torinese | 005070 |
| Montegrosso d'Asti | 005076 |
| Moransengo-Tonengo | 005122 |
| Robella | 005092 |
| San Martino Alfieri | 005099 |
| Serole | 005104 |
| Sessame | 005105 |
| Viarigi | 005115 |
| Villa San Secondo | 005119 |
| Villanova d'Asti | 005118 |
| Vinchio | 005120 |

### Biella (11/74 comuni coperti)

| Comune | Codice ISTAT |
|---|---|
| Biella | 096004 |
| Camandona | 096009 |
| Caprile | 096013 |
| Cavaglià | 096016 |
| Donato | 096024 |
| Gifflenga | 096027 |
| Magnano | 096030 |
| Mezzana Mortigliengo | 096033 |
| Piedicavallo | 096044 |
| Valdengo | 096071 |
| Villa del Bosco | 096078 |

### Cuneo (41/247 comuni coperti)

| Comune | Codice ISTAT |
|---|---|
| Acceglio | 004001 |
| Aisone | 004002 |
| Alto | 004005 |
| Bagnasco | 004008 |
| Bagnolo Piemonte | 004009 |
| Bastia Mondovì | 004014 |
| Briga Alta | 004031 |
| Casalgrasso | 004045 |
| Castelmagno | 004053 |
| Cavallermaggiore | 004059 |
| Cherasco | 004067 |
| Chiusa di Pesio | 004068 |
| Costigliole Saluzzo | 004075 |
| Cravanzana | 004076 |
| Cuneo | 004078 |
| Entracque | 004084 |
| Gaiola | 004093 |
| Genola | 004096 |
| Govone | 004099 |
| Grinzane Cavour | 004100 |
| Limone Piemonte | 004110 |
| Mombasiglio | 004125 |
| Monchiero | 004129 |
| Montà | 004133 |
| Monterosso Grana | 004139 |
| Oncino | 004154 |
| Pianfei | 004165 |
| Pietraporzio | 004167 |
| Pontechianale | 004172 |
| Rifreddo | 004181 |
| Robilante | 004185 |
| Roburent | 004186 |
| Roccabruna | 004187 |
| Saliceto | 004201 |
| Santo Stefano Belbo | 004213 |
| Sommariva del Bosco | 004222 |
| Stroppo | 004224 |
| Torre San Giorgio | 004228 |
| Torresina | 004229 |
| Trinità | 004232 |
| Vinadio | 004248 |

### Novara (16/87 comuni coperti)

| Comune | Codice ISTAT |
|---|---|
| Borgolavezzaro | 003023 |
| Borgomanero | 003024 |
| Casaleggio Novara | 003039 |
| Castelletto sopra Ticino | 003043 |
| Cerano | 003049 |
| Colazza | 003051 |
| Galliate | 003068 |
| Ghemme | 003073 |
| Grignasco | 003079 |
| Lesa | 003084 |
| Momo | 003100 |
| Novara | 003106 |
| Oleggio | 003108 |
| Pettenasco | 003116 |
| San Nazzaro Sesia | 003134 |
| Vinzaglio | 003164 |

### Torino (46/312 comuni coperti)

| Comune | Codice ISTAT |
|---|---|
| Agliè | 001001 |
| Bardonecchia | 001022 |
| Barone Canavese | 001023 |
| Bobbio Pellice | 001026 |
| Bruino | 001038 |
| Campiglione Fenile | 001049 |
| Candiolo | 001051 |
| Carema | 001057 |
| Carignano | 001058 |
| Caselle Torinese | 001063 |
| Castelnuovo Nigra | 001067 |
| Ceres | 001072 |
| Ceresole Reale | 001073 |
| Chiusa di San Michele | 001081 |
| Claviere | 001087 |
| Coassolo Torinese | 001088 |
| Favria | 001101 |
| Fiano | 001104 |
| Gravere | 001117 |
| Lemie | 001131 |
| Locana | 001134 |
| Marentino | 001144 |
| Massello | 001145 |
| Moncenisio | 001157 |
| Noasca | 001165 |
| Pianezza | 001189 |
| Pino Torinese | 001192 |
| Piverone | 001196 |
| Pomaretto | 001198 |
| Pralormo | 001203 |
| Rocca Canavese | 001221 |
| Roletto | 001222 |
| Rorà | 001226 |
| Salbertrand | 001232 |
| Samone | 001235 |
| San Giorio di Susa | 001245 |
| Santena | 001257 |
| Sauze di Cesana | 001258 |
| Sparone | 001267 |
| Torino | 001272 |
| Torrazza Piemonte | 001273 |
| Usseglio | 001282 |
| Valprato Soana | 001288 |
| Verrua Savoia | 001294 |
| Vigone | 001299 |
| Volpiano | 001314 |

### Verbano-Cusio-Ossola (6/74 comuni coperti)

| Comune | Codice ISTAT |
|---|---|
| Craveggia | 103024 |
| Formazza | 103031 |
| Macugnaga | 103039 |
| Madonna del Sasso | 103040 |
| Verbania | 103072 |
| Villadossola | 103075 |

### Vercelli (10/82 comuni coperti)

| Comune | Codice ISTAT |
|---|---|
| Alagna Valsesia | 002002 |
| Carisio | 002032 |
| Fontanetto Po | 002058 |
| Ghislarengo | 002062 |
| Moncrivello | 002079 |
| Motta de' Conti | 002082 |
| Rimella | 002113 |
| Scopello | 002135 |
| Valduggia | 002152 |
| Vercelli | 002158 |

## Comuni prioritari per l'aggiornamento giornaliero (copertura ARPA)

**A cosa serve questa sezione**: dei 177 comuni coperti, **51 hanno anche
una stazione ARPA attiva** con sensore di temperatura (vedi [Fonti
Dati](data-sources.md#arpa-piemonte--integrata-e-scaricata-2026-07-18)) e
sono quindi gli unici utilizzabili per il confronto/validazione
Open-Meteo↔ARPA (bias, trend, eventi — vedi [Analisi
statistica](statistical-analysis.md#validazione-contro-arpa-piemonte-2026-07-18)).
Dal 2026-07-19 `update_recent_data.py` (funzione
`load_municipalities_with_data()`) li scarica **per primi** (query ordinata
`has_arpa DESC, nome`), perché la quota giornaliera Open-Meteo è
imprevedibile (vedi sotto) e un run interrotto a metà deve comunque aver
già garantito il delta utile al confronto, prima del resto dei comuni in
ordine alfabetico.

Se una sessione di aggiornamento si interrompe prima di coprire tutti i
177 comuni, **controllare per primi questi 51** (via log o query su
`temperature` per la data massima per comune) prima di considerare il
delta del giorno completo.

| Comune | Codice ISTAT | Esito delta 2026-07-19 |
|---|---|---|---|
| Acceglio | 004001 | ✅ |
| Alagna Valsesia | 002002 | ✅ |
| Alessandria | 006003 | ✅ |
| Asti | 005005 | ✅ |
| Bardonecchia | 001022 | ✅ |
| Biella | 096004 | ✅ |
| Bobbio Pellice | 001026 | ✅ |
| Borgomanero | 003024 | ✅ |
| Bosio | 006022 | ✅ |
| Briga Alta | 004031 | ✅ |
| Carrega Ligure | 006034 | ✅ |
| Caselle Torinese | 001063 | ✅ |
| Castelmagno | 004053 | ✅ |
| Cerano | 003049 | ✅ |
| Ceresole Reale | 001073 | ✅ |
| Chiusa di Pesio | 004068 | ✅ |
| Costigliole Saluzzo | 004075 | ✅ |
| Cuneo | 004078 | ✅ |
| Entracque | 004084 | ✅ |
| Formazza | 103031 | ✅ |
| Govone | 004099 | ✅ |
| Isola Sant'Antonio | 006087 | ✅ |
| Lemie | 001131 | ✅ |
| Limone Piemonte | 004110 | ✅ |
| Locana | 001134 | ✅ |
| Macugnaga | 103039 | ✅ |
| Marentino | 001144 | ✅ (riuscito al retry) |
| Massello | 001145 | ✅ |
| Momo | 003100 | ✅ |
| Monterosso Grana | 004139 | ✅ |
| Noasca | 001165 | ✅ |
| Novara | 003106 | ✅ |
| Novi Ligure | 006114 | ✅ |
| Piedicavallo | 096044 | ✅ |
| Pino Torinese | 001192 | ✅ |
| Piverone | 001196 | ✅ |
| Pontechianale | 004172 | ✅ |
| Pralormo | 001203 | ✅ |
| Salbertrand | 001232 | ✅ |
| Saliceto | 004201 | ✅ |
| Santena | 001257 | ✅ |
| Sauze di Cesana | 001258 | ✅ |
| Serole | 005104 | ✅ |
| Sparone | 001267 | ✅ |
| Torino | 001272 | ✅ |
| Tortona | 006174 | ✅ |
| Usseglio | 001282 | ✅ (riuscito al retry) |
| Valprato Soana | 001288 | ✅ |
| Verbania | 103072 | ✅ |
| Vercelli | 002158 | ✅ |
| Vinadio | 004248 | ✅ |

## Come scaricare nuovi comuni (Open-Meteo, storico 2000 → oggi)

**Fonte**: Open-Meteo Archive API (`https://archive-api.open-meteo.com/v1/archive`),
nessuna chiave richiesta. **Limite scoperto sul campo**: oltre al rate
limit "al minuto", esiste un **limite giornaliero**, ma la sua entità
esatta resta poco chiara — **variabile da un giorno all'altro**, non un
numero fisso: la prima volta (2026-07-17) ci si è bloccati dopo ~19-20
comuni, mentre il 2026-07-18 una sessione ne ha ottenuti 57 e un'altra,
in parallelo sullo stesso giorno, solo 22 prima di bloccarsi. Ipotesi non
confermata: la quota potrebbe essere legata al volume di dati scaricato
più che a un conteggio piatto di richieste (coerente con un'osservazione
simile del 2026-07-17, vedi [Fonti Dati](data-sources.md)). Consiglio
pratico: scaricare **a lotti piccoli** (10-20 comuni), fermarsi appena
arriva un errore `429`/messaggio di quota esaurita **o appena i download
smettono di progredire per diversi minuti senza errori espliciti**
(osservato il 2026-07-18: il processo può restare "vivo" ma bloccato nei
retry senza produrre output visibile), e riprendere il giorno dopo — non
serve a niente insistere, la quota si resetta il giorno successivo.

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
|---|---|---|---|
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

# Heatwave Piemonte — Istruzioni per Claude

Questo repository mantiene una **wiki persistente** in `wiki/`, secondo il pattern
descritto da Andrej Karpathy ("LLM Wiki", vedi
https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). Questo file è
il **livello schema**: definisce come la wiki è strutturata e come va mantenuta.
Leggilo prima di rispondere a domande sul progetto o prima di modificare codice/dati.

## I tre livelli

1. **Sorgenti grezze (immutabili, non toccare per "aggiornare la wiki")**
   - Codice: `src/**`, `sql/*.sql`, `config.yaml`
   - Documenti di pianificazione originali: `README.md`, `PROJECT_SUMMARY.md`,
     `SIMPLIFICATION_SUMMARY.md`, `docs/*.md`
   - Dati: `data/raw`, `data/processed`, `data/external`, `logs/`

   Questi documenti descrivono spesso uno stato **aspirazionale/pianificato**
   (es. "1.7M record", "dashboard con 5 pagine") che non corrisponde ancora al
   codice realmente presente. Non prenderli mai come verità sullo stato attuale
   senza verificare il codice.

2. **Wiki (`wiki/`)** — di proprietà di Claude, va tenuta sincronizzata con lo
   stato reale del codice, non con le intenzioni dei documenti di pianificazione.
   - `wiki/index.md` — catalogo di tutte le pagine, organizzato per categoria
   - `wiki/log.md` — log cronologico append-only di ingest/query/lint
   - `wiki/pages/*.md` — pagine di sintesi (entità, concetti, stato del progetto)

3. **Schema** — questo file.

## Convenzioni

- Nomi pagina in kebab-case, sempre sotto `wiki/pages/`.
- Le pagine sono in italiano (lingua del progetto e del README).
- Link tra pagine con markdown relativo standard, es. `[ETL](etl-pipeline.md)`.
- Ogni pagina cita le sorgenti grezze da cui è sintetizzata (path relativi).
- La pagina `wiki/pages/project-status.md` è quella più delicata: distingue
  sempre "pianificato nei docs" da "effettivamente implementato nel codice".

## Workflow — Ingest

Quando arriva materiale nuovo (nuovo script in `src/`, nuova tabella SQL, nuovo
dato scaricato, nuovo file in `docs/`):

1. Leggi la sorgente.
2. Aggiorna la/le pagine wiki pertinenti (di solito 1-4 pagine: la pagina di
   dominio + `project-status.md` + eventualmente `data-model.md` o
   `architecture.md`).
3. Aggiorna `wiki/index.md` se è una pagina nuova o se il riassunto è cambiato.
4. Aggiungi una riga a `wiki/log.md` con data, azione, pagine toccate.

## Workflow — Query

Quando l'utente fa una domanda sul progetto:

1. Cerca prima nelle pagine wiki pertinenti (`wiki/index.md` per orientarti).
2. Se la wiki non basta, leggi la sorgente grezza citata dalla pagina.
3. Se l'esplorazione produce sintesi utile e riusabile, valuta se aggiungerla
   come nuova pagina (o sezione) invece di ripeterla solo in chat.

## Workflow — Lint

Periodicamente (o quando richiesto esplicitamente, es. "controlla la wiki"):

- Verifica che le pagine non contraddicano il codice attuale (in particolare
  `data-model.md` contro `sql/01_init_database.sql`, `etl-pipeline.md` contro
  `src/data_acquisition/`, `src/data_processing/`, `src/database/`).
- Segnala pagine orfane (non linkate da `index.md`) o claim non più validi.
- Aggiorna `project-status.md` con lo stato reale rilevato.

## Nota sul contesto del progetto

Progetto portfolio (Data Engineering / Data Science / GIS) di un utente con
laurea in Scienze Naturali, in formazione ITS "Data Manager for Business
Intelligence Software Developer". Le spiegazioni tecniche nella wiki possono
collegare i concetti statistici/GIS a nozioni di scienze naturali quando utile,
ma il livello tecnico va mantenuto professionale (portfolio da mostrare a
recruiter/tech lead).

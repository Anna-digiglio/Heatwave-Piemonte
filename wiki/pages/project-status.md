# Stato del progetto (pianificato vs implementato)

**Sorgenti**: confronto diretto tra `docs/ROADMAP.md`/`PROJECT_SUMMARY.md`
(pianificazione) e stato reale delle cartelle/codice al 2026-07-04.

Questa pagina è quella con la scadenza più breve nella wiki: va aggiornata a
ogni sessione di lavoro rilevante (vedi workflow di ingest in `CLAUDE.md`).

## Settimana 1 — Setup & Data Acquisition

| Attività | Roadmap | Realtà |
|---|---|---|
| Struttura repo | ✅ | ✅ |
| Schema DB (`01_init_database.sql`) | ✅ | ✅ completo: 6 tabelle, 2 viste, 1 funzione, 25+ indici |
| Script download (`download_data.py`) | pianificato | ✅ scritto, **ma con bug di import** (vedi [Fonti Dati](data-sources.md)) — non testato su run reale |
| Download dati 2000-2026 | ⬜ | ❌ non eseguito — esiste solo `test_open_meteo_torino.csv` (1 riga) |
| Dati geografici (ISTAT comuni/province) | ⬜ | ❌ non scaricati — `municipalities` è vuota |
| Python environment / requirements | ⬜ | `.venv` presente, `requirements.txt` presente e dettagliato |

## Settimana 2 — ETL & Analisi

| Attività | Roadmap | Realtà |
|---|---|---|
| `DataCleaner` completo | pianificato | ✅ scritto e ragionevolmente completo (vedi [ETL](etl-pipeline.md)) |
| Caricamento `temperature` nel DB | pianificato | ❌ `load_to_db.py` crea solo schema + 1 record di test, non carica CSV reali |
| `identify_heatwaves()` eseguita | pianificato | Funzione SQL scritta, mai eseguita (nessun dato da processare) |
| KPI calcolati | pianificato | Solo via viste materializzate SQL (vuote, nessun dato sotto) |
| Query SQL (10+) | pianificato | 3 query scritte in `02_common_queries.sql` |

## Settimana 3 — Visualizzazione & Deployment

| Attività | Roadmap | Realtà |
|---|---|---|
| `src/analysis/` (statistica, spaziale, temporale) | pianificato | ❌ cartella vuota |
| `src/visualization/` | pianificato | ❌ cartella vuota |
| Progetti QGIS | pianificato | ❌ `qgis_projects/` vuota |
| Dashboard Streamlit | pianificato | ❌ `dashboard/` vuota |
| Test unitari | pianificato (70%+ coverage) | ❌ `tests/` vuota |
| Documentazione | in gran parte fatta | ✅ README, PROJECT_SUMMARY, docs/* molto estesi (a volte più avanti del codice) |

## Prossimo passo a maggiore impatto

Nell'ordine, sbloccano tutto il resto:

1. **Fixare il bug di import in `download_data.py`** (annotazione `cdsapi.Client`)
2. **Eseguire un download reale** (anche solo Open-Meteo, senza Copernicus, per
   partire) → popola `data/raw/`
3. **Popolare `municipalities`** con dati ISTAT reali (oggi solo `provinces` ha
   8 record seed)
4. **Scrivere il pezzo mancante di `load_to_db.py`** che carica
   `data/processed/temperature_clean.csv` nella tabella `temperature` a batch
   — oggi è il buco più grande della pipeline (vedi [ETL](etl-pipeline.md))
5. Solo dopo (4), tutto il resto (KPI, mappe, dashboard, analisi statistiche)
   ha dati reali su cui lavorare

## Discrepanze da tenere a mente quando si presenta il progetto

`README.md` e `PROJECT_SUMMARY.md` descrivono metriche come "1.7M record",
"Status: Production Ready", "database size 3-5 GB" — sono **target
pianificati**, scritti prima di scrivere il codice, non misurazioni reali.
Utile saperlo per non presentarli come risultati raggiunti in un colloquio o
in una demo.

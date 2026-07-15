# Test unitari (`tests/`)

**Sorgenti**: `tests/test_data_cleaning.py`, `tests/test_analysis.py`,
`tests/test_config.py`, `pytest.ini`

Stato: **implementati ed eseguiti il 2026-07-15** — 31 test, tutti pure
unit test (nessuno richiede un database o una rete: lavorano su
DataFrame/array sintetici costruiti a mano).

```
python -m pytest tests/ -v
python -m pytest tests/ --cov=src.data_processing --cov=src.analysis --cov=src.utils.config --cov-report=term-missing
```

## Cosa coprono

- **`test_data_cleaning.py`** (15 test) — `DataCleaner`
  (`src/data_processing/clean_data.py`): dedup, gestione missing values,
  validazione range/logica temperatura, outlier IQR, quality flags, e due
  test end-to-end sulla pipeline completa (`clean_data()`). Copertura
  86% del modulo.
- **`test_analysis.py`** (11 test) — solo le funzioni pure di
  `src/analysis/*.py` (Mann-Kendall, regressione lineare, haversine, pesi
  spaziali, indice di Moran, clustering K-means, aggregazioni ondate di
  calore). Le funzioni che leggono dal database (`load_*`, `main()`) non
  sono coperte da unit test — richiederebbero un database di test/mock,
  non fatto in questa sessione.
- **`test_config.py`** (5 test) — `Config.get()` e
  `Config.get_database_url()`, incluso un test di regressione sulla
  precedenza delle variabili d'ambiente su `config.yaml`.

## Bug reale trovato scrivendo i test (2026-07-15)

`test_bad_rows_are_dropped_good_rows_survive` (un dataset sintetico con
una sola riga fuori range fisico, temp_max=999°C) falliva: la riga
sopravviveva alla pipeline invece di essere scartata.

**Causa**: `detect_outliers()` gira *dopo* `validate_temperature()` (che
aveva già segnato la riga `quality_flag=2`, bad) e sovrascriveva
incondizionatamente il flag a `1` (suspect, perché 999°C è anche un
outlier IQR) — **declassando** una riga "bad" a "suspect". Dato che
`apply_quality_flags()` scarta solo `quality_flag >= 2`, la riga
fisicamente impossibile sarebbe finita nel dataset pulito.

**Fix**: `detect_outliers()` ora aggiorna il flag a 1 solo se il flag
attuale è `< 2` (`df.loc[is_outlier & (df['quality_flag'] < 2), 'quality_flag'] = 1`),
non declassando mai un flag già "bad".

**Impatto sui dati reali già caricati**: nessuno. Il bug richiede che una
riga sia *contemporaneamente* fuori range fisico (validata come bad) e un
outlier IQR — condizione mai verificata nei dataset reali già puliti e
caricati (`validate_temperature` aveva sempre trovato 0 righe fuori range
sia su `temperature_data.csv` che su `temperature_data_extra.csv`, vedi
[ETL](etl-pipeline.md)). È comunque un bug di correttezza reale nel
codice, ora corretto e coperto da un test di regressione — sarebbe
scattato silenziosamente su qualunque futuro dataset con un valore
sentinella o un errore di sensore (es. `-999` per missing, un classico).

## Cosa non è coperto (limiti espliciti)

- Nessun test per `src/database/load_to_db.py` (richiede un database live
  — servirebbe un DB di test dedicato o mock di SQLAlchemy, non fatto).
- Nessun test per `src/data_acquisition/download_data.py` (chiamate di
  rete reali — servirebbe mock di `requests`, non fatto).
- `seasonal_analysis.py` (STL) non testato: 0% di copertura, nessuna
  funzione pura isolabile facilmente senza dati temporali realistici.
- `src/visualization/` non esiste ancora (cartella vuota), quindi nessun
  `test_visualization.py` nonostante fosse nominato in `PROJECT_SUMMARY.md`.

Questi limiti sono scelte esplicite per restare a unit test puri e veloci
(l'intera suite gira in ~5 secondi), non un'omissione accidentale.

"""
heatwave_definitions.py - Definizione alternativa (percentile) di ondata di
calore, a scopo di confronto metodologico.

La definizione **canonica** usata in tutto il resto del sito (mappa, KPI
della home, statistiche per comune) è quella già implementata nel database
(`identify_heatwaves()` in `sql/01_init_database.sql`): almeno 3 giorni
consecutivi con temperatura massima sopra una **soglia fissa di 35°C**,
uguale per ogni comune.

Questa è una scelta deliberata di semplicità/uniformità, ma ha un limite: un
comune di montagna che raramente supera i 35°C anche in piena estate non
avrà mai un'ondata "sua", anche se per i suoi standard un'estate è stata
eccezionalmente calda. Una definizione alternativa, comune in climatologia,
usa una soglia **relativa** alla storia del singolo comune: il percentile
90° (o altro) delle sue temperature massime storiche, invece di un numero
fisso uguale per tutti.

Questa funzione implementa quella definizione alternativa, usata solo nel
tab "Dettaglio tecnico" della pagina Ondate di Calore come confronto
illustrativo per il comune selezionato - **non sostituisce** la definizione
canonica usata ovunque nel resto della dashboard.
"""

import pandas as pd


def identify_heatwaves_percentile(daily: pd.DataFrame, percentile: int = 90, min_duration: int = 3) -> dict:
    """
    Identifica le ondate di calore in una serie giornaliera di un singolo
    comune usando come soglia il percentile storico di temp_max.

    Args:
        daily: DataFrame con colonne 'date' (datetime) e 'temp_max', per un
            solo comune.
        percentile: percentile (0-100) di temp_max usato come soglia.
        min_duration: durata minima in giorni consecutivi per contare come
            ondata.

    Returns:
        dict con 'threshold' (soglia calcolata in °C) e 'events' (DataFrame
        con start_date, end_date, duration_days, max_temp per ogni ondata
        trovata).
    """
    daily = daily.sort_values('date').reset_index(drop=True)
    threshold = daily['temp_max'].quantile(percentile / 100)

    is_hot = daily['temp_max'] > threshold
    run_id = (is_hot != is_hot.shift()).cumsum()

    events = []
    for _, group in daily.groupby(run_id):
        if not is_hot.loc[group.index[0]]:
            continue
        if len(group) >= min_duration:
            events.append({
                'start_date': group['date'].iloc[0],
                'end_date': group['date'].iloc[-1],
                'duration_days': len(group),
                'max_temp': group['temp_max'].max(),
            })

    return {'threshold': threshold, 'events': pd.DataFrame(events)}


def identify_heatwaves_events(daily: pd.DataFrame, threshold: float = 35.0, min_duration: int = 3) -> pd.DataFrame:
    """
    Versione Python della definizione **canonica** (soglia fissa, non
    percentile) già implementata lato SQL in `identify_heatwaves()`
    (`sql/01_init_database.sql`) - usata per calcolare le ondate al volo su
    serie non presenti in `heatwave_events` (che è popolata solo dalla
    fonte Open-Meteo), tipicamente dati ARPA.

    Args:
        daily: DataFrame con colonne 'municipality_name', 'date', 'temp_max',
            'temp_mean' - una o più comuni insieme (non richiede ordinamento
            in ingresso).

    Returns:
        DataFrame con le stesse colonne di `get_heatwave_events()` (tranne
        province_name, da aggiungere con un merge a valle): municipality_name,
        start_date, end_date, duration_days, max_temp, mean_temp,
        intensity_index.
    """
    if daily.empty:
        return pd.DataFrame(columns=[
            'municipality_name', 'start_date', 'end_date', 'duration_days',
            'max_temp', 'mean_temp', 'intensity_index',
        ])

    events = []
    for name, group in daily.sort_values('date').groupby('municipality_name'):
        is_hot = group['temp_max'] > threshold
        run_id = (is_hot != is_hot.shift()).cumsum()
        for _, run in group.groupby(run_id):
            if not is_hot.loc[run.index[0]] or len(run) < min_duration:
                continue
            max_temp = run['temp_max'].max()
            events.append({
                'municipality_name': name,
                'start_date': run['date'].iloc[0],
                'end_date': run['date'].iloc[-1],
                'duration_days': len(run),
                'max_temp': max_temp,
                'mean_temp': run['temp_mean'].mean(),
                'intensity_index': (max_temp - threshold) * len(run),
            })
    return pd.DataFrame(events)

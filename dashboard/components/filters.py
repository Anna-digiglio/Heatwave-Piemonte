"""
filters.py - Filtri riutilizzabili, inline nella pagina che li usa davvero.

Non più una sidebar comune a tutte le pagine (rimossa il 2026-07-15 su
richiesta dell'utente: appariva ovunque anche dove non serviva a niente,
es. nella pagina Download Dati o nella Home). Ogni pagina richiama solo il
filtro di cui ha davvero bisogno, nel punto della pagina in cui lo usa.
Streamlit persiste automaticamente il valore di un widget tramite il suo
`key` per tutta la sessione, quindi non serve più gestire a mano
`st.session_state` come quando i filtri dovevano sopravvivere al cambio
pagina nella sidebar.
"""

import streamlit as st

from .queries import get_municipality_metadata, get_overview_stats


def render_year_range_filter(key: str) -> tuple:
    """
    Slider intervallo anni. `key` deve essere univoca per pagina.

    Min/max **dinamici** dalla data reale più vecchia/più recente in
    `temperature` (`get_overview_stats()`), non più una coppia fissa nel
    codice: un range hardcoded (`2000, 2025`) è esattamente il tipo di bug
    già trovato in `heatwave_stats.py` il 2026-07-17 (16 ondate del 2026
    scartate da un `reindex` fermo al 2025) — qui avrebbe reso impossibile
    perfino selezionare l'anno corrente una volta arrivati dati più
    recenti.
    """
    stats = get_overview_stats()
    year_min, year_max = stats['date_start'].year, stats['date_end'].year
    year_range = st.slider(
        "Intervallo anni",
        min_value=year_min,
        max_value=year_max,
        value=(year_min, year_max),
        key=key,
    )
    return year_range[0], year_range[1]


def render_province_filter(key: str) -> list:
    """
    Multiselect provincia. `key` deve essere univoca per pagina. Di default
    è **vuoto** (= tutti i comuni con dati, nessun filtro attivo): l'utente
    clicca e sceglie dal menu solo se vuole restringere a una o più
    province, senza dover scrivere/digitare nulla a mano. Un default con
    tutte le province già selezionate riempirebbe il riquadro di 8 tag fin
    dal primo sguardo, senza comunicare nulla di utile.
    """
    metadata = get_municipality_metadata()
    all_provinces = sorted(metadata['province_name'].unique())
    provinces = st.multiselect(
        "Filtra per provincia (opzionale)",
        options=all_provinces,
        default=[],
        key=key,
        placeholder="Tutte le province con dati",
        help=f"Lascia vuoto per includere tutti i {len(metadata)} comuni con dati; scegli una o più province per restringere.",
    )
    return provinces or all_provinces

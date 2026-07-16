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

from .queries import get_municipality_metadata

YEAR_MIN, YEAR_MAX = 2000, 2025


def render_year_range_filter(key: str) -> tuple:
    """Slider intervallo anni. `key` deve essere univoca per pagina."""
    year_range = st.slider(
        "Intervallo anni",
        min_value=YEAR_MIN,
        max_value=YEAR_MAX,
        value=(YEAR_MIN, YEAR_MAX),
        key=key,
    )
    return year_range[0], year_range[1]


def render_province_filter(key: str) -> list:
    """
    Multiselect provincia. `key` deve essere univoca per pagina. Ritorna la
    lista di province scelte, o tutte le province con dati se l'utente non
    ne seleziona nessuna (equivalente a "nessun filtro").
    """
    metadata = get_municipality_metadata()
    all_provinces = sorted(metadata['province_name'].unique())
    provinces = st.multiselect(
        "Provincia",
        options=all_provinces,
        default=all_provinces,
        key=key,
        help="Vuoto o tutte selezionate = nessun filtro.",
    )
    return provinces or all_provinces

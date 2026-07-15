"""
filters.py - Filtri globali condivisi tra tutte le pagine, nella sidebar.

Streamlit esegue ogni pagina come script indipendente, quindi i widget non
sono condivisi automaticamente: qui si usa `st.session_state` per far
persistere la scelta dell'utente quando naviga da una pagina all'altra
(i default della sidebar riflettono l'ultima selezione fatta, anche in
un'altra pagina).
"""

import streamlit as st

from .queries import get_municipality_metadata

YEAR_MIN, YEAR_MAX = 2000, 2025


def render_sidebar_filters() -> tuple:
    """
    Disegna la sidebar comune (intervallo anni + provincia) e ritorna
    (year_start, year_end, province_selezionate).

    `province_selezionate` è la lista di nomi provincia scelti, oppure
    l'intera lista di province con dati se l'utente non filtra nulla
    (equivalente a "tutte").
    """
    metadata = get_municipality_metadata()
    all_provinces = sorted(metadata['province_name'].unique())

    st.sidebar.header("🔎 Filtri")

    year_range = st.sidebar.slider(
        "Intervallo anni",
        min_value=YEAR_MIN,
        max_value=YEAR_MAX,
        value=st.session_state.get('year_range', (YEAR_MIN, YEAR_MAX)),
        key='year_range',
    )

    provinces = st.sidebar.multiselect(
        "Provincia",
        options=all_provinces,
        default=st.session_state.get('province_filter', all_provinces),
        key='province_filter',
        help="Filtra i comuni per provincia. Vuoto o tutte selezionate = nessun filtro.",
    )
    if not provinces:
        provinces = all_provinces

    st.sidebar.caption(
        "Filtri applicati a grafici e mappe di questa pagina (dove pertinente). "
        "Restano impostati anche cambiando pagina."
    )

    return year_range[0], year_range[1], provinces

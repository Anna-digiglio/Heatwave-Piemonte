"""
styling.py - CSS condiviso per un aspetto coerente in tutta la dashboard.

La palette/i colori di base vivono nel tema (`.streamlit/config.toml`, che
Streamlit applica automaticamente senza bisogno di CSS). Qui ci sono solo
le rifiniture che il tema da solo non copre.
"""

import streamlit as st

_CUSTOM_CSS = """
<style>
/* st.metric tronca con "..." qualunque valore più largo della colonna
   (successo con testi come "Nessun trend chiaro" o nomi di comune lunghi
   come "Verbano-Cusio-Ossola"). Qui il valore va a capo invece di
   sparire - i numeri restano su una riga (di solito corti), il testo più
   lungo si distribuisce su due righe leggibili. */
div[data-testid="stMetricValue"] {
    white-space: normal !important;
    overflow: visible !important;
    line-height: 1.25 !important;
    font-size: 1.35rem !important;
}

div[data-testid="stMetricLabel"] {
    opacity: 0.75;
}
</style>
"""


def inject_custom_css() -> None:
    """Da richiamare una volta per pagina, subito dopo st.set_page_config()."""
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)

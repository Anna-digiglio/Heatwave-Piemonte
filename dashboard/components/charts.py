"""
charts.py - Rifinitura condivisa per i grafici Plotly.

`st.plotly_chart(fig)` usa di default `theme="streamlit"` (verificato in
`streamlit/elements/plotly_chart.py` del pacchetto installato): Streamlit
applica già in automatico font/colori/griglie coerenti col tema chiaro o
scuro attivo. Per questo `apply_chart_theme` si limita a rendere lo sfondo
del grafico trasparente (così eredita il colore del container invece di
quello scelto da Plotly di default) e NON tocca font/colori del testo -
farlo qui li fisserebbe a un valore costante, rompendo l'adattamento
automatico chiaro/scuro che Streamlit fornisce già gratis.
"""

import plotly.graph_objects as go


def apply_chart_theme(fig: go.Figure) -> go.Figure:
    """Da richiamare su ogni figura, prima di `st.plotly_chart`."""
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    return fig

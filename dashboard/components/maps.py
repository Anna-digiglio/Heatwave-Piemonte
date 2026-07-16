"""
maps.py - Utility per le mappe Folium.
"""

import streamlit as st
from shapely import wkt
from shapely.geometry import mapping


def wkt_to_geojson(wkt_str: str) -> dict:
    """Converte una geometria WKT in un dict GeoJSON (richiesto da folium.GeoJson)."""
    return mapping(wkt.loads(wkt_str))


def render_gradient_legend(
    colormap, vmin: float, vmax: float, labels: list, unit: str, title: str,
    n_bins: int = 5, signed: bool = False,
) -> None:
    """
    Legenda testuale per una colormap continua (branca `LinearColormap`):
    divide [vmin, vmax] in `n_bins` fasce uguali e mostra, per ciascuna, lo
    swatch del colore realmente usato sulla mappa, il range numerico e
    un'etichetta di gravità/velocità (`labels`, una per fascia).

    Non è la legenda automatica di branca (`colormap.add_to(m)`, un gradiente
    continuo con soli min/max etichettati): qui ogni fascia ha un'etichetta
    testuale esplicita, più facile da leggere per chi non è abituato a leggere
    una colorbar continua.
    """
    step = (vmax - vmin) / n_bins if vmax > vmin else 0
    fmt = "{:+.2f}".format if signed else "{:.1f}".format

    rows = []
    for i in range(n_bins):
        low = vmin + i * step
        high = vmin + (i + 1) * step
        color = colormap((low + high) / 2)
        label = labels[i] if i < len(labels) else ""
        rows.append(
            '<div style="display:flex;align-items:center;gap:8px;margin:2px 0;">'
            f'<span style="display:inline-block;width:22px;height:14px;background:{color};'
            'border:1px solid rgba(0,0,0,0.3);border-radius:3px;flex-shrink:0;"></span>'
            f'<span style="font-size:0.85rem;">{fmt(low)} – {fmt(high)} {unit} — <b>{label}</b></span>'
            '</div>'
        )

    st.markdown(
        f'<div style="margin:0.25rem 0 0.75rem 0;"><b style="font-size:0.9rem;">{title}</b>'
        + ''.join(rows) + '</div>',
        unsafe_allow_html=True,
    )

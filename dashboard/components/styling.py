"""
styling.py - CSS e componenti HTML condivisi per l'identità visiva "calore"
della dashboard (hero, card di navigazione, striscia "numeri chiave",
tipografia, sidebar). Palette e font vivono come token in `constants.py`
(THEME_*, FONT_*), così questo file e `charts.py` condividono la stessa
fonte di verità invece di ripetere gli hex in due posti.

Il tema chiaro/scuro nativo di Streamlit (vedi `.streamlit/config.toml`)
resta gestito da Streamlit stesso e NON viene toccato qui: widget nativi
(bottoni, slider, dataframe, i st.metric delle altre pagine) continuano a
seguire il toggle chiaro/scuro dell'utente. Hero, card di navigazione e
striscia "numeri chiave" sono invece componenti nuovi, disegnati con
un'identità scura fissa (scelta deliberata, validata su un mockup con
l'utente il 2026-07-17 — sfondo poi schiarito da nero puro a grigio ardesia
su suo feedback): non provano a inseguire il toggle, sono un "pannello a
tema" come farebbe un badge di brand, non un layer che reagisce al tema.
"""

import streamlit as st

from .constants import (
    FONT_BODY, FONT_DISPLAY, FONT_MONO,
    THEME_BORDER, THEME_BORDER_STRONG, THEME_COLD, THEME_HOT, THEME_INK,
    THEME_MID, THEME_SURFACE, THEME_SURFACE_RAISED, THEME_TEXT,
    THEME_TEXT_FAINT, THEME_TEXT_MUTED,
)

_CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400..700&family=Manrope:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ---------- Tipografia globale --------------------------------------------
   Solo i font cambiano: i colori restano quelli del tema nativo (chiaro o
   scuro) scelto dall'utente, per non rompere il toggle di Streamlit. */
html, body, [data-testid="stAppViewContainer"] {{
    font-family: {FONT_BODY};
}}
h1, h2, h3,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 {{
    font-family: {FONT_DISPLAY} !important;
    font-weight: 600 !important;
}}

/* st.metric tronca con "..." qualunque valore più largo della colonna
   (successo con testi come "Nessun trend chiaro" o nomi di comune lunghi
   come "Verbano-Cusio-Ossola"). Qui il valore va a capo invece di sparire,
   e usa il monospace: le cifre si leggono come una misura, non come testo. */
div[data-testid="stMetricValue"] {{
    font-family: {FONT_MONO} !important;
    font-variant-numeric: tabular-nums;
    white-space: normal !important;
    overflow: visible !important;
    line-height: 1.25 !important;
    font-size: 1.35rem !important;
}}
div[data-testid="stMetricLabel"] {{
    opacity: 0.75;
}}

/* ---------- Respiro tra le sezioni: fade-in leggero al caricamento ------- */
[data-testid="stMainBlockContainer"] {{
    animation: hwFadeIn 0.45s ease both;
}}
@keyframes hwFadeIn {{
    from {{ opacity: 0; transform: translateY(6px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
@media (prefers-reduced-motion: reduce) {{
    [data-testid="stMainBlockContainer"] {{ animation: none; }}
}}

/* ---------- Sidebar: hover/attivo -----------------------------------------
   `data-testid` e `aria-current="page"` sono API stabili di Streamlit 1.58
   (verificate nel bundle installato) - non classi generate/hashate, che
   cambiano da una versione all'altra e romperebbero questo CSS. L'accento è
   una sovrapposizione translucida: funziona sia sulla sidebar chiara sia su
   quella scura del tema nativo, senza fissarne lo sfondo. */
[data-testid="stSidebarNavLink"] {{
    border-radius: 8px !important;
    transition: background 0.15s ease, transform 0.15s ease;
}}
[data-testid="stSidebarNavLink"]:hover {{
    background: rgba(52, 152, 219, 0.12) !important;
    transform: translateX(2px);
}}
[data-testid="stSidebarNavLink"][aria-current="page"] {{
    background: linear-gradient(90deg, rgba(231,76,60,0.18), rgba(243,156,18,0.06) 65%, transparent) !important;
    font-weight: 700 !important;
    box-shadow: inset 3px 0 0 0 {THEME_HOT};
}}

/* ================== Componenti custom (identità scura fissa) ============ */

.hw-hero {{
    position: relative;
    overflow: hidden;
    padding: 40px 32px 32px;
    margin: -1rem -1rem 1.5rem;
    border-radius: 16px;
    background: {THEME_INK};
    border: 1px solid {THEME_BORDER};
    isolation: isolate;
    color: {THEME_TEXT};
}}
.hw-hero::before {{
    content: "";
    position: absolute;
    inset: -30%;
    z-index: -1;
    background:
        radial-gradient(38% 55% at 10% 10%, rgba(52,152,219,0.30), transparent 70%),
        radial-gradient(40% 55% at 55% -10%, rgba(243,156,18,0.20), transparent 70%),
        radial-gradient(45% 60% at 95% 35%, rgba(231,76,60,0.26), transparent 70%);
    filter: blur(40px);
    animation: hwDrift 26s ease-in-out infinite alternate;
}}
@keyframes hwDrift {{
    0%   {{ transform: translate(0,0) scale(1); }}
    100% {{ transform: translate(-2%, 3%) scale(1.06); }}
}}
@media (prefers-reduced-motion: reduce) {{
    .hw-hero::before {{ animation: none; }}
}}
.hw-eyebrow {{
    font-family: {FONT_MONO};
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: {THEME_MID};
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 14px;
}}
.hw-eyebrow .hw-rule {{ width: 28px; height: 1px; background: linear-gradient(90deg, {THEME_COLD}, {THEME_HOT}); }}
.hw-hero h1 {{
    font-family: {FONT_DISPLAY} !important;
    font-weight: 600 !important;
    font-size: clamp(2rem, 3.6vw, 2.9rem) !important;
    line-height: 1.08 !important;
    margin: 0 0 12px !important;
    text-wrap: balance;
    max-width: 18ch;
    background: linear-gradient(100deg, #fff 30%, #ffe9c7 55%, #ffb199 78%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}}
.hw-lede {{
    max-width: 68ch;
    color: {THEME_TEXT_MUTED};
    font-size: 1rem;
    margin: 0 0 20px;
}}
.hw-lede b {{ color: {THEME_TEXT}; font-weight: 700; }}
.hw-hero-meta {{
    display: flex;
    gap: 24px;
    flex-wrap: wrap;
    font-family: {FONT_MONO};
    font-size: 0.78rem;
    color: {THEME_TEXT_FAINT};
}}
.hw-hero-meta b {{ color: {THEME_TEXT_MUTED}; font-weight: 600; }}

/* Card di navigazione: il wrapper è un vero `st.container(key=...)`, che
   Streamlit espone come classe `st-key-<key>` sull'elemento (vedi
   `render_nav_card_header`) - qui la trasformiamo in card senza toccare il
   markup interno di Streamlit. Il link cliccabile resta un `st.page_link`
   nativo dentro lo stesso container, per non rompere la navigazione SPA. */
[class*="st-key-navcard-"] {{
    position: relative;
    background: {THEME_SURFACE};
    border: 1px solid {THEME_BORDER};
    border-radius: 14px;
    padding: 18px 18px 6px;
    overflow: hidden;
    transition: transform 0.25s cubic-bezier(.2,.8,.2,1), box-shadow 0.25s ease, border-color 0.25s ease, background 0.25s ease;
}}
[class*="st-key-navcard-"]::before {{
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    opacity: 0.9;
}}
[class*="st-key-navcard-"]:hover {{
    transform: translateY(-4px);
    border-color: {THEME_BORDER_STRONG};
    background: {THEME_SURFACE_RAISED};
    box-shadow: 0 16px 32px -14px rgba(0,0,0,0.55);
}}
.st-key-navcard-temporale::before {{ background: linear-gradient(90deg, {THEME_COLD}, #6dc1f0); }}
.st-key-navcard-spaziale::before  {{ background: linear-gradient(90deg, {THEME_MID}, #f7c15c); }}
.st-key-navcard-ondate::before    {{ background: linear-gradient(90deg, {THEME_HOT}, #ff8064); }}

[class*="st-key-navcard-"] .hw-card-icon {{
    width: 38px; height: 38px;
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.15rem;
    background: {THEME_SURFACE_RAISED};
    border: 1px solid {THEME_BORDER};
    margin-bottom: 12px;
}}
[class*="st-key-navcard-"] h3 {{
    font-family: {FONT_DISPLAY} !important;
    font-size: 1.12rem !important;
    font-weight: 600 !important;
    color: {THEME_TEXT} !important;
    margin: 0 0 6px !important;
}}
[class*="st-key-navcard-"] p {{
    color: {THEME_TEXT_MUTED} !important;
    font-size: 0.86rem !important;
    margin: 0 0 12px !important;
}}
[class*="st-key-navcard-"] [data-testid="stPageLink"] {{
    font-family: {FONT_BODY};
    font-weight: 600;
    transition: transform 0.2s ease;
}}
[class*="st-key-navcard-"]:hover [data-testid="stPageLink"] {{
    transform: translateX(4px);
}}

/* Striscia "numeri chiave" */
.hw-stats {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1px;
    background: {THEME_BORDER};
    border: 1px solid {THEME_BORDER};
    border-radius: 14px;
    overflow: hidden;
    margin-bottom: 0.25rem;
}}
@media (max-width: 760px) {{ .hw-stats {{ grid-template-columns: repeat(2,1fr); }} }}
.hw-stat {{
    background: {THEME_SURFACE};
    padding: 18px 20px;
    transition: background 0.2s ease;
}}
.hw-stat:hover {{ background: {THEME_SURFACE_RAISED}; }}
.hw-stat-label {{
    font-size: 0.7rem;
    color: {THEME_TEXT_FAINT};
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 8px;
}}
.hw-stat-value {{
    font-family: {FONT_MONO};
    font-variant-numeric: tabular-nums;
    font-size: 1.55rem;
    font-weight: 600;
    color: {THEME_TEXT};
    display: flex;
    align-items: baseline;
    gap: 6px;
}}
.hw-stat-value .hw-unit {{ font-size: 0.8rem; color: {THEME_TEXT_MUTED}; font-weight: 500; }}
.hw-stat-spark {{ margin-top: 10px; display: block; }}
.hw-stat-spark path.hw-fill {{ opacity: 0.18; }}
</style>
"""


def inject_custom_css() -> None:
    """Da richiamare una volta per pagina, subito dopo st.set_page_config()."""
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)


def render_hero(eyebrow: str, title: str, lede: str, meta: list[tuple[str, str]]) -> None:
    """Hero termico: eyebrow + titolo in Fraunces + testo + micro-metadati."""
    meta_html = "".join(f'<span>{label} <b>{value}</b></span>' for label, value in meta)
    # Nessun a-capo/indentazione nell'HTML: CommonMark tratta una riga
    # indentata di 4+ spazi (anche dentro un blocco HTML) come blocco di
    # codice letterale, non HTML - un'indentazione "leggibile" qui
    # renderizzava il markup come testo invece che come pagina (bug reale,
    # vedi wiki/log.md 2026-07-17).
    st.markdown(
        f'<div class="hw-hero">'
        f'<div class="hw-eyebrow"><span class="hw-rule"></span>{eyebrow}</div>'
        f'<h1>{title}</h1>'
        f'<p class="hw-lede">{lede}</p>'
        f'<div class="hw-hero-meta">{meta_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_nav_card_header(icon: str, title: str, description: str) -> None:
    """
    Contenuto HTML di una card di navigazione (icona/titolo/descrizione).

    Va richiamato **dentro** un `st.container(key="navcard-<slug>")`, dove
    `<slug>` deve corrispondere a uno dei selettori CSS sopra
    (`temporale` / `spaziale` / `ondate`) per ottenere il bordo a gradiente
    giusto. Il link vero e proprio resta un `st.page_link` nativo, chiamato
    subito dopo (fuori da questa funzione) nello stesso container: un `<a>`
    costruito a mano qui romperebbe la navigazione SPA di Streamlit.
    """
    st.markdown(
        f'<div class="hw-card-icon">{icon}</div><h3>{title}</h3><p>{description}</p>',
        unsafe_allow_html=True,
    )


def render_stats_row(stats: list[dict]) -> None:
    """
    Striscia di tile "numeri chiave" con sparkline decorativa.

    Ogni elemento di `stats` è un dict con chiavi 'label', 'value', 'unit',
    'color', 'spark' (lista di y normalizzati 0-1). Lo sparkline è
    illustrativo — comunica il tono cromatico della metrica (fresco/caldo),
    non è calcolato dalla serie storica reale.
    """
    tiles = "".join(_stat_tile_html(**s) for s in stats)
    st.markdown(f'<div class="hw-stats">{tiles}</div>', unsafe_allow_html=True)


def _stat_tile_html(label: str, value: str, unit: str, color: str, spark: list) -> str:
    width, height = 160, 22
    n = len(spark)
    xs = [round(i * width / (n - 1), 1) for i in range(n)] if n > 1 else [0.0, float(width)]
    ys = [round(height - 2 - v * (height - 6), 1) for v in spark]
    points = list(zip(xs, ys))
    line_points = " ".join(f"{x},{y}" for x, y in points)
    fill_path = f"M0,{height} L" + " ".join(f"{x},{y}" for x, y in points) + f" L{width},{height} Z"
    # Single-line: vedi commento in render_hero sul bug indentazione = code block.
    return (
        f'<div class="hw-stat">'
        f'<div class="hw-stat-label">{label}</div>'
        f'<div class="hw-stat-value">{value}<span class="hw-unit">{unit}</span></div>'
        f'<svg class="hw-stat-spark" width="100%" height="{height}" viewBox="0 0 {width} {height}" preserveAspectRatio="none">'
        f'<path class="hw-fill" d="{fill_path}" fill="{color}"></path>'
        f'<polyline points="{line_points}" fill="none" stroke="{color}" stroke-width="1.5"></polyline>'
        f'</svg>'
        f'</div>'
    )

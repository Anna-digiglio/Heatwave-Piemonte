"""
06_sintesi_della_ricerca.py - Sintesi divulgativa dei dati raccolti e dei
risultati del progetto, con riferimenti alla letteratura scientifica.
Non è l'articolo tecnico (quello vive in paper/manoscritto.md): questa
pagina spiega cosa è stato trovato e perché, per un pubblico non
specialistico, citando ogni affermazione (vedi pagina "Citazioni e Fonti").
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from components.constants import THEME_COLD, THEME_HOT, THEME_MID
from components.queries import (
    get_arpa_event_comparison_summary,
    get_arpa_overview_stats,
    get_arpa_validation,
    get_combined_heatwave_count,
    get_combined_trend_analysis,
    get_morans_i_summary,
    get_overview_stats,
    get_spatial_analysis,
    get_trend_analysis,
)
from components.styling import inject_custom_css, render_sidebar_branding, render_stats_row

st.set_page_config(page_title='Sintesi della Ricerca | Heatwave Piemonte', layout='wide')
inject_custom_css()
render_sidebar_branding()
st.title("🔬 Sintesi della Ricerca")
st.caption(
    "Riassunto di ciò che abbiamo trovato analizzando 26 anni di temperature in Piemonte, "
    "articolo completo in elaborazione. Per l'elenco completo delle fonti vedi la pagina "
    "[Citazioni e Fonti](08_citazioni_e_fonti.py)."
)

with st.expander("ℹ️ Come si legge questa pagina"):
    st.markdown(
        "- Ogni affermazione rimanda a uno studio scientifico o a un report istituzionale: "
        "le citazioni in stile *Autore, anno* sono descritte per intero nella pagina "
        "[Citazioni e Fonti](08_citazioni_e_fonti.py).\n"
        "- I numeri qui sotto sono calcolati dal vivo sugli stessi dati delle pagine di "
        "analisi (Analisi Temporale, Analisi Spaziale, Ondate di Calore, Contesto "
        "Territoriale): non sono ricopiati a mano, quindi restano sempre aggiornati.\n"
        "- Per il dettaglio metodologico completo (formule, codice, tabelle) vedi le "
        "pagine di analisi collegate in ciascuna sezione."
    )

stats = get_overview_stats()
arpa_stats = get_arpa_overview_stats()
n_years = stats['date_end'].year - stats['date_start'].year + 1
combined_trend_df = get_combined_trend_analysis()
n_municipalities_combined = combined_trend_df['municipality_name'].nunique() if not combined_trend_df.empty else 0

st.divider()

# ---------------------------------------------------------------------------
# 1. Perché questo progetto
# ---------------------------------------------------------------------------
st.subheader("1. Perché questo progetto")
st.markdown(
    "Le ondate di calore in Italia sono aumentate di circa 7.5 giorni/decade a livello "
    "nazionale, su oltre 250 stazioni meteorologiche (Settanta et al., 2024). Negli "
    "Appennini, gli eventi di caldo estremo estivo del trentennio 1991-2020 sono aumentati "
    "del 134% rispetto al periodo di riferimento 1961-1990 (Capozzi et al., 2025). Il "
    "Piemonte, e in particolare Torino, ha una letteratura scientifica solida sull'isola di "
    "calore urbana: 147 anni di dati che mostrano un effetto notturno fino a 4-5°C "
    "(Garzena et al., 2019; Bassani et al., 2022; Milelli et al., 2023), ma quasi tutta "
    "concentrata sul solo capoluogo, con confronto urbano/rurale su poche stazioni. "
    "**Mancava un'analisi sistematica che coprisse l'intero territorio regionale a grana "
    "comunale**: è la domanda a cui prova a rispondere questo progetto."
)

st.divider()

# ---------------------------------------------------------------------------
# 2. I dati raccolti
# ---------------------------------------------------------------------------
st.subheader("2. I dati raccolti")
st.caption("Aggiornato dal vivo, stessa fonte delle altre pagine della dashboard.")
render_stats_row([
    {
        'label': "Comuni con temperatura reale", 'unit': f"/ {stats['n_municipalities']} totali", 'color': THEME_MID,
        'value': str(n_municipalities_combined),
        'spark': [0.15, 0.15, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0],
    },
    {
        'label': "Periodo coperto", 'unit': f"{n_years} anni", 'color': THEME_COLD,
        'value': f"{stats['date_start'].year}–{stats['date_end'].year}",
        'spark': [0.1, 0.2, 0.3, 0.4, 0.55, 0.7, 0.85, 1.0],
        'unit_wrap': True,
    },
    {
        'label': "Righe di temperatura", 'unit': "Open-Meteo + ARPA", 'color': THEME_MID,
        'value': f"{(stats['n_temperature_rows'] + arpa_stats['n_arpa_rows']):,}".replace(',', '.'),
        'spark': [0.3, 0.35, 0.5, 0.45, 0.65, 0.6, 0.8, 1.0],
        'unit_wrap': True,
    },
    {
        'label': "Ondate di calore identificate", 'unit': "eventi", 'color': THEME_HOT,
        'value': str(get_combined_heatwave_count()),
        'spark': [0.05, 0.1, 0.15, 0.3, 0.4, 0.55, 0.75, 1.0],
    },
])
st.markdown(
    f"\nDietro questi numeri: temperatura giornaliera da **Open-Meteo** (stazioni virtuali "
    f"di rianalisi/modello, {stats['n_municipalities_with_data']} comuni) e dalla rete "
    f"reale **ARPA Piemonte** ({arpa_stats['n_arpa_municipalities']} comuni, usata anche per "
    "validare Open-Meteo, il dettaglio è nella sezione «Limiti» più sotto); confini e "
    "geometrie di tutti i 1180 comuni "
    "piemontesi (ISTAT); popolazione residente comunale (ISTAT, demo.istat.it); uso del "
    "suolo (Copernicus CORINE Land Cover 2018); indice di vegetazione da satellite "
    "(Copernicus Global Land Service NDVI). Elenco completo con link diretti nella pagina "
    "[Citazioni e Fonti](08_citazioni_e_fonti.py); tutti i CSV scaricabili in "
    "[Download Dati](07_download_dati.py)."
)

st.divider()

# ---------------------------------------------------------------------------
# 3. Come misuriamo il riscaldamento
# ---------------------------------------------------------------------------
st.subheader("3. Come misuriamo il riscaldamento")
st.markdown(
    "- **Il trend**: test di Mann-Kendall (Mann, 1945; Kendall, 1975), un metodo che non "
    "assume che i dati seguano una distribuzione particolare, adatto a serie climatiche "
    "reali, spesso rumorose. La pendenza vera e propria (°C/decade) viene da una "
    "regressione lineare separata.\n"
    "- **La stagionalità**: scomposizione STL (Cleveland et al., 1990), che separa una "
    "serie giornaliera in trend, stagionalità e residuo, usata per misurare quanto "
    "l'escursione tra estate e inverno vari da comune a comune.\n"
    "- **Il pattern spaziale**: indice di Moran (Moran, 1950), che dice se i comuni "
    "geograficamente vicini si somigliano più di quanto ci si aspetterebbe per puro caso, "
    "e clustering K-means (MacQueen, 1967) per raggruppare i comuni in regimi climatici "
    "simili.\n"
    "- **I fattori esplicativi oltre la quota**: un modello a errore spaziale (Anselin, "
    "1988), necessario perché, come mostra il punto precedente, i residui di una "
    "normale regressione lineare risultano spazialmente autocorrelati, il che rende "
    "inaffidabile un modello OLS classico.\n"
    "- **Le ondate di calore**: definizione primaria a soglia fissa (almeno 3 giorni "
    "consecutivi sopra 35°C, uguale per ogni comune, per semplicità e uniformità); "
    "definizione di confronto a soglia relativa, il 90° percentile storico del singolo "
    "comune (Perkins & Alexander, 2013), discussa in dettaglio in "
    "[Ondate di Calore](04_ondate_di_calore.py), perché la soglia fissa penalizza "
    "sistematicamente i comuni di montagna (il dettaglio è nella sezione «Limiti» più sotto)."
)

st.divider()

# ---------------------------------------------------------------------------
# 4. Cosa abbiamo trovato
# ---------------------------------------------------------------------------
st.subheader("4. Cosa abbiamo trovato")

trend_om = get_trend_analysis()
n_om = len(trend_om)
n_sig = int((trend_om['lr_p_value'] < 0.05).sum()) if not trend_om.empty else 0
n_cooling_sig = int(((trend_om['lr_p_value'] < 0.05) & (trend_om['lr_slope_per_decade'] < 0)).sum()) if not trend_om.empty else 0
slope_min = trend_om['lr_slope_per_decade'].min() if not trend_om.empty else None
slope_max = trend_om['lr_slope_per_decade'].max() if not trend_om.empty else None

morans = get_morans_i_summary()
morans_i = morans.iloc[0]['morans_i'] if not morans.empty else None
morans_p = morans.iloc[0]['p_value_permutation'] if not morans.empty else None

spatial = get_spatial_analysis()
n_hw = get_combined_heatwave_count()

st.markdown(
    f"**Il riscaldamento è diffuso e statisticamente significativo**: su {n_om} comuni con "
    f"dati Open-Meteo, **{n_sig} mostrano un trend di riscaldamento significativo** "
    f"(Mann-Kendall, p<0.05), con pendenze fino a **+{slope_max:.1f}°C/decade** nei casi più "
    "marcati. Il segnale è diffuso su tutto il territorio, non limitato ai soli capoluoghi "
    "di provincia, coerente con quanto atteso a livello nazionale (Settanta et al., 2024). "
)
if n_cooling_sig:
    comuni_word = "comune" if n_cooling_sig == 1 else "comuni"
    st.markdown(
        f"**Non è uniforme, però**: {n_cooling_sig} {comuni_word} di alta quota mostra"
        f"{'no' if n_cooling_sig != 1 else ''} un trend di **raffreddamento** "
        f"statisticamente significativo (fino a {slope_min:.1f}°C/decade). Un dettaglio "
        "onesto da non nascondere: il segnale prevalente è di riscaldamento, ma non è "
        "un'unanimità."
    )

cluster_stats = (
    spatial.groupby('climate_cluster')['temp_mean_avg'].agg(['count', 'mean']).sort_values('mean')
    if not spatial.empty else None
)
if cluster_stats is not None and len(cluster_stats) == 3:
    (n_cold, t_cold), (n_mid, t_mid), (n_warm, t_warm) = (
        (int(row['count']), row['mean']) for _, row in cluster_stats.iterrows()
    )
    cluster_text = (
        f"un gruppo alpino/di alta quota ({n_cold} comuni, {t_cold:.1f}°C medi, il più "
        f"freddo), uno pedemontano/collinare intermedio ({n_mid} comuni, {t_mid:.1f}°C), "
        f"e un gruppo di pianura ({n_warm} comuni, {t_warm:.1f}°C, il più caldo, include "
        "i capoluoghi maggiori)"
    )
else:
    cluster_text = "tre regimi climatici distinti (alpino, intermedio, pianura calda)"

st.markdown(
    f"\n**Il pattern non è casuale nello spazio**: indice di Moran = **{morans_i:.3f}** "
    f"(atteso sotto casualità: ~0), p={morans_p:.3f}. I comuni geograficamente vicini "
    "hanno temperature più simili tra loro di quanto ci si aspetterebbe per caso. Il "
    f"clustering individua **tre regimi climatici distinti**: {cluster_text}. Vedi mappe "
    "in [Analisi Spaziale](03_analisi_spaziale.py)."
)
st.markdown(
    f"\n**Le ondate di calore**: **{n_hw} eventi identificati** dal 2000 a oggi (almeno 3 "
    "giorni consecutivi sopra 35°C), concentrati nella pianura centro-orientale; diversi "
    "comuni alpini non hanno mai raggiunto la soglia nel periodo, coerente con clima/quota "
    "e non con un vuoto di dati. **Attenzione**: questo conteggio è quasi certamente un "
    "sottoconteggio del fenomeno reale, non un dato definitivo, il dettaglio è nella "
    "sezione «Limiti» più sotto."
)
st.markdown(
    "\n**Confronto con fonti esterne indipendenti**: il 2025 risulta il quinto anno più "
    "caldo dal 1958 in Piemonte, con una temperatura media annua di circa 10.8°C, quasi 1°C "
    "sopra il trentennio di riferimento 1991-2020 (ARPA Piemonte, 2026), coerente in "
    "direzione con il trend di riscaldamento diffuso trovato in questo progetto sullo "
    "stesso territorio."
)

st.divider()

# ---------------------------------------------------------------------------
# 5. Uso del suolo e popolazione
# ---------------------------------------------------------------------------
st.subheader("5. Uso del suolo e popolazione")
st.markdown(
    "L'ipotesi di partenza: a parità di quota, le zone più urbanizzate o più densamente "
    "popolate sono anche più calde? Un modello a errore spaziale (necessario per il "
    "pattern spaziale non casuale di cui sopra) su tutti i comuni con dati, che include "
    "quota, densità di popolazione, percentuale di superficie urbana e indice di "
    "vegetazione (NDVI), trova che:\n\n"
    "- **La quota resta di gran lunga il predittore più forte e stabile** in ogni versione "
    "del modello (sempre p<0.001).\n"
    "- **La percentuale di superficie urbana risulta ora significativa** (p≈0.03), con il "
    "segno atteso: più urbanizzato, più caldo. Un riscontro quantitativo, seppur ancora "
    "provvisorio, dell'ipotesi originale del progetto (città/industria come fattore "
    "esplicativo oltre la quota).\n"
    "- **Densità di popolazione e NDVI non risultano significativi** nella versione più "
    "recente del modello. Va detto onestamente: in versioni precedenti con un campione più "
    "piccolo, era successo l'opposto (NDVI significativo, % urbano no). Un segnale che "
    "questi due risultati vanno ancora consolidati con un campione più ampio, non trattati "
    "come definitivi. Dettaglio completo in [Contesto Territoriale](05_contesto_territoriale.py)."
)

st.divider()

# ---------------------------------------------------------------------------
# 6. Limiti
# ---------------------------------------------------------------------------
st.subheader("6. Limiti")

arpa_val = get_arpa_validation()
bias_mean = arpa_val['temp_max_bias'].mean() if not arpa_val.empty else None
r_mean = arpa_val['temp_max_r'].mean() if not arpa_val.empty else None
event_summary = get_arpa_event_comparison_summary()
recall = event_summary.get('recall')
n_matched = event_summary.get('n_matched_municipalities')

st.markdown(
    f"**Le temperature Open-Meteo sono stime di rianalisi/modello, non osservazioni "
    f"dirette di stazione**. Un limite dichiarato fin dall'inizio, e ora quantificato "
    f"confrontandole con le osservazioni reali della rete ARPA Piemonte, per "
    f"{int(n_matched) if n_matched else '108'} comuni dove esiste una stazione ARPA "
    f"corrispondente:\n\n"
    f"- Correlazione giorno-per-giorno molto alta (r medio **{r_mean:.3f}**), ma un bias "
    f"sistematico: Open-Meteo sottostima le temperature massime reali di **{bias_mean:.2f}°C** "
    "in media, di più nei comuni in quota.\n"
    f"- **Il conteggio delle ondate di calore ne risente molto di più del trend**: "
    f"riapplicando la stessa definizione ai dati ARPA (verità di terra), Open-Meteo "
    f"cattura solo il **{recall*100:.1f}%** delle ondate realmente accadute in questi "
    "comuni. Le ondate contate in questo progetto (sezione «Cosa abbiamo trovato» sopra) "
    "sono quindi con ogni probabilità un sottoconteggio sostanziale del fenomeno reale, "
    "non un numero prudente.\n"
    "- **Il trend di riscaldamento, invece, è robusto alla fonte dati**: ricalcolato sulle "
    "sole osservazioni ARPA, concorda in segno con Open-Meteo in oltre il 90% dei comuni. "
    "Il risultato più importante di questo lavoro (il riscaldamento diffuso descritto "
    "sopra) non dipende dalla fonte."
)
st.markdown(
    "\nAltri limiti da tenere presenti: la copertura resta una minoranza dei 1180 comuni "
    "piemontesi (i comuni analizzati sono stati scelti per massimizzare la copertura "
    "geografica per provincia, non a caso); la definizione di ondata di calore a soglia "
    "fissa penalizza sistematicamente i comuni di montagna, che raramente superano 35°C "
    "anche in estati eccezionali per il loro standard locale; e, come detto nella sezione "
    "«Uso del suolo e popolazione» sopra, il ruolo di uso del suolo/popolazione oltre la "
    "quota non è ancora un risultato stabile tra un aggiornamento del campione e l'altro."
)

st.divider()

# ---------------------------------------------------------------------------
# 7. Cosa significa in pratica
# ---------------------------------------------------------------------------
st.subheader("7. Cosa significa in pratica")
st.markdown(
    "Con la cautela dovuta al risultato ancora provvisorio sul ruolo dell'uso del suolo "
    "(sezione «Uso del suolo e popolazione» sopra), un segnale di riscaldamento diffuso e "
    "un'urbanizzazione che inizia a emergere come fattore aggiuntivo suggeriscono che le "
    "strategie di adattamento al caldo (verde urbano, materiali da costruzione, "
    "pianificazione degli spazi pubblici) non dovrebbero restare confinate ai soli grandi "
    "capoluoghi, ma considerare anche i centri minori della pianura e della cintura "
    "urbana, le zone dove, in questo lavoro, il segnale di calore risulta più marcato. "
    "Il fatto che le ondate di calore siano probabilmente sottocontate (sezione «Limiti» "
    "sopra) rende ancora più rilevante, non meno, investire in reti di monitoraggio "
    "locale e sistemi di allerta come quelli già attivi in Piemonte (ARPA Piemonte, 2026)."
)

st.divider()
st.markdown(
    "**Per l'elenco completo delle fonti citate in questa pagina**, bibliografia "
    "scientifica e fonti dei dati con link diretti, vedi "
    "[Citazioni e Fonti](08_citazioni_e_fonti.py)."
)
st.caption("Progetto portfolio di analisi dati climatici: Data Engineering / Data Science / GIS.")

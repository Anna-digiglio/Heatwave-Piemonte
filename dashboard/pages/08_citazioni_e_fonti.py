"""
08_citazioni_e_fonti.py - Bibliografia scientifica citata nel progetto e
elenco delle fonti dati reali usate per costruire il dataset.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from components.styling import inject_custom_css, render_sidebar_branding

st.set_page_config(page_title='Citazioni e Fonti — Heatwave Piemonte', layout='wide')
inject_custom_css()
render_sidebar_branding()
st.title("📚 Citazioni e Fonti")
st.caption(
    "Da dove vengono i dati mostrati in questo sito, e quale letteratura scientifica "
    "è stata usata per definizioni, metodi e confronti."
)

with st.expander("ℹ️ Come si legge questa pagina"):
    st.markdown(
        "- **Fonti dati**: da dove arrivano davvero i numeri (temperature, confini "
        "comunali, popolazione, uso del suolo, vegetazione) — con link diretto a ciascuna "
        "fonte. Per il dettaglio tecnico di ogni fonte vedi anche la pagina "
        "[Download Dati](07_download_dati.py).\n"
        "- **Bibliografia scientifica**: gli studi usati per definire le ondate di calore, "
        "confrontare i risultati con la letteratura su Torino/Piemonte e impostare il "
        "confronto uso del suolo → temperatura. Alcune voci sono ancora titoli/riferimenti "
        "raccolti in fase di ricerca preliminare, non citazioni bibliografiche complete "
        "(DOI/anno/volume) — è segnalato esplicitamente dove manca, invece di inventare "
        "dettagli non verificati."
    )

st.divider()

# ---------------------------------------------------------------------------
# Fonti dati
# ---------------------------------------------------------------------------
st.subheader("Fonti dati")
st.caption("Le fonti effettivamente usate per i dati mostrati in questo sito — non l'elenco completo delle fonti implementate nel codice, alcune delle quali restano disattivate/sperimentali.")

DATA_SOURCES = [
    (
        "Open-Meteo — Historical Weather API",
        "Temperatura giornaliera (minima/media/massima) e precipitazione, 2000–oggi, "
        "per 234 comuni. Dati di rianalisi/modello (non osservazioni dirette di stazione) — "
        "validati contro le stazioni reali ARPA Piemonte, vedi pagina Analisi Temporale.",
        "https://open-meteo.com/en/docs/historical-weather-api",
    ),
    (
        "ARPA Piemonte — rete di monitoraggio meteo-idrografico",
        "Osservazioni giornaliere reali di temperatura da 218 stazioni meteorologiche "
        "attive, usate sia per estendere la copertura territoriale sia per validare le "
        "temperature Open-Meteo (bias e confronto a livello di evento).",
        "https://utility.arpa.piemonte.it/meteoidro/",
    ),
    (
        "ISTAT — Confini amministrativi generalizzati",
        "Geometrie e confini di tutti i 1180 comuni piemontesi, base di ogni mappa del sito.",
        "https://www.istat.it/storage/cartografia/confini_amministrativi/generalizzati/2026/Limiti01012026_g.zip",
    ),
    (
        "ISTAT — Popolazione residente (demo.istat.it)",
        "Popolazione residente per comune, base per il calcolo della densità demografica "
        "usata nella pagina Contesto Territoriale.",
        "https://demo.istat.it/",
    ),
    (
        "Copernicus — CORINE Land Cover 2018",
        "Uso del suolo (% urbano/agricolo/forestale-seminaturale/zone umide/acqua) per "
        "ciascuno dei 1180 comuni, dataset europeo Copernicus Land Monitoring Service.",
        "https://land.copernicus.eu/",
    ),
    (
        "Copernicus — Global Land Service NDVI 300m V3",
        "Indice di vegetazione da satellite (verde/densità della vegetazione) per ciascuno "
        "dei 1180 comuni, complementare al solo uso del suolo discreto di CORINE.",
        "https://land.copernicus.eu/",
    ),
]

for name, description, url in DATA_SOURCES:
    col_label, col_link = st.columns([3, 1])
    with col_label:
        st.write(f"**{name}**")
        st.caption(description)
    with col_link:
        st.link_button("Vai alla fonte →", url)
    st.divider()

# ---------------------------------------------------------------------------
# Bibliografia scientifica
# ---------------------------------------------------------------------------
st.subheader("Bibliografia scientifica")
st.info(
    "Bibliografia completata il 2026-07-19: ogni voce è stata verificata con l'API "
    "pubblica di Crossref (autori/rivista/volume/DOI), non lasciata a un titolo raccolto "
    "a memoria durante la ricerca preliminare del 16/7."
)

st.markdown("#### Definizione di ondate di calore e metriche")
st.markdown(
    "- Perkins, S.E. & Alexander, L.V. (2013). *On the Measurement of Heat Waves*. "
    "**Journal of Climate**, 26(13). — definizione a percentile storico, usata come "
    "confronto metodologico nella pagina Ondate di Calore.\n"
    "- Nairn, J. & Fawcett, R. (2014). *The Excess Heat Factor: A Metric for Heatwave "
    "Intensity and Its Use in Classifying Heatwave Severity*. **International Journal "
    "of Environmental Research and Public Health**, 12(1), 227-253. "
    "[DOI: 10.3390/ijerph120100227](https://doi.org/10.3390/ijerph120100227) — metrica "
    "alternativa all'indice di intensità usato nel progetto. *(coautore corretto il "
    "2026-07-19: non \"Fenwick\" come raccolto inizialmente, ma Fawcett — verificato via "
    "Crossref)*"
)

st.markdown("#### Isola di calore urbana a Torino e in Piemonte")
st.markdown(
    "- Garzena, D. et al. (2019). *Analysis of the long-time climate data series for "
    "Turin and assessment of the city's urban heat island*. **Weather** (Wiley/RMetS). "
    "— 147 anni di dati, confronto Torino/stazioni rurali.\n"
    "- Bassani, F., Garbero, V., Poggi, D., Ridolfi, L., von Hardenberg, J., Milelli, M. "
    "(2022). *An innovative approach to select urban-rural sites for Urban Heat Island "
    "analysis: the case of Turin (Italy)*. **Urban Climate**, 42, 101099. "
    "[DOI: 10.1016/j.uclim.2022.101099](https://doi.org/10.1016/j.uclim.2022.101099)\n"
    "- Milelli, M., Bassani, F., Garbero, V., Poggi, D., von Hardenberg, J., Ridolfi, L. "
    "(2023). *Characterization of the Urban Heat and Dry Island effects in the Turin "
    "metropolitan area*. **Urban Climate**, 47, 101397. "
    "[DOI: 10.1016/j.uclim.2022.101397](https://doi.org/10.1016/j.uclim.2022.101397) — "
    "20 anni di dati orari ARPA Piemonte.\n"
    "- Pauly, L., Canonico, M., Ferrero, E. (2024). *Numerical investigation of thermal "
    "patterns and local wind circulations to characterize Urban Heat Island during a "
    "heatwave in Turin*. **Urban Climate**, 54, 101847. "
    "[DOI: 10.1016/j.uclim.2024.101847](https://doi.org/10.1016/j.uclim.2024.101847) — "
    "simulazione WRF/MLUCM dell'ondata di calore di giugno 2019, pattern termici e "
    "circolazione locale (incluso l'effetto Foehn)."
)

st.markdown("#### Uso del suolo e temperatura")
st.markdown(
    "- Morabito, M., Crisci, A., Guerri, G., Messeri, A., Congedo, L., Munafò, M. "
    "(2021). *Surface urban heat islands in Italian metropolitan cities: Tree cover and "
    "impervious surface influences*. **Science of The Total Environment**, 751, 142334. "
    "[DOI: 10.1016/j.scitotenv.2020.142334](https://doi.org/10.1016/j.scitotenv.2020.142334) "
    "— quantifica l'effetto di copertura arborea e superficie impermeabile sulle isole "
    "di calore di superficie nelle città italiane, template metodologico per il "
    "confronto uso del suolo → temperatura di questo progetto.\n"
    "- De Razza, S., Zanetti, C., De Marchi, M., Pappalardo, S.E. (2024). *Mapping "
    "urban heatwaves and islands: the reverse effect of Salento's \"white cities\"*. "
    "**Frontiers in Earth Science**, 12. "
    "[DOI: 10.3389/feart.2024.1375827](https://doi.org/10.3389/feart.2024.1375827) — "
    "caso controintuitivo su fattori mitiganti, da dati satellitari Landsat-8."
)

st.markdown("#### Contesto climatico regionale e nazionale")
st.markdown(
    "- Settanta, G., Fraschetti, P., Lena, F., Perconti, W., Piervitali, E. (2024). "
    "*Recent tendencies of extreme heat events in Italy*. **Theoretical and Applied "
    "Climatology**, 155, 7335–7348. "
    "[DOI: 10.1007/s00704-024-05063-w](https://doi.org/10.1007/s00704-024-05063-w) — "
    "oltre 250 stazioni a terra, 1991-2020: il 77% mostra un aumento di oltre 3 giorni "
    "di ondate di calore per decade. Fonte diretta del dato di contesto citato "
    "nell'introduzione del paper (+7.5 giorni/decade). Testo integrale leggibile "
    "gratuitamente nel preprint su Research Square (stessi autori, pre-revisione tra "
    "pari): [10.21203/rs.3.rs-4004015/v1](https://www.researchsquare.com/article/rs-4004015/v1.pdf).\n"
    "- Capozzi, V., Di Bernardino, A., Budillon, G. (2025). *Changes in large-scale "
    "circulation behind the increase in extreme heat events in the Apennines (Italy)*. "
    "**Atmospheric Research**, 319, 108013. "
    "[DOI: 10.1016/j.atmosres.2025.108013](https://doi.org/10.1016/j.atmosres.2025.108013) "
    "— ondate di calore 1961-2022 negli Appennini e circolazione a grande scala "
    "associata. Open access (licenza CC BY), scaricato per intero in `paper/references/`. "
    "**Fonte esatta** del dato di contesto \"+134%\" (Appennini, eventi estremi estivi "
    "1991-2020 vs 1961-1990; +102% in primavera, +53% inverno, +27% autunno).\n"
    "- Petkov, B.H. (2015). *Temperature Variability over the Po Valley, Italy, "
    "according to Radiosounding Data*. **Advances in Meteorology**, 2015. "
    "[DOI: 10.1155/2015/383614](https://doi.org/10.1155/2015/383614) — rivista ad "
    "accesso aperto (Hindawi), scaricata per intero in `paper/references/`; anche su "
    "arXiv ([1410.8081](https://arxiv.org/abs/1410.8081))."
)

st.divider()

st.markdown("#### Confronto con report istituzionali (ISTAT, ARPA Piemonte, ISPRA/SNPA)")
st.caption(
    "Report ufficiali usati per confrontare i risultati del progetto con le stime "
    "istituzionali più recenti sullo stesso territorio o con la stessa metodologia. "
    "PDF completi disponibili in `paper/references/` (non tutti online in permanenza "
    "agli URL sotto, verificati il 2026-07-19)."
)
st.markdown(
    "- SNPA — *Il clima in Italia nel 2025*. Report Ambientali SNPA n. 48/2026, "
    "ISBN 978-88-448-0375-9 (2026-07-01). "
    "[Link](https://www.snpambiente.it/wp-content/uploads/2026/07/Rapporto-SNPA-clima-2025.pdf) "
    "— sintesi nazionale annuale coordinata da ISPRA con dati di tutte le ARPA regionali.\n"
    "- ARPA Piemonte — *Il clima in Piemonte — Anno 2025* (2026-02-18). "
    "[Link](https://www.arpa.piemonte.it/sites/default/files/media/2026-02/anno_2025_solare_0.pdf) "
    "— confronto diretto più rilevante: 2025 quinto anno più caldo dal 1958 in Piemonte "
    "(media annua ~10.8°C, +quasi 1°C sopra il trentennio 1991-2020).\n"
    "- ISTAT — *Misure statistiche per l'adattamento ai cambiamenti climatici* "
    "(Statistica Focus, METEOCLIMA, anno 2022, ottobre 2024). "
    "[Link](https://www.istat.it/wp-content/uploads/2024/10/Statistica-focus-METEOCLIMA_Anno-2022.pdf) "
    "— indice di ondata di calore a percentile per capoluogo di provincia, confrontabile "
    "in metodo (non in soglia) con la definizione usata in questo progetto.\n"
    "- ISPRA — *Qualità dell'ambiente urbano — Focus: Le città, la sfida dei cambiamenti "
    "climatici*. [Link](https://www.isprambiente.gov.it/files/pubblicazioni/statoambiente/FocussuLecittelasfidadeicambiamenticlimatici.pdf) "
    "— approfondimento sull'isola di calore urbana nelle città italiane."
)

st.divider()

st.markdown("#### Riferimenti metodologici")
st.caption("I metodi statistici/spaziali usati nel progetto, citati alla fonte originale.")
st.markdown(
    "- Mann, H.B. (1945). *Nonparametric Tests Against Trend*. **Econometrica**, 13, 245. "
    "[DOI: 10.2307/1907187](https://doi.org/10.2307/1907187) — test di trend non "
    "parametrico (Mann-Kendall).\n"
    "- Kendall, M.G. (1975). *Rank Correlation Methods*. Griffin, Londra. — "
    "formalizzazione del coefficiente usata insieme a Mann (1945).\n"
    "- Moran, P.A.P. (1950). *Notes on Continuous Stochastic Phenomena*. **Biometrika**, "
    "37, 17-23. [DOI: 10.1093/biomet/37.1-2.17](https://doi.org/10.1093/biomet/37.1-2.17) "
    "— indice di autocorrelazione spaziale (Moran's I).\n"
    "- Cleveland, R.B., Cleveland, W.S., McRae, J.E., Terpenning, I. (1990). *STL: A "
    "Seasonal-Trend Decomposition Procedure Based on Loess*. **Journal of Official "
    "Statistics**, 6(1), 3-73. — scomposizione stagionale usata nella pagina Analisi "
    "Temporale.\n"
    "- MacQueen, J. (1967). *Some Methods for Classification and Analysis of "
    "Multivariate Observations*. Proc. 5th Berkeley Symposium on Mathematical "
    "Statistics and Probability, 1, 281-297. — algoritmo K-means per il clustering "
    "climatico.\n"
    "- Anselin, L. (1988). *Spatial Econometrics: Methods and Models*. Kluwer Academic "
    "Publishers. — modello a errore spaziale."
)

st.divider()
st.caption(
    "Progetto portfolio di analisi dati climatici — Data Engineering / Data Science / GIS."
)

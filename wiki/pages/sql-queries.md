# Query SQL di analisi

**Sorgente**: `sql/02_common_queries.sql`

Catalogo delle query pronte all'uso, pensate per rispondere direttamente alle
[domande di ricerca](project-overview.md) del progetto.

| # | Query | Risponde a |
|---|---|---|
| 1 | Temperatura media/max/min annuale per provincia + conteggio giorni sopra soglia (30/35/40°C) | "Le giornate estreme sono aumentate nel tempo?" |
| 2 | Confronto decadi (2000-2009, 2010-2019, 2020-2026) con variazione % | "Quali province mostrano i maggiori incrementi?" |
| 3 | Ranking province per incremento (via CTE `yearly_temp`, base per regressione lineare) | "Quali province mostrano i maggiori incrementi?" |

Le query usano `EXTRACT(YEAR FROM date)` per raggruppare e `FILTER (WHERE ...)`
per i conteggi condizionali — pattern PostgreSQL idiomatico, più leggibile di
`SUM(CASE WHEN ...)`.

**Gap**: il file copre le prime 3 delle "10 query comuni" previste in
`docs/ROADMAP.md` (giorni oltre soglia già incluso nella query #1, statistiche
descrittive standalone, query di vulnerabilità territoriale/hotspot non
ancora scritte). Da completare in base alle esigenze di
[Mappe GIS](gis-maps.md) e [Dashboard](dashboard.md) quando verranno costruite.

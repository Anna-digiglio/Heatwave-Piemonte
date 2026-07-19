# 🌡️ Il riscaldamento del Piemonte: un'analisi spazio-temporale dei trend termici e delle ondate di calore

[![Python Version](https://img.shields.io/badge/Python-3.9+-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 📊 Descrizione del Progetto

**Heatwave Piemonte** è un progetto di Data Engineering e GIS che analizza l'evoluzione delle temperature e delle ondate di calore nei comuni e nelle province piemontesi dal 2000 ad oggi. 

Il progetto integra tecnologie moderne per la gestione, elaborazione e visualizzazione di dati climatici territoriali, fornendo insights su trend termici, vulnerabilità climatica e rischi ambientali.

### 🎯 Obiettivi Principali

1. **Trend Termico**: Verificare se le giornate con temperature estreme sono aumentate nel tempo
2. **Analisi Provinciale**: Identificare le province con maggiori incrementi di temperature
3. **Differenze Territoriali**: Quantificare le variazioni geografiche significative
4. **Vulnerabilità Climatica**: Identificare aree maggiormente esposte a ondate di calore

## 📈 Domande di Ricerca

- ❓ Le giornate con temperature estreme (>30°C, >35°C, >40°C) sono aumentate nel tempo?
- ❓ Quali province mostrano i maggiori incrementi di temperatura?
- ❓ Esistono pattern geografici e stagionali significativi?
- ❓ Quali sono i comuni con maggiore vulnerabilità alle ondate di calore?
- ❓ Come è evoluto il fenomeno delle "heatwaves" negli ultimi 25 anni?

## 🛠️ Stack Tecnologico

### Backend & Data Engineering
- **Python 3.9+** - Linguaggio principale
- **pandas, numpy** - Elaborazione dati
- **SQLAlchemy** - ORM per database
- **GeoPandas** - Analisi geospaziale

### Database
- **PostgreSQL 14+** - Data warehouse relazionale
- **PostGIS** - Estensione geospaziale
- **TimescaleDB** (opzionale) - Ottimizzazione serie temporali

### Geospatial & Mapping
- **QGIS** - Analisi e visualizzazione GIS
- **Folium** - Mappe interattive
- **Shapely** - Operazioni geometriche

### Visualizzazione & BI
- **Streamlit** - Dashboard interattiva
- **Plotly** - Grafici interattivi
- **Matplotlib/Seaborn** - Visualizzazioni statiche

### DevOps & Versionamento
- **Git/GitHub** - Version control
- **Docker** (opzionale) - Containerizzazione
- **GitHub Actions** (opzionale) - CI/CD

## 📁 Struttura del Progetto

```
heatwave-piemonte/
├── src/
│   ├── data_acquisition/       # Download e acquisizione dati
│   ├── data_processing/        # Cleaning e preprocessing
│   ├── database/               # Gestione database
│   ├── analysis/               # Analisi statistiche
│   ├── visualization/          # Grafici e heatmap
│   └── utils/                  # Funzioni di utilità
├── data/
│   ├── raw/                    # Dati grezzi scaricati
│   ├── processed/              # Dati elaborati
│   └── external/               # Dati di riferimento (province, comuni)
├── sql/                        # Query SQL e script DDL
├── qgis_projects/              # Progetti QGIS
├── dashboard/                  # Applicazione Streamlit
├── docs/                       # Documentazione
├── tests/                      # Test unitari
├── config.yaml                 # Configurazione centrale
├── requirements.txt            # Dipendenze Python
├── .env.example                # Template variabili ambiente
└── README.md                   # Questo file
```

## 🚀 Quickstart

### Prerequisiti
- Python 3.9+
- PostgreSQL 14+ con PostGIS
- QGIS 3.20+
- Git

### Installazione

1. **Clone il repository**
   ```bash
   git clone https://github.com/yourusername/heatwave-piemonte.git
   cd heatwave-piemonte
   ```

2. **Crea ambiente virtuale**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Installa dipendenze**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configura il database**
   ```bash
   cp .env.example .env
   # Modifica .env con le tue credenziali
   psql -U postgres -f sql/01_init_database.sql
   ```

5. **Scarica i dati**
   ```bash
   python src/data_acquisition/download_data.py
   ```

6. **Carica il database**
   ```bash
   python src/database/load_to_db.py
   ```

7. **Avvia il dashboard**
   ```bash
   streamlit run dashboard/app.py
   ```

## 📊 KPI Principali

| KPI | Descrizione |
|-----|-------------|
| **Temp. Media Annuale** | Temperatura media per anno e provincia |
| **Temp. Max Annuale** | Massima temperatura registrata |
| **Giorni >30°C** | Count giorni con T > 30°C |
| **Giorni >35°C** | Count giorni con T > 35°C |
| **Giorni >40°C** | Count giorni con T > 40°C |
| **Durata Ondate** | Lunghezza media heatwave |
| **Trend Decennale** | Variazione °C ogni 10 anni |
| **Anomalia Termica** | Differenza vs media climatica |

## 🗺️ Mappe GIS

- 🌡️ **Temperatura Media per Provincia** - Heatmap provinciale
- 🔥 **Hotspot Climatici** - Zone ad alta vulnerabilità
- 📈 **Evoluzione Temporale** - Animazione 2000-2026
- 🌊 **Heatwave Index** - Indice di intensità delle ondate
- 📍 **Distribuzione Comuni** - Analisi a livello comunale

## 📈 Dataset

Fonti dati pubbliche utilizzate (approccio intermedio):

- **Default (abilitate)**
   - **Open-Meteo API**: Dati meteorologici storici 2000-2026 (JSON)
      - Temperature medie, massime, minime
      - Precipitazioni giornaliere
      - Free, no API key required
   - **Copernicus ERA5**: Reanalysis giornaliero (NetCDF)
      - Temperatura superficiale, precipitazione, pressione
      - Usato per confronto/climatologia di riferimento

- **Opzionali (disabilitate di default)**
   - **ARPA Piemonte**: Stazioni e serie storiche locali (CSV)
      - Per validazione e calibrazione locale
   - **ISTAT**: Confini amministrativi e dati territoriali (GeoJSON/Shapefile)
      - Comuni, province, codici ISTAT
   - **OpenStreetMap**: Confini territoriali e geometrie aggiuntive (Nominatim/OSM)
      - Boundary data via Nominatim

Le sorgenti abilitate di default sono configurate in `config.yaml` e possono essere modificate tramite il flag `--sources` dello script di acquisizione.

## 🔍 Analisi Statistiche Implementate

✅ **Statistiche Descrittive** - Media, mediana, deviazione standard, quantili
✅ **Trend Analysis** - Regressione lineare e Mann-Kendall test
✅ **Correlazione Territoriale** - Autocorrelazione spaziale (Moran's I)
✅ **Serie Temporali** - STL decomposition, Moving Average
✅ **Analisi di Frequenza** - Distribuzioni empiriche
✅ **Clustering Geografico** - K-means su coordinate geospaziali

## 🎯 Roadmap (3 Settimane)

### Settimana 1: Setup & Data Acquisition
- [x] Struttura progetto
- [ ] Setup database PostgreSQL/PostGIS
- [ ] Download dati storici
- [ ] Validazione e cleaning dati

### Settimana 2: ETL & Analysis
- [ ] Pipeline ETL completa
- [ ] Caricamento database
- [ ] Query SQL ottimizzate
- [ ] Analisi statistiche

### Settimana 3: Visualization & Dashboard
- [ ] Mappe GIS in QGIS
- [ ] Dashboard Streamlit
- [ ] Documentazione finale
- [ ] Deploy su GitHub

## 📚 Documentazione

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Architettura tecnica dettagliata
- [DATABASE.md](docs/DATABASE.md) - Schema relazionale e modello dati
- [ETL.md](docs/ETL.md) - Pipeline di elaborazione dati
- [API.md](docs/API.md) - Documentazione funzioni Python
- [TUTORIAL.md](docs/TUTORIAL.md) - Guida passo-passo all'uso

## 💻 Utilizzo

### Download dati
```bash
python src/data_acquisition/download_data.py --year 2000:2026 --region all
```

### Elaborazione dati
```bash
python src/data_processing/clean_data.py --input data/raw --output data/processed
```

### Analisi
```bash
python src/analysis/statistical_analysis.py --input data/processed --output results/
```

### Dashboard
```bash
streamlit run dashboard/app.py
```

## 🧪 Testing

```bash
pytest tests/ --cov=src --cov-report=html
```

## 📋 Code Quality

```bash
# Formatting
black src/

# Linting
flake8 src/ --max-line-length=100

# Type checking
mypy src/
```

## 🤝 Contribuzioni

Le contribuzioni sono benvenute! Per modifiche significative:

1. Fork il repository
2. Crea un branch (`git checkout -b feature/AmazingFeature`)
3. Commit i cambiamenti (`git commit -m 'Add AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Apri una Pull Request

## 📝 Licenza

Questo progetto è licenziato sotto la MIT License - vedi il file [LICENSE](LICENSE) per i dettagli.

## 👤 Autore

**Nome Cognome**
- LinkedIn: [@tuoprofilo](https://linkedin.com/in/tuoprofilo)
- GitHub: [@tuoprofilo](https://github.com/tuoprofilo)
- Email: tuoemail@example.com

## 🙏 Ringraziamenti

- ARPA Piemonte per i dati meteorologici
- Open-Meteo per l'API meteorologica
- Copernicus per i dati ERA5
- La comunità Python per i librerie eccezionali

## 📞 Contatti & Support

Per domande o problemi, apri una [GitHub Issue](issues) o contattami direttamente.

---

**Ultimo aggiornamento**: Maggio 2026  
**Versione**: 1.0.0  
**Status**: 🚧 In Sviluppo

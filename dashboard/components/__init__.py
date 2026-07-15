"""
Rende importabile il pacchetto `src` (root del progetto) da dentro
`dashboard/`, che Streamlit esegue come script standalone (non come modulo
di pacchetto) — senza questo, `from src.utils...` fallirebbe con
ModuleNotFoundError sia in app.py sia nelle pagine sotto pages/.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

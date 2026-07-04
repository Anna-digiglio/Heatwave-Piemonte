"""
logger.py - Sistema di Logging Centralizzato

Modulo per gestire logging strutturato con loguru.

Features:
    - Logging a console e file
    - Livelli configurabili
    - Formato consistente
    - Rotazione file log
"""

import sys
from pathlib import Path
from loguru import logger as _logger
from .config import config


def setup_logger() -> None:
    """
    Configura il sistema di logging per l'applicazione.
    
    - Rimuove handler di default
    - Aggiunge handler console
    - Aggiunge handler file con rotazione
    """
    
    # Rimuovi handler di default
    _logger.remove()
    
    # Ottieni configurazione
    log_level = config.get('logging.level', 'INFO')
    log_format = config.get('logging.format', 
                           '{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}')
    log_file = config.get('logging.file', './logs/heatwave_piemonte.log')
    
    # Crea directory logs se non esiste
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Handler console
    if config.get('logging.console', True):
        _logger.add(
            sys.stdout,
            format=log_format,
            level=log_level,
            colorize=True
        )
    
    # Handler file con rotazione
    _logger.add(
        log_file,
        format=log_format,
        level=log_level,
        rotation="500 MB",  # Ruota ogni 500 MB
        retention="7 days",  # Mantieni 7 giorni
        compression="zip",  # Comprimi file vecchi
        encoding="utf-8"
    )
    
    _logger.info(f"Logger configurato - Livello: {log_level}")


# Funzione per ottenere logger specifico di modulo
def get_logger(name: str):
    """
    Ottiene logger per un modulo specifico.
    
    Args:
        name (str): Nome del modulo (solitamente __name__)
        
    Returns:
        Logger: Istanza logger configurata
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Messaggio")
    """
    return _logger.bind(name=name)


# Inizializza logger al caricamento del modulo
setup_logger()
logger = _logger

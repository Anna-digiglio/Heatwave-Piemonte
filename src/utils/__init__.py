"""
Heatwave Piemonte - Data Engineering & GIS Analysis

Package per analisi spazio-temporale delle ondate di calore in Piemonte.
"""

__version__ = "1.0.0"
__author__ = "Data Engineering Team"
__email__ = "your.email@example.com"

from .config import config
from .logger import logger, get_logger
from .database import db_manager

__all__ = ['config', 'logger', 'get_logger', 'db_manager']

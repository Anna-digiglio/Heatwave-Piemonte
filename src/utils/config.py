"""
config.py - Gestione Configurazione Centralizzata

Modulo per caricare e gestire la configurazione del progetto
attraverso il file config.yaml.

Utilità:
    - Caricamento YAML
    - Validazione configurazione
    - Accesso variabili d'ambiente
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any
from loguru import logger


class Config:
    """Gestore centralizzato della configurazione del progetto."""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        """Singleton pattern per istanza unica."""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Inizializza la configurazione."""
        if self._config is None:
            self._load_config()
    
    @staticmethod
    def _load_config() -> Dict[str, Any]:
        """
        Carica la configurazione dal file YAML.
        
        Returns:
            Dict[str, Any]: Dizionario configurazione
            
        Raises:
            FileNotFoundError: Se il file config.yaml non esiste
        """
        # Prefer project root config.yaml, fallback to src/config.yaml
        possible_paths = [
            Path(__file__).resolve().parents[2] / "config.yaml",  # project root
            Path(__file__).resolve().parents[1] / "config.yaml",  # src/config.yaml
        ]

        config_path = None
        for p in possible_paths:
            if p.exists():
                config_path = p
                break

        if config_path is None:
            logger.error(f"File configurazione non trovato in percorsi: {possible_paths}")
            raise FileNotFoundError(f"config.yaml non trovato in {possible_paths}")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                Config._config = yaml.safe_load(f)
            logger.info(f"Configurazione caricata da: {config_path}")
            return Config._config
        except yaml.YAMLError as e:
            logger.error(f"Errore parsing YAML: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Ottiene valore di configurazione con notazione punto.
        
        Args:
            key (str): Chiave di configurazione (es. 'database.host')
            default (Any): Valore default se non trovato
            
        Returns:
            Any: Valore configurazione
            
        Example:
            >>> config.get('database.host')
            'localhost'
        """
        if self._config is None:
            self._load_config()
        
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        # Sostituisci variabili d'ambiente
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]
            return os.getenv(env_var, value)
        
        return value
    
    def get_database_url(self) -> str:
        """
        Genera URL di connessione al database.
        
        Returns:
            str: SQLAlchemy database URL
        """
        host = self.get('database.host', 'localhost')
        port = self.get('database.port', 5432)
        user = self.get('database.user', os.getenv('DB_USER', 'postgres'))
        password = self.get('database.password', os.getenv('DB_PASSWORD', ''))
        database = self.get('database.database', 'heatwave_piemonte')
        
        if password:
            return f"postgresql://{user}:{password}@{host}:{port}/{database}"
        else:
            return f"postgresql://{user}@{host}:{port}/{database}"
    
    def get_data_paths(self) -> Dict[str, Path]:
        """
        Ottiene tutti i path dati come Path objects.
        
        Returns:
            Dict[str, Path]: Dizionario con tutti i path
        """
        base_path = Path(__file__).parent.parent
        
        paths = {}
        for key, relative_path in self.get('paths', {}).items():
            paths[key] = base_path / relative_path
        
        return paths
    
    def ensure_paths_exist(self) -> None:
        """Crea tutti i path necessari se non esistono."""
        paths = self.get_data_paths()
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Directory verificata/creata: {path}")


# Istanza globale di configurazione
config = Config()


if __name__ == "__main__":
    # Test della configurazione
    print("Database URL:", config.get_database_url())
    print("Percorsi dati:", config.get_data_paths())
    print("Temperature thresholds:", config.get('processing.temperature_thresholds'))

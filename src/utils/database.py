"""
database.py - Gestione Connessione Database

Modulo per gestire connessioni a PostgreSQL con connection pooling.

Features:
    - Connection pooling con SQLAlchemy
    - Gestione transazioni
    - Context manager per sessioni
    - Health check database
"""

from typing import Optional, Generator
from contextlib import contextmanager
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.exc import SQLAlchemyError

from .config import config
from .logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Gestore centralizzato per connessioni database."""
    
    def __init__(self, pool_size: int = 10, max_overflow: int = 20):
        """
        Inizializza il database manager.
        
        Args:
            pool_size (int): Dimensione pool connessioni
            max_overflow (int): Overflow massimo pool
        """
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self._engine = None
        self._session_factory = None
    
    @property
    def engine(self):
        """
        Ottiene engine SQLAlchemy (lazy initialization).
        
        Returns:
            Engine: SQLAlchemy engine
        """
        if self._engine is None:
            self._create_engine()
        return self._engine
    
    @property
    def session_factory(self):
        """Ottiene session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine)
        return self._session_factory
    
    def _create_engine(self) -> None:
        """Crea engine SQLAlchemy con configurazione ottimizzata."""
        db_url = config.get_database_url()
        
        logger.info(f"Creazione engine database: {db_url.split('@')[1] if '@' in db_url else db_url}")
        
        try:
            self._engine = create_engine(
                db_url,
                echo=config.get('database.echo', False),
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_pre_ping=True,  # Test connessioni prima di usarle
                pool_recycle=3600,  # Ricicla connessioni ogni ora
                connect_args={
                    'connect_timeout': 10,
                    'application_name': 'heatwave_piemonte'
                }
            )
            
            # Test connessione
            self.check_connection()
            logger.info("Engine database creato con successo")
            
        except SQLAlchemyError as e:
            logger.error(f"Errore creazione engine: {e}")
            raise
    
    def check_connection(self) -> bool:
        """
        Verifica la connessione al database.
        
        Returns:
            bool: True se connessione ok
            
        Raises:
            SQLAlchemyError: Se connessione fallisce
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                logger.info("Connessione database verificata")
                return True
        except SQLAlchemyError as e:
            logger.error(f"Errore connessione database: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager per sessioni database.
        
        Yields:
            Session: Sessione SQLAlchemy
            
        Example:
            >>> with db_manager.get_session() as session:
            >>>     result = session.query(Table).filter(...).all()
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Errore transazione: {e}")
            raise
        finally:
            session.close()
    
    def execute_query(self, query: str) -> list:
        """
        Esegue query raw SQL e ritorna risultati.
        
        Args:
            query (str): Query SQL
            
        Returns:
            list: Risultati query
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                return result.fetchall()
        except SQLAlchemyError as e:
            logger.error(f"Errore esecuzione query: {e}")
            raise
    
    def execute_update(self, query: str, params: Optional[dict] = None) -> int:
        """
        Esegue UPDATE/INSERT/DELETE.
        
        Args:
            query (str): Query SQL
            params (dict): Parametri query
            
        Returns:
            int: Numero righe modificate
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                conn.commit()
                return result.rowcount
        except SQLAlchemyError as e:
            logger.error(f"Errore update: {e}")
            raise
    
    def close(self) -> None:
        """Chiude engine e pool connessioni."""
        if self._engine:
            self._engine.dispose()
            logger.info("Engine database chiuso")
    
    def __enter__(self):
        """Context manager enter."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Istanza globale database manager
db_manager = DatabaseManager()


if __name__ == "__main__":
    # Test connessione
    try:
        db_manager.check_connection()
        print("✓ Connessione database OK")
        
        # Test query semplice
        result = db_manager.execute_query("SELECT COUNT(*) FROM provinces;")
        print(f"✓ Numero province: {result[0][0]}")
        
    except Exception as e:
        print(f"✗ Errore: {e}")

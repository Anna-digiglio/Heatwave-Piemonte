"""
test_config.py - Test unitari per src/utils/config.py

Include un test di regressione per il bug risolto il 2026-07-04: le
variabili d'ambiente (.env, non tracciato in git) devono avere precedenza
su config.yaml (tracciato in git, non deve contenere segreti reali).
"""

from src.utils.config import config


class TestGetDotNotation:
    def test_returns_nested_value(self):
        assert config.get('database.host') is not None

    def test_returns_default_for_missing_key(self):
        assert config.get('nonexistent.key', 'fallback') == 'fallback'

    def test_returns_default_for_missing_top_level_section(self):
        assert config.get('nonexistent_section.sub_key', 42) == 42


class TestGetDatabaseUrl:
    def test_env_vars_take_precedence_over_yaml(self, monkeypatch):
        """
        Regression: prima del fix del 2026-07-04, get_database_url() dava
        sempre precedenza al placeholder in config.yaml su DB_PASSWORD,
        rendendo .env inutile per la password del database.
        """
        monkeypatch.setenv('DB_HOST', 'testhost')
        monkeypatch.setenv('DB_PORT', '5555')
        monkeypatch.setenv('DB_USER', 'testuser')
        monkeypatch.setenv('DB_PASSWORD', 'testpass')
        monkeypatch.setenv('DB_NAME', 'testdb')

        url = config.get_database_url()

        assert url == 'postgresql://testuser:testpass@testhost:5555/testdb'

    def test_falls_back_to_yaml_password_without_env(self, monkeypatch):
        monkeypatch.delenv('DB_PASSWORD', raising=False)

        url = config.get_database_url()
        yaml_password = config.get('database.password')

        assert yaml_password in url

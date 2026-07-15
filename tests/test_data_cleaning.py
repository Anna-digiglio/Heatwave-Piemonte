"""
test_data_cleaning.py - Test unitari per DataCleaner (src/data_processing/clean_data.py)

Non richiede un database: DataCleaner lavora solo su DataFrame in memoria
(l'unico I/O è la creazione delle cartelle data/processed, config-driven).
"""

import pandas as pd
import pytest

from src.data_processing.clean_data import DataCleaner


@pytest.fixture
def cleaner():
    return DataCleaner()


def make_df(n=10, province='Torino'):
    """DataFrame sintetico con lo stesso schema di temperature_data.csv, tutto valido."""
    dates = pd.date_range('2020-01-01', periods=n)
    return pd.DataFrame({
        'date': dates,
        'temp_max': [20.0] * n,
        'temp_min': [10.0] * n,
        'temp_mean': [15.0] * n,
        'precipitation': [0.0] * n,
        'province': [province] * n,
        'data_source': ['OpenMeteo'] * n,
    })


class TestRemoveDuplicates:
    def test_drops_exact_duplicates_on_date_and_province(self, cleaner):
        df = make_df(3)
        df_with_dup = pd.concat([df, df.iloc[[0]]], ignore_index=True)
        result = cleaner.remove_duplicates(df_with_dup)
        assert len(result) == 3

    def test_keeps_rows_from_different_provinces_on_same_date(self, cleaner):
        df = pd.concat([make_df(2, 'Torino'), make_df(2, 'Asti')], ignore_index=True)
        result = cleaner.remove_duplicates(df)
        assert len(result) == 4


class TestHandleMissingValues:
    def test_interpolates_missing_temp_mean(self, cleaner):
        df = make_df(5)
        df.loc[2, 'temp_mean'] = None
        result = cleaner.handle_missing_values(df)
        assert not result['temp_mean'].isna().any()

    def test_fills_missing_precipitation_with_zero(self, cleaner):
        df = make_df(5)
        df.loc[1, 'precipitation'] = None
        result = cleaner.handle_missing_values(df)
        assert result.loc[1, 'precipitation'] == 0

    def test_drops_rows_with_missing_temp_max(self, cleaner):
        df = make_df(5)
        df.loc[2, 'temp_max'] = None
        result = cleaner.handle_missing_values(df)
        assert len(result) == 4

    def test_drops_rows_with_missing_temp_min(self, cleaner):
        df = make_df(5)
        df.loc[0, 'temp_min'] = None
        result = cleaner.handle_missing_values(df)
        assert len(result) == 4


class TestValidateTemperature:
    def test_flags_out_of_physical_range_as_bad(self, cleaner):
        df = make_df(3)
        df['quality_flag'] = 0
        df.loc[0, 'temp_max'] = 100.0  # ben oltre TEMP_MAX_VALID (60)
        result = cleaner.validate_temperature(df)
        assert result.loc[0, 'quality_flag'] == 2

    def test_flags_min_greater_than_max_as_suspect(self, cleaner):
        df = make_df(3)
        df['quality_flag'] = 0
        df.loc[0, 'temp_min'] = 25.0
        df.loc[0, 'temp_max'] = 20.0
        result = cleaner.validate_temperature(df)
        assert result.loc[0, 'quality_flag'] == 1

    def test_leaves_valid_rows_at_flag_zero(self, cleaner):
        df = make_df(5)
        df['quality_flag'] = 0
        result = cleaner.validate_temperature(df)
        assert (result['quality_flag'] == 0).all()


class TestDetectOutliers:
    def test_flags_extreme_value_relative_to_rest(self, cleaner):
        df = make_df(20)
        df['quality_flag'] = 0
        df.loc[0, 'temp_max'] = 45.0  # tutte le altre righe sono a 20.0
        result = cleaner.detect_outliers(df)
        assert result.loc[0, 'quality_flag'] == 1

    def test_does_not_flag_uniform_data(self, cleaner):
        df = make_df(20)
        df['quality_flag'] = 0
        result = cleaner.detect_outliers(df)
        assert (result['quality_flag'] == 0).all()


class TestApplyQualityFlags:
    def test_discards_only_bad_quality_rows(self, cleaner):
        df = make_df(3)
        df['quality_flag'] = [0, 1, 2]
        result = cleaner.apply_quality_flags(df)
        assert len(result) == 2
        assert 2 not in result['quality_flag'].values

    def test_initializes_missing_quality_flag_column_to_zero(self, cleaner):
        df = make_df(3)
        assert 'quality_flag' not in df.columns
        result = cleaner.apply_quality_flags(df)
        assert len(result) == 3


class TestCleanDataPipelineRegression:
    def test_valid_dataset_survives_full_pipeline_intact(self, cleaner, tmp_path):
        """
        Regression test per il bug trovato il 2026-07-15 in produzione:
        senza inizializzare esplicitamente quality_flag=0 per tutte le righe
        prima di validate_temperature/detect_outliers, pandas crea la
        colonna con NaN per le righe non flaggate come sospette, e
        apply_quality_flags le scarta tutte (NaN < 2 è False in pandas).
        Su 75.976 righe reali tutte valide sopravvivevano solo le 10
        esplicitamente flaggate. Con un dataset interamente valido, ci si
        aspetta che sopravviva per intero.
        """
        df = make_df(50)
        csv_path = tmp_path / 'input.csv'
        df.to_csv(csv_path, index=False)

        result = cleaner.clean_data(csv_path)

        assert len(result) == 50

    def test_bad_rows_are_dropped_good_rows_survive(self, cleaner, tmp_path):
        df = make_df(10)
        df.loc[0, 'temp_max'] = 999.0  # fuori range fisico -> quality_flag=2, va scartata
        csv_path = tmp_path / 'input.csv'
        df.to_csv(csv_path, index=False)

        result = cleaner.clean_data(csv_path)

        assert len(result) == 9

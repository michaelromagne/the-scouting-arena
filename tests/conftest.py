import pytest
import pandas as pd


@pytest.fixture()
def salzbourg_brest_events_with_xT():
    """Salzbourg Brest Champions League events dataframe."""
    return pd.read_parquet("xT_salzbourg_brest.parquet")

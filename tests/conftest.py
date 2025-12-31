import pandas as pd
import pytest


@pytest.fixture()
def salzbourg_brest_events_with_xt():
    """Salzbourg Brest Champions League events dataframe."""
    return pd.read_parquet("xT_salzbourg_brest.parquet")

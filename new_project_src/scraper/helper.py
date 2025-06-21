import pandas as pd
# for scraper


# for cleaner

def _strip_cols(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.str.strip()
    return df

def _parse_datetime(col: pd.Series) -> pd.Series:
    return pd.to_datetime(col, format="%m/%d/%Y %H:%M", errors="coerce")


# for inserter
from pandas.api.types import is_string_dtype
def get_unique_samples(df):
    result = {}

    for col in df.columns:
        if is_string_dtype(df[col]):
            uniq = (
                df[col]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            if len(uniq) <= 50:
                result[col] = uniq

    return result
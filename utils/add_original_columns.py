import numpy as np


def _add_original_columns(original_df, df_selected):
    for colname in original_df.columns:
        df_selected[colname] = np.asarray(original_df[colname])

    return df_selected

"""
Utility wrapper around tsfresh.
"""

import gc
import time

import numpy as np
import pandas as pd
from scipy.stats import pearsonr
import tsfresh
from tsfresh.utilities.dataframe_functions import roll_time_series

from .add_original_columns import _add_original_columns
from .print_time_taken import _print_time_taken


class TSFreshBuilder:
    """
    Scikit-learn-style feature builder based on TSFresh.

    Args:

        num_features: The (maximum) number of features to build.

        memory: How much back in time you want to go until the
                feature builder starts "forgetting" data.

        column_id: The name of the column containing the ids.

        time_stamp: The name of the column containing the time stamps.

        target: The name of the target column.
    """

    def __init__(self, num_features, memory, column_id, time_stamp, target):
        self.num_features = num_features
        self.memory = memory
        self.column_id = column_id
        self.time_stamp = time_stamp
        self.target = target

        self.selected_features = []

    def _extract_features(self, data_frame):
        df_rolled = roll_time_series(
            data_frame,
            column_id=self.column_id,
            column_sort=self.time_stamp,
            max_timeshift=self.memory,
        )

        extracted_minimal = tsfresh.extract_features(
            df_rolled,
            column_id=self.column_id,
            column_sort=self.time_stamp,
            default_fc_parameters=tsfresh.feature_extraction.MinimalFCParameters(),
        )

        extracted_index_based = tsfresh.extract_features(
            df_rolled,
            column_id=self.column_id,
            column_sort=self.time_stamp,
            default_fc_parameters=tsfresh.feature_extraction.settings.IndexBasedFCParameters(),
        )

        extracted_features = pd.concat(
            [extracted_minimal, extracted_index_based], axis=1
        )
        del extracted_minimal
        del extracted_index_based

        gc.collect()

        extracted_features[np.isnan(extracted_features)] = 0.0

        extracted_features[np.isinf(extracted_features)] = 0.0

        return extracted_features

    def _remove_target_column(self, data_frame):
        colnames = np.asarray(data_frame.columns)

        if self.target not in colnames:
            return data_frame

        colnames = colnames[colnames != self.target]

        return data_frame[colnames]

    def _select_features(self, data_frame, target):
        df_selected = tsfresh.select_features(data_frame, target)

        colnames = np.asarray(df_selected.columns)

        correlations = np.asarray(
            [np.abs(pearsonr(target, df_selected[col]))[0] for col in colnames]
        )

        # [::-1] is somewhat unintuitive syntax,
        # but it reverses the entire column.
        self.selected_features = colnames[np.argsort(correlations)][::-1][
            : self.num_features
        ]

        return df_selected[self.selected_features]

    def fit(self, data_frame):
        """
        Fits the features.
        """
        begin = time.time()

        target = np.asarray(data_frame[self.target])

        df_without_target = self._remove_target_column(data_frame)

        df_extracted = self._extract_features(df_without_target)

        df_selected = self._select_features(df_extracted, target)

        del df_extracted
        gc.collect()

        df_selected = _add_original_columns(data_frame, df_selected)

        end = time.time()

        _print_time_taken(begin, end)

        return df_selected

    def transform(self, data_frame):
        """
        Transforms the raw data into a set of features.
        """
        df_extracted = self._extract_features(data_frame)

        df_selected = df_extracted[self.selected_features]

        del df_extracted
        gc.collect()

        df_selected = _add_original_columns(data_frame, df_selected)

        return df_selected

"""
Wrapper around tsflex

"""

import datetime
import time
import warnings
from typing import Dict, List, Optional, Tuple, TypedDict, Union

import numpy as np
import pandas as pd  # type: ignore
from pandas.api.types import is_numeric_dtype  # type: ignore
from scipy.stats import pearsonr  # type: ignore
from tsflex.features import FeatureCollection, MultipleFeatureDescriptors
from tsflex.features.integrations import tsfel_feature_dict_wrapper

from .add_original_columns import _add_original_columns
from .print_time_taken import _print_time_taken
from .remove_target_column import _remove_target_column
from .tsfel_builder import TSFELAggs, TSFELBuilder, _flatten_aggs, _get_window_params

# ------------------------------------------------------------------


class TsflexBuilder:
    """
    Scikit-learn-style feature builder based on tsflex.

    Args:
        aggregations: The aggregations to use.

        num_features: The (maximum) number of features to build.

        horizon: The prediction horizon to use.

        memory: How much back in time you want to go until the
                feature builder starts "forgetting" data.

        time_stamp: The name of the column containing the time stamps.

        target: The name of the target column.
    """

    statistical_aggs: TSFELAggs = TSFELBuilder.statistical_aggs
    temporal_aggs: TSFELAggs = TSFELBuilder.temporal_aggs
    all_aggs: TSFELAggs = {**statistical_aggs, **temporal_aggs}

    def __init__(
        self,
        num_features: int,
        horizon: pd.Timedelta,
        memory: pd.Timedelta,
        time_stamp: str,
        target: str,
        aggregations: Optional[TSFELAggs] = None,
        allow_lagged_targets: bool = False,
    ) -> None:
        self.aggregations = aggregations or self.all_aggs
        self.num_features = num_features
        self.horizon = horizon
        self.memory = memory
        self.time_stamp = time_stamp
        self.target = target
        self.allow_lagged_targets = allow_lagged_targets

        self._runtime = None
        self.fitted = False
        self.max_depth = 2

        self.selected_features: List[int] = []

    def _extract_features(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        data_frame = data_frame.set_index(self.time_stamp)
        _, window_size, overlap = _get_window_params(
            data_frame, self.horizon, self.memory
        )

        fc = FeatureCollection(
            MultipleFeatureDescriptors(
                functions=tsfel_feature_dict_wrapper(self.aggregations),
                series_names=["traffic_volume"],
                windows=self.memory,
                strides=f"1{pd.infer_freq(data_frame.index)}",
            )
        )

        print(fc)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            df_extracted = fc.calculate([data_frame], return_df=True, n_jobs=1)

        df_extracted.set_index(data_frame.index[window_size:])
        for col in df_extracted:
            if is_numeric_dtype(df_extracted[col]):
                df_extracted[col][df_extracted[col].isna()] = 0
        return df_extracted

    def _select_features(
        self, data_frame: pd.DataFrame, target: Union[pd.Series, np.ndarray]
    ) -> pd.DataFrame:
        colnames = np.asarray(data_frame.columns)
        print("Selecting the best out of " + str(len(colnames)) + " features...")
        colnames = np.asarray(
            [
                col
                for col in colnames
                if is_numeric_dtype(data_frame[col])
                and np.var(np.asarray(data_frame[col])) > 0.0
            ]
        )
        correlations = np.asarray(
            [np.abs(pearsonr(target, data_frame[col]))[0] for col in colnames]
        )
        correlations[np.isnan(correlations) | np.isinf(correlations)] = 0.0

        self.selected_features = colnames[np.argsort(correlations)][::-1][
            : self.num_features
        ]
        return data_frame[self.selected_features]

    def fit(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Fits the DFS on the data frame and returns
        the features for the training set.
        """
        print("TSFEL: Trying features...")
        begin = time.time()
        target = np.asarray(data_frame[self.target])
        df_for_extraction = (
            data_frame
            if self.allow_lagged_targets
            else _remove_target_column(data_frame, self.target)
        )
        df_extracted = self._extract_features(df_for_extraction)
        cutoff = len(target) - len(df_extracted)
        df_selected = self._select_features(df_extracted, target[cutoff:])
        df_selected = _add_original_columns(data_frame[cutoff:], df_selected)
        end = time.time()
        _print_time_taken(begin, end)
        self.fitted = True
        self._runtime = datetime.timedelta(seconds=end - begin)
        return df_selected

    @property
    def runtime(self) -> Union[None, datetime.timedelta]:
        if self.fitted:
            return self._runtime

    def transform(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Fits the DFS on the data frame and returns
        the features for the training set.
        """
        df_for_extraction = (
            data_frame
            if self.allow_lagged_targets
            else _remove_target_column(data_frame, self.target)
        )
        df_extracted = self._extract_features(df_for_extraction)
        df_selected = df_extracted[self.selected_features]
        df_selected = _add_original_columns(data_frame, df_selected)
        return df_selected

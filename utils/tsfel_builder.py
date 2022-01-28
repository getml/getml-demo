"""
Wrapper around TSFEL
"""

import datetime
import time
import warnings
from typing import Dict, List, Optional, Tuple, TypedDict, Union

import numpy as np
import pandas as pd  # type: ignore
import tsfel
from pandas.api.types import is_numeric_dtype  # type: ignore
from scipy.stats import pearsonr  # type: ignore

from .add_original_columns import _add_original_columns
from .print_time_taken import _print_time_taken
from .remove_target_column import _remove_target_column


class TSFELAgg(TypedDict):
    """
    A typed dict holding meta data for a certain TSFEL aggregation.
    """

    complexity: str
    description: str
    function: str
    parameters: Union[str, Dict[str, Union[str, int]]]
    n_features: int
    use: str
    tag: Union[str, List[str]]


TSFELAggs = Dict[str, Dict[str, TSFELAgg]]

# ------------------------------------------------------------------


def _flatten_aggs(
    aggs: TSFELAggs, domains: Optional[List[str]] = None
) -> Dict[str, TSFELAgg]:
    domains = domains or list(aggs.keys())
    return {
        name: {**values, **{"domain": domain}}
        for domain, agg in aggs.items()
        for name, values in agg.items()
        if domain in domains
    }


# ------------------------------------------------------------------


# TODO: Complete? Check for additional params
def _infer_required_obs(aggs: TSFELAggs) -> int:
    try:
        n_coeff = int(_flatten_aggs(aggs)["LPCC"]["parameters"]["n_coeff"])
    except KeyError:
        n_coeff = 1

    try:
        d = int(_flatten_aggs(aggs)["ECDF"]["parameters"]["d"])
    except KeyError:
        d = 1

    return max(n_coeff, d)


# ------------------------------------------------------------------


def _get_window_params(
    data_frame: pd.DataFrame,
    horizon: pd.Timedelta,
    memory: pd.Timedelta,
) -> Tuple[float, float, float]:
    freq = pd.Timedelta(1, pd.infer_freq(data_frame.index))
    win_size = memory // freq
    lag = horizon // freq
    overlap = (win_size - lag) / win_size
    return lag, win_size, overlap


# ------------------------------------------------------------------


class TSFELBuilder:
    """
    Scikit-learn-style feature builder based on TSFEL.

    Args:
        aggregations: The aggregations to use.

        num_features: The (maximum) number of features to build.

        horizon: The prediction horizon to use.

        memory: How much back in time you want to go until the
                feature builder starts "forgetting" data.

        time_stamp: The name of the column containing the time stamps.

        target: The name of the target column.
    """

    statistical_aggs: TSFELAggs = tsfel.get_features_by_domain("statistical")
    temporal_aggs: TSFELAggs = tsfel.get_features_by_domain("temporal")
    # spectral_aggs: TSFELAggs = tsfel.get_features_by_domain("spectral")
    # all_aggs: TSFELAggs = tsfel.get_features_by_domain()
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
        lag, window_size, overlap = _get_window_params(
            data_frame, self.horizon, self.memory
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            df_extracted = tsfel.time_series_features_extractor(
                self.aggregations,
                data_frame,
                window_size=window_size,
                overlap=overlap,
                verbose=0,
            )
        df_extracted.set_index(data_frame.index[window_size - lag :])
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

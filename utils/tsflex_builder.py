"""
Wrapper around tsflex
"""

import datetime
import time
import warnings
from typing import Callable, List, Optional, Union, cast

import numpy as np
import pandas as pd  # type: ignore
from pandas.api.types import is_numeric_dtype  # type: ignore
from tsflex.features import FeatureCollection, MultipleFeatureDescriptors
from tsflex.features.integrations import (
    tsfel_feature_dict_wrapper,
    tsfresh_settings_wrapper,
)
from tsfresh.feature_extraction import EfficientFCParameters, MinimalFCParameters

from .print_time_taken import _print_time_taken
from .tsfel_builder import TSFELBuilder

# ------------------------------------------------------------------


class TsflexBuilder:
    """
    Scikit-learn-style feature builder based on tsflex.

    Args:
        num_features: The (maximum) number of features to build.

        horizon: The prediction horizon to use.

        memory: How much back in time you want to go until the
                feature builder starts "forgetting" data.

        column_id: The name of the column containing the ids.

        time_stamp: The name of the column containing the time stamps.

        target: The name of the target column.

        aggregations: The aggregations to use.

        allow_lagged_targets: Whether to build features based on lagged targets

        min_chunksize: The minimum size of chunks to aggregate over
    """

    tsfel_statistical_aggs: List[Callable] = tsfel_feature_dict_wrapper(
        TSFELBuilder.statistical_aggs
    )
    tsfel_temporal_aggs: List[Callable] = tsfel_feature_dict_wrapper(
        TSFELBuilder.temporal_aggs
    )
    tsfel_aggs: List[Callable] = [*tsfel_statistical_aggs, *tsfel_temporal_aggs]
    tsfresh_minimal_aggs: List[Callable] = tsfresh_settings_wrapper(
        MinimalFCParameters()
    )
    tsfresh_efficient_aggs: List[Callable] = tsfresh_settings_wrapper(
        EfficientFCParameters()
    )
    tsfresh_aggs: List[Callable] = [*tsfresh_minimal_aggs, *tsfresh_efficient_aggs]
    all_aggs: List[Callable] = [*tsfel_aggs, *tsfresh_aggs]

    def __init__(
        self,
        num_features: int,
        horizon: pd.Timedelta,
        memory: pd.Timedelta,
        column_id: str,
        time_stamp: str,
        target: str,
        aggregations: Optional[List[Callable]] = None,
        allow_lagged_targets: bool = False,
        min_chunksize: int = 0,
    ) -> None:
        self.num_features = num_features
        self.horizon = horizon
        self.memory = memory
        self.column_id = column_id
        self.time_stamp = time_stamp
        self.target = target
        self.aggregations = aggregations or self.tsfel_aggs
        self.allow_lagged_targets = allow_lagged_targets
        self.min_chunksize = min_chunksize

        self._runtime = None
        self.fitted = False

        self.selected_features: List[int] = []

    def _extract_features(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        fc = FeatureCollection(
            MultipleFeatureDescriptors(
                functions=self.aggregations,
                series_names=["traffic_volume"],
                windows=self.memory,
                strides=f"1{pd.infer_freq(data_frame.index)}",
            )
        )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            extraced = cast(
                pd.DataFrame, fc.calculate([data_frame], return_df=True, n_jobs=1)
            )

        for col in extraced:
            if is_numeric_dtype(extraced[col]):
                extraced[col][extraced[col].isna()] = 0

        return extraced

    def _select_features(
        self, data_frame: pd.DataFrame, target: Union[pd.Series, np.ndarray]
    ) -> pd.DataFrame:
        print(f"Selecting the best out of {data_frame.shape[1]} features...")

        data_frame = data_frame.loc[:, (data_frame != data_frame.iloc[0]).any()]
        correlations = data_frame.corrwith(pd.Series(target)).abs()
        correlations = correlations.replace([np.inf, np.nan], 0)
        correlations = correlations.sort_values(ascending=False)

        self.selected_features = correlations.index[: self.num_features].tolist()
        return data_frame[self.selected_features]

    def fit(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Fits the DFS on the data frame and returns
        the features for the training set.
        """
        print("tsflex: Trying features...")
        begin = time.time()
        data_frame = data_frame.set_index(self.time_stamp)
        grouped = data_frame.groupby(self.column_id)
        extracted = []
        other = []
        for _, group in grouped:
            to_extract = group if self.allow_lagged_targets else group.drop(self.target)
            extracted.append(self._extract_features(to_extract))
            other.append(group[self.min_chunksize :])
        extracted = pd.concat(extracted)
        other = pd.concat(other)
        selected = self._select_features(extracted, other[self.target])
        selected = pd.concat([selected, other], axis=1)

        end = time.time()
        _print_time_taken(begin, end)
        self.fitted = True
        self._runtime = datetime.timedelta(seconds=end - begin)
        return selected

    @property
    def runtime(self) -> Union[None, datetime.timedelta]:
        if self.fitted:
            return self._runtime

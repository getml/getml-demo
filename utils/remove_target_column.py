import numpy as np


def _remove_target_column(data_frame, target):
    colnames = np.asarray(data_frame.columns)
    if target not in colnames:
        return data_frame
    colnames = colnames[colnames != target]
    return data_frame[colnames]

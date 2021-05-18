import pathlib

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

files = pathlib.Path(".").glob("*.csv")

dfs = {}

for file in files:
    df = pd.read_csv(file, index_col=0)
    name = file.stem
    df.index = [[name] * df.shape[0], df.index]
    dfs[name] = df

comparisons = pd.concat(dfs.values())

colors = {
    "getML: FastProp": (0.25, 0.17, 0.51),
    "featuretools": (0.96, 0.60, 0.05),
    "tsfresh": (0.32, 0.71, 0.24),
}

ax = (
    comparisons.speedup_per_feature.unstack()
    .iloc[:, [1, 0, 2]]
    .plot.bar(color=colors.values())
)

plt.tight_layout()
plt.savefig("spf.png")


ax2 = (
    comparisons.features_per_second.unstack()
    .iloc[:, [1, 0, 2]]
    .plot.bar(color=colors.values())
)

plt.tight_layout()
plt.savefig("fps.png")

sc_data = comparisons.copy()[["features_per_second", "rsquared"]]
sc_data.rename(columns={"rsquared": "auc/rsquared"}, inplace=True)
sc_data["auc/rsquared"]["occupancy"] = comparisons["auc"]["occupancy"].values

col = [colors[tool] for tool in comparisons.index.get_level_values(1)]

ax3 = sc_data.plot.scatter(x="features_per_second", y="auc/rsquared", c=col)

# for i, dat in enumerate(sc_data.index.get_level_values(0)):
#     point = ax3.get_children()[0].get_offsets().data[i]
#     ax3.annotate(dat, (point[0] + 0.05, point[1]))

plt.tight_layout()
plt.savefig("auc-rsquared_fps.png")

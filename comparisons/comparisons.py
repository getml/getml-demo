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

# --------------------------------------------------------------------------

ax = (
    comparisons.speedup_per_feature.unstack()
    .iloc[:, [1, 0, 2]]
    .plot.bar(color=colors.values())
)

ax.set_ylabel("Normalized runtime/feature \n (getML=1)")
ax.set_title("Runtime per feature on different data sets (lower is better)")

plt.tight_layout()
plt.savefig("nrpf.png")

# --------------------------------------------------------------------------

fig, axes = plt.subplots(nrows=2)

ax2 = (
    comparisons.features_per_second.unstack()
    .iloc[:, [1, 0, 2]]
    .plot.bar(color=colors.values(), ax=axes[0])
)

# for container in ax2.containers:
#     ax2.bar_label(container, label_type="edge")
ax2.set_ylabel("Features created/second")
ax2.set_xticklabels([])
ax2.set_title("Features created per second (higher is better)")

sc_data = comparisons.copy()[["features_per_second", "rsquared"]]
sc_data.rename(columns={"rsquared": "auc/rsquared"}, inplace=True)
sc_data["auc/rsquared"]["occupancy"] = comparisons["auc"]["occupancy"].values

ax4 = (
    sc_data["auc/rsquared"]
    .unstack()
    .iloc[:, [1, 0, 2]]
    .plot.bar(color=colors.values(), ax=axes[1], legend=None)
)

ax4.set_ylabel("AUC/Rsquared")
ax4.set_title("Performance (higher is better)")

fig.tight_layout(pad=1)

plt.savefig("fps_performance.png")

# --------------------------------------------------------------------------

ax5 = (
    sc_data["auc/rsquared"].unstack().iloc[:, [1, 0, 2]].plot.bar(color=colors.values())
)

ax5.set_ylabel("AUC/Rsquared")
ax5.set_title("Performance (higher is better)")

fig.tight_layout()

plt.savefig("performance.png")

# --------------------------------------------------------------------------

col = [colors[tool] for tool in comparisons.index.get_level_values(1)]

ax3 = sc_data.plot.scatter(x="features_per_second", y="auc/rsquared", c=col)

# for i, dat in enumerate(sc_data.index.get_level_values(0)):
#     point = ax3.get_children()[0].get_offsets().data[i]
#     offset = (0.001, 0.01)
#     ax3.annotate(dat, (point[0] + offset[0], point[1] + offset[1]))

ax3.grid(True)

ax3.set_ylabel("AUC/Rsquared")
ax3.set_xlabel("Features/second")
ax3.set_title("Performance vs. speed")

plt.tight_layout()
plt.savefig("auc-rsquared_fps.png")

# --------------------------------------------------------------------------

plt.style.use("seaborn")

fig, axes = plt.subplots(nrows=2)

ax = (
    comparisons.speedup_per_feature.unstack()
    .iloc[:, [1, 0, 2]]
    .plot.bar(color=colors.values(), ax=axes[0])
)

ax.set_ylabel("Normalized runtime/feature \n (getML=1)")
ax.set_title("Runtime per feature on different data sets (lower is better)")
ax.set_xticklabels([])

sc_data = comparisons.copy()[["speedup_per_feature", "rsquared"]]
sc_data.rename(columns={"rsquared": "auc/rsquared"}, inplace=True)
sc_data["auc/rsquared"]["occupancy"] = comparisons["auc"]["occupancy"].values

ax4 = (
    sc_data["auc/rsquared"]
    .unstack()
    .iloc[:, [1, 0, 2]]
    .plot.bar(color=colors.values(), ax=axes[1], legend=None)
)

ax4.set_ylabel("AUC/Rsquared")
ax4.set_title("Predictive performance (higher is better)")

fig.tight_layout(pad=1)


plt.savefig("nrpf_performance.png")

# --------------------------------------------------------------------------

<p align="center" style="text-align: center;">
    <img width="400" style="width: 50% !important; max-width: 400px;" src="assets/getml_logo.png" />
</p>

<p align="center" style="text-align: center;">
    <i>getML combines feature learning with AutoML to build end-to-end prediction pipelines</i>
</p>

<p align="center" style="text-align: center;">
        <a href="https://binder.mybinder.ovh/v2/gh/getml/getml-demo/master?urlpath=lab" target="_blank" alt="mybinder.org">
        <!-- <a href="https://mybinder.org/v2/gh/getml/getml-demo/master?urlpath=lab" target="_blank" alt="mybinder.org"> -->
        <img src="https://mybinder.org/badge_logo.svg" /></a>
        <a href="https://go.getml.com/meetings/alexander-uhlig/call" target="_blank">
        <img src="https://img.shields.io/badge/schedule-a_meeting-blueviolet.svg" /></a>
        <a href="mailto:contact@getml.com" target="_blank">
        <img src="https://img.shields.io/badge/contact-us_by_mail-orange.svg" /></a>
</p>

<br>
<span style="display: block; border-bottom: 1px solid #eaecef;"></span>

## Examples

This demo contains various example projects to help you to get started
with relational learning and getML. They cover different aspects of the software, and can serve as documentation or
as blueprints for your own project.

Each project solves a typical data science problem in a specific domain. You
can either choose a project by domain or by the underlying machine learning
problem, e.g. binary classification on a time series or regression using a
relational data scheme involving many tables.

Available example projects are listed below.

|                                                       | Task           | Data                     | Size               | Domain         |
| ----------------------------------------------------- | -------------- | ------------------------ | ------------------ | -------------- |
| [Financial: Loan default prediction][loansnb]         | Classification | Relational               | 8 Tables, 60 MB    | Financial      |
| [Occupancy detection][occupancynb]                    | Classification | Multivariate time series | 1 Table, 32k rows  | Energy         |
| [Expenditure categorization][consumerexpendituresnb]  | Classification | Relational               | 3 Tables, 150 MB   | E-commerce     |
| [Disease lethality prediction][atherosclerosisnb]     | Classification | Relational               | 3 Tables, 22 MB    | Health         |
| [IMdb: Predicting actors' gender][imdbnb]             | Classification | Relational with text     | 7 Tables, 477.1 MB | Entertainment  |
| [MovieLens: Predicting users' gender][movielensnb]    | Classification | Relational               | 7 Tables, 20 MB    | Entertainment  |
| [CORA: Categorizing academic studies][coranb]         | Classification | Relational               | 3 Tables, 4.6 MB   | Academia       |
| [Order cancellation][onlineretailnb]                  | Classification | Relational               | 1 Table, 398k rows | E-commerce     |
| [Traffic volume prediction (I94)][interstate94nb]     | Regression     | Multivariate time series | 1 Table, 24k rows  | Transportation |
| [Air pollution prediction][airpollutionnb]            | Regression     | Multivariate time series | 1 Table, 41k rows  | Environment    |
| [Traffic volume prediction (LA)][dodgersnb]           | Regression     | Multivariate time series | 1 Table, 47k rows  | Transportation |
| [Predicting a force vector from sensor data][robotnb] | Regression     | Multivariate time series | 1 Table, 15k rows  | Robotics       |

## Benchmarks

If you are mainly interested in how getML performs compared to other approaches, you can refer to the following notebooks:

|                                                    | Benchmarks                                       | Results                                  |
| -------------------------------------------------- | ------------------------------------------------ | ---------------------------------------- |
| [Occupancy detection][occupancynb]                 | Academic literature: Neural networks             | AUC (getML 99.8%, next best 99.6%)       |
| [IMdb: Predicting actors' gender][imdbnb]          | Academic literature: RDN, Wordification, RPT     | AUC (getML 92.87%, next best 86%)        |
| [MovieLens: Predicting users' gender][movielensnb] | Academic literature: PRM, MBN                    | Accuracy (getML 81.6%, next best 69%)    |
| [CORA: Categorizing academic studies][coranb]      | Academic literature: RelF, LBP, EPRN, PRN, ACORA | Accuracy (getML 89.9%, next best 85.7%)  |
| [Traffic volume prediction (I94)][interstate94nb]  | Prophet (fbprophet)                              | R-squared (getML 98.4%, prophet 83.3%)   |
| [Traffic volume prediction (LA)][dodgersnb]        | Prophet (fbprophet), tsfresh                     | R-squared (getML 76%, next best 67%)     |
| [Air pollution prediction][airpollutionnb]         | featuretools, tsfresh                            | R-squared (getML 62.3%, next best 50.4%) |

In particular, we have benchmarked getML's _FastProp_ (short for fast propositionalization) against other implementations of the propositionalization algorithm.

<p align="center" style="text-align: center;">
    <img src="proposiltionalization/comparisons/nrpf_performance.png" />
</p>

As we can see, _FastProp_ is true to its name: It achieves similar or slightly better performance than _featuretools_ or _tsfresh_, but generates features between 11x to 65x faster than these implementations.

If you want to reproduce these results, please refer to the following notebooks:

|                                      | Results                                                 |
| ------------------------------------ | ------------------------------------------------------- |
| [Air pollution][airpollutionnb_prop] | ~23x faster than featuretools, ~11x faster than tsfresh |
| [Dodgers][dodgersnb_prop]            | ~18x faster than featuretools, ~31x faster than tsfresh |
| [Interstate94][interstate94nb_prop]  | ~35x faster than featuretools                           |
| [Occupancy][occupancynb_prop]        | ~75x faster than featuretools, ~51x faster than tsfresh |
| [Robot][robotnb_prop]                | ~65x faster than featuretools, ~22x faster than tsfresh |

These results are very hardware-dependent and may be different on your machine. However, we have no doubt that you will find that getML's _FastProp_ is significantly faster than _featuretools_ and _tsfresh_ while consuming considerably less memory.

Some benchmarks are also featured on the [Relational Dataset Repository](https://relational.fit.cvut.cz/):

|                                                    | Official page                                                 |
| -------------------------------------------------- | ------------------------------------------------------------- |
| [CORA: Categorizing academic studies][coranb]      | [CORA](https://relational.fit.cvut.cz/dataset/CORA)           |
| [Financial: Loan default prediction][loansnb]      | [Financial](https://relational.fit.cvut.cz/dataset/Financial) |
| [IMdb: Predicting actors' gender][imdbnb]          | [IMDb](https://relational.fit.cvut.cz/dataset/IMDb)           |
| [MovieLens: Predicting users' gender][movielensnb] | [MovieLens](https://relational.fit.cvut.cz/dataset/MovieLens) |

[loansnb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/loans.ipynb
[occupancynb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/occupancy.ipynb
[consumerexpendituresnb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/consumer_expenditures.ipynb
[atherosclerosisnb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/atherosclerosis.ipynb
[imdbnb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/imdb.ipynb
[movielensnb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/movie_lens.ipynb
[coranb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/cora.ipynb
[onlineretailnb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/online_retail.ipynb
[interstate94nb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/interstate94.ipynb
[airpollutionnb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/air_pollution.ipynb
[dodgersnb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/dodgers.ipynb
[robotnb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/robot.ipynb
[airpollutionnb_prop]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/propositonilzation/air_pollution_prop.ipynb
[dodgersnb_prop]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/propositonilzation/dodgers_prop.ipynbpynb
[interstate94nb_prop]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/propositonilzation/interstate94_prop.ipynb
[occupancynb_prop]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/propositonilzation/occupancy_prop.ipynb
[robotnb_prop]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/propositonilzation/robot_prop.ipynb

## Try it live

You can try these notebooks on a live server. No installation or registration required. Start your own getML live demo [here](https://demo.getml.com/v2/gh/getml/getml-demo/master?urlpath=lab).

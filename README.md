<p align="center" style="text-align: center;">
    <img width="400" style="width: 50% !important; max-width: 400px;" src="assets/getml_logo.png" />
</p>

<p align="center" style="text-align: center;">
    <i>getML combines Feature Learning with AutoML to build end-to-end prediction pipelines</i>
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

# Examples

This demo contains various example projects to help you to get started
with relational learning and getML. They cover different aspects of the software, and can serve as documentation or
as blueprints for your own project.

Each project solves a typical data science problem in a specific domain. You
can either choose a project by domain or by the underlying machine learning
problem, e.g. binary classification on a time series or regression using a
relational data scheme involving many tables.

Available example projects are listed below.


|                                                           | Task           | Data                     | Size               | Domain         |
| --------------------------------------------------------- | -------------- | ------------------------ | ------------------ | -------------- |
| [Loan default prediction][loansnb]                        | Classification | Relational               | 8 Tables, 60 MB    | Financial      |
| [Occupancy detection](occupancy.ipynb)                    | Classification | Multivariate time series | 1 Table, 32k rows  | Energy         |
| [Expenditure categorization](consumer_expenditures.ipynb) | Classification | Relational               | 3 Tables, 150 MB   | E-commerce     |
| [Disease lethality prediction](atherosclerosis.ipynb)     | Classification | Relational               | 3 Tables, 22 MB    | Health         |
| [IMdb: Predicting actors' gender](imdb.ipynb)             | Classification | Relational with text     | 7 Tables, 477.1 MB | Entertainment  |
| [CORA: Categorizing academic studies](cora.ipynb)         | Classification | Relational               | 3 Tables, 4.6 MB   | Academia       |
| [Order cancellation](online_retail.ipynb)                 | Classification | Relational               | 1 Table, 398k rows | E-commerce     |
| [Traffic volume prediction](interstate94.ipynb)           | Regression     | Multivariate time series | 1 Table, 24k rows  | Transportation |
| [Air pollution prediction](air_pollution.ipynb)           | Regression     | Multivariate time series | 1 Table, 41k rows  | Environment    |
| [Traffic volume prediction](dodgers.ipynb)                | Regression     | Multivariate time series | 1 Table, 47k rows  | Transportation |
| [Predicting a force vector from sensor data](robot.ipynb) | Regression     | Multivariate time series | 1 Table, 15k rows  | Robotics       |

[loansnb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/loans.ipynb

# Benchmarks

If you are mainly interested in how getML performs compared to other approaches, you can refer to the following notebooks:

|                                                   | Benchmarks                                       | Results                                 |
| ------------------------------------------------- | ------------------------------------------------ | --------------------------------------- |
| [Occupancy detection](occupancy.ipynb)            | Academic literature: Neural networks             | AUC (getML 99.8%, next best 99.6%)      |
| [IMdb: Predicting actors' gender](imdb.ipynb)     | Academic literature: RDN, Wordification, RPT     | AUC (getML 92.87%, next best 86%)        |
| [CORA: Categorizing academic studies](cora.ipynb) | Academic literature: RelF, LBP, EPRN, PRN, ACORA | Accuracy (getML 89.9%, next best 85.7%) |
| [Traffic volume prediction](interstate94.ipynb)   | Prophet (fbprophet)                              | R-squared (getML 98.4%, prophet 83.3%)  |
| [Traffic volume prediction](dodgers.ipynb)        | Prophet (fbprophet), tsfresh                     | R-squared (getML 76%, next best 67%)    |
| [Air pollution prediction](air_pollution.ipynb)   | featuretools, tsfresh                            | R-squared (getML 62.3%, next best 50.4%)  |



#### getML on mybinder.org

The live demo is made possible by [mybinder.org](https://mybinder.readthedocs.io/en/latest/about.html). It is a public and free-to-use deployment of the BinderHub platform that is a part of Project Jupyter. Start your own getML live demo [here](https://mybinder.org/v2/gh/getml/getml-demo/master?urlpath=lab).

You can also launch the live demo of getML on a specific cluster in the mybinder universe. Available binder clusters are
[OVH](https://binder.mybinder.ovh/v2/gh/getml/getml-demo/master?urlpath=lab),
[GKE](https://gke.mybinder.org/v2/gh/getml/getml-demo/master?urlpath=lab) and
[GESIS](https://notebooks.gesis.org/binder/v2/gh/getml/getml-demo/master?urlpath=lab).

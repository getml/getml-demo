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

## Examples

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
| [Financial: Loan default prediction][loansnb]             | Classification | Relational               | 8 Tables, 60 MB    | Financial      |
| [Occupancy detection][occupancynb]                        | Classification | Multivariate time series | 1 Table, 32k rows  | Energy         |
| [Expenditure categorization][consumerexpendituresnb]      | Classification | Relational               | 3 Tables, 150 MB   | E-commerce     |
| [Disease lethality prediction][atherosclerosisnb]         | Classification | Relational               | 3 Tables, 22 MB    | Health         |
| [IMdb: Predicting actors' gender][imdbnb]                 | Classification | Relational with text     | 7 Tables, 477.1 MB | Entertainment  |
| [CORA: Categorizing academic studies][coranb]             | Classification | Relational               | 3 Tables, 4.6 MB   | Academia       |
| [Order cancellation][onlineretailnb]                      | Classification | Relational               | 1 Table, 398k rows | E-commerce     |
| [Traffic volume prediction][interstate94nb]               | Regression     | Multivariate time series | 1 Table, 24k rows  | Transportation |
| [Air pollution prediction][airpollutionnb]                | Regression     | Multivariate time series | 1 Table, 41k rows  | Environment    |
| [Traffic volume prediction][dodgersnb]                    | Regression     | Multivariate time series | 1 Table, 47k rows  | Transportation |
| [Predicting a force vector from sensor data][robotnb]     | Regression     | Multivariate time series | 1 Table, 15k rows  | Robotics       |

## Benchmarks

If you are mainly interested in how getML performs compared to other approaches, you can refer to the following notebooks:

|                                                   | Benchmarks                                       | Results                                 |
| ------------------------------------------------- | ------------------------------------------------ | --------------------------------------- |
| [Occupancy detection][occupancynb]                | Academic literature: Neural networks             | AUC (getML 99.8%, next best 99.6%)      |
| [IMdb: Predicting actors' gender][imdbnb]         | Academic literature: RDN, Wordification, RPT     | AUC (getML 92.87%, next best 86%)        |
| [CORA: Categorizing academic studies][coranb]     | Academic literature: RelF, LBP, EPRN, PRN, ACORA | Accuracy (getML 89.9%, next best 85.7%) |
| [Traffic volume prediction][interstate94nb]       | Prophet (fbprophet)                              | R-squared (getML 98.4%, prophet 83.3%)  |
| [Traffic volume prediction][dodgersnb]            | Prophet (fbprophet), tsfresh                     | R-squared (getML 76%, next best 67%)    |
| [Air pollution prediction][airpollutionnb]        | featuretools, tsfresh                            | R-squared (getML 62.3%, next best 50.4%)  |

Some benchmarks are also featured on the [Relational Dataset Repository](https://relational.fit.cvut.cz/):

|                                                   | Official page                                                 | 
| ------------------------------------------------- | ------------------------------------------------------------- |
| [CORA: Categorizing academic studies][coranb]     | [CORA](https://relational.fit.cvut.cz/dataset/CORA)           | 
| [Financial: Loan default prediction][loansnb]     | [Financial](https://relational.fit.cvut.cz/dataset/Financial) | 
| [IMdb: Predicting actors' gender][imdbnb]         | [IMDb](https://relational.fit.cvut.cz/dataset/IMDb)           | 

[loansnb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/loans.ipynb
[occupancynb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/occupancy.ipynb
[consumerexpendituresnb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/consumer_expenditures.ipynb
[atherosclerosisnb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/atherosclerosis.ipynb
[imdbnb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/imdb.ipynb
[coranb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/cora.ipynb
[onlineretailnb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/online_retail.ipynb
[interstate94nb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/interstate94.ipynb
[airpollutionnb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/air_pollution.ipynb
[dodgersnb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/dodgers.ipynb
[robotnb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/robot.ipynb

## Try it live

You can try these notebooks on a live server. No installation or registration required. Start your own getML live demo [here](https://demo.getml.com/v2/gh/getml/getml-demo/master?urlpath=lab).


<img src="assets/getml_logo.png" 
     width="35%" 
     align=right
     alt="getML logo"
     style="margin-top: 1.5rem;">

# Welcome to the getML live-demo

**This is a live session from which you can run example notebooks showing how to use getML.**

To get started with getML start with [this](loans.ipynb) notebook. It is a jupyter notebook on loan default prediction, which is reduced to the essential.

# Many more examples

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
| [MovieLens: Predicting users' gender][movielensnb]        | Classification | Relational               | 7 Tables, 20 MB    | Entertainment  |
| [CORA: Categorizing academic studies][coranb]             | Classification | Relational               | 3 Tables, 4.6 MB   | Academia       |
| [Order cancellation][onlineretailnb]                      | Classification | Relational               | 1 Table, 398k rows | E-commerce     |
| [Traffic volume prediction (I94)][interstate94nb]         | Regression     | Multivariate time series | 1 Table, 24k rows  | Transportation |
| [Air pollution prediction][airpollutionnb]                | Regression     | Multivariate time series | 1 Table, 41k rows  | Environment    |
| [Traffic volume prediction (LA)][dodgersnb]               | Regression     | Multivariate time series | 1 Table, 47k rows  | Transportation |
| [Predicting a force vector from sensor data][robotnb]     | Regression     | Multivariate time series | 1 Table, 15k rows  | Robotics       |


# Benchmarks

If you are mainly interested in how getML performs compared to other approaches, you can refer to the following notebooks:

|                                                   | Benchmarks                                       | Results                                 |
| ------------------------------------------------- | ------------------------------------------------ | --------------------------------------- |
| [Occupancy detection][occupancynb]                | Academic literature: Neural networks             | AUC (getML 99.8%, next best 99.6%)      |
| [IMdb: Predicting actors' gender][imdbnb]         | Academic literature: RDN, Wordification, RPT     | AUC (getML 92.87%, next best 86%)       |
| [MovieLens: Predicting users' gender][movielensnb]| Academic literature: PRM, MBN                    | Accuracy (getML 81.6%, next best 69%)   |
| [CORA: Categorizing academic studies][coranb]     | Academic literature: RelF, LBP, EPRN, PRN, ACORA | Accuracy (getML 89.9%, next best 85.7%) |
| [Traffic volume prediction (I94)][interstate94nb] | Prophet (fbprophet)                              | R-squared (getML 98.4%, prophet 83.3%)  |
| [Traffic volume prediction (LA)][dodgersnb]       | Prophet (fbprophet), tsfresh                     | R-squared (getML 76%, next best 67%)    |
| [Air pollution prediction][airpollutionnb]        | featuretools, tsfresh                            | R-squared (getML 62.3%, next best 50.4%)  |

Some benchmarks are also featured on the [Relational Dataset Repository](https://relational.fit.cvut.cz/):

|                                                     | Official page                                                 | 
| --------------------------------------------------- | ------------------------------------------------------------- |
| [CORA: Categorizing academic studies][coranb]       | [CORA](https://relational.fit.cvut.cz/dataset/CORA)           | 
| [Financial: Loan default prediction][loansnb]       | [Financial](https://relational.fit.cvut.cz/dataset/Financial) | 
| [IMdb: Predicting actors' gender][imdbnb]           | [IMDb](https://relational.fit.cvut.cz/dataset/IMDb)           | 
| [MovieLens: Predicting users' gender][movielensnb]  | [MovieLens](https://relational.fit.cvut.cz/dataset/MovieLens) | 

[loansnb]: loans.ipynb
[occupancynb]: occupancy.ipynb
[consumerexpendituresnb]: consumer_expenditures.ipynb
[atherosclerosisnb]: atherosclerosis.ipynb
[imdbnb]: https://nbviewer.getml.com/github/getml/getml-demo/blob/master/imdb.ipynb 
[movielensnb]: movie_lens.ipynb
[coranb]: cora.ipynb
[onlineretailnb]: online_retail.ipynb
[interstate94nb]: interstate94.ipynb
[airpollutionnb]: air_pollution.ipynb
[dodgersnb]: dodgers.ipynb
[robotnb]: robot.ipynb



# Get in contact

If you have any question schedule a [call with Alex](https://go.getml.com/meetings/alexander-uhlig/getml-demo), the co-founder of getML, or write us an [email](team@getml.com). Do you prefer a guided demo held by us? Just contact us to make an appointment.

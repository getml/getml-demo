<img src="assets/getml_logo.png" 
     width="35%" 
     align=right
     alt="getML logo"
     style="margin-top: 1.5rem;">

# Welcome to the getML live-demo

**This is a live session from which you can run example notebooks showing how to use getML.**

To get started with getML start with [this](loans_demo.ipynb) notebook. It is a jupyter notebook on loan default prediction, which is reduced to the essential.


# Many more examples

This demo contains various examples projects to help you to get started
with relational learning and getML. They cover different aspects of the software, and can serve as documentation or
as blueprints for your own project.

Each project solves a typical data science problem in a specific domain. You
can either choose a project by domain or by the underlying machine learning
problem, e.g. binary classification on a time series or regression using a
relational data scheme involving many tables.

Avaliable examples projects are listed below.

|                                                                | Task           | Data                     | Size               | Domain         |
| -------------------------------------------------------------- | -------------- | ------------------------ | ------------------ | -------------- |
| [Loan default prediction](loans_demo.ipynb)                    | Classification | Relational               | 8 Tables, 60 MB    | Financial      |
| [Occupancy detection](occupancy_demo.ipynb)                    | Classification | Multivariate time series | 1 Table, 32k rows  | Energy         |
| [Expenditure categorization](consumer_expenditures_demo.ipynb) | Classification | Relational               | 3 Tables, 150 MB   | E-commerce     |
| [Disease lethality prediction](atherosclerosis_demo.ipynb)     | Classification | Relational               | 3 Tables, 22 MB    | Health         |
| [IMdb] (imdb_demo.ipynb)                                       | Classification | Relational               | 7 Tables, 477.1 MB | Entertainment  |
| [CORA] (cora_demo.ipynb)                                       | Classification | Relational               | 3 Tables, 4.6 MB   | Academia       |
| [Order cancellation](online_retail_demo.ipynb)                 | Classification | Relational               | 1 Table, 398k rows | E-commerce     |
| [Traffic volume prediction](interstate94_demo.ipynb)           | Regression     | Multivariate time series | 1 Table, 24k rows  | Transportation |
| [Air pollution prediction](air_pollution_demo.ipynb)           | Regression     | Multivariate time series | 1 Table, 41k rows  | Environment    |
| [Traffic volume prediction](dodgers_demo.ipynb)                | Regression     | Multivariate time series | 1 Table, 47k rows  | Transportation |
| [Predicting a force vector from sensor data](robot-demo.ipynb) | Regression     | Multivariate time series | 1 Table, 15k rows  | Robotics       |

# Benchmarks

If you are mainly interested in how getML performs compared to other approaches, you can refer to the following notebooks:

|                                                                | Benchmarks                                        | Results                                 |
| -------------------------------------------------------------- | ------------------------------------------------- |---------------------------------------- |
| [Occupancy detection](occupancy_demo.ipynb)                    | Academic literature: Neural networks              | AUC (getML 99.8%, next best 99.6%)      | 
| [IMdb] (imdb_demo.ipynb)                                       | Academic literature: RDN, Wordification, RPT      | AUC (getML 92.5%, next best 86%)        |
| [Loan default prediction](loans_demo.ipynb)                    | Academic literature: ...                          | AUC (getML 94.3%, next best 88%)        |
| [CORA] (cora_demo.ipynb)                                       | Academic literature: RelF, LBP, EPRN, PRN, ACORA  | Accuracy (getML 89.3%, next best 85.7%) |
| [Traffic volume prediction](interstate94_demo.ipynb)           | Prophet (fbprophet)                               | R-squared (getML 98.4%, prophet 83.3%)  |
| [Traffic volume prediction](dodgers_demo.ipynb)                | Prophet (fbprophet), tsfresh                      | R-squared (getML 76%, next best 67%)    |
| [Air pollution prediction](air_pollution_demo.ipynb)           | tsfresh                                           | R-squared (getML 60.9%, tsfresh 48.7%)  |

# Get in contact

If you have any question schedule a [call with Alex](https://go.getml.com/meetings/alexander-uhlig/getml-demo), the co-founder of getML, or write us an [email](team@getml.com). Do you prefer a guided demo held by us? Just contact us to make an appointment.


# Getting started

This is the most basic example project and contains a thorough explanation of
the foundations of getML: Relational Learning. Its is ideally suited for
beginners who are new to working with relational business data. A very simple
target variable is generated on an artificial data set. The purpose if the
analysis is to demonstrate how getML Multirel algorithm is able to find the SQL
defintion of the target variable autonomously.

## Introduction

Automated machine learning (AutoML) has attracted a great deal of attention in
recent years. The goal is to simplify the application of traditional machine
learning methods to real world business problems by automating key steps of a
data science project, such as feature extraction, model selection, and
hyperparameter optimization. With AutoML, data scientists are able to develop
and compare dozens of models, gain insights, generate predictions, and solve
more business problems in less time.

While it is often claimed that AutoML covers the complete workflow of a data
science project - from the raw data set to the deployable machine learning
models - current solutions have one major drawback: They cannot handle real
world business data. This data typically comes in the form relational data. The
relevant information is scattered over a multitude of tables that are related
via so-called join keys. In order to start an AutoML pipeline, a flat feature
table has to be created from the raw relational data by hand. This step is
called feature engineering and is a tedious and error-prone process that
accounts for up to 90% of the time in a data science project.

![](../assets/getting_started/getting_started_pic1.png)

getML adds automated feature learning on relational data and time series to
AutoML. The getML algorithms, Multirel and Relboost, find the right
aggregations and subconditions needed to construct meaningful features from the
raw relational data. This is done by performing a sophisticated,
gradient-boosting-based heuristic. In doing so, getML brings the vision of
end-to-end automation of machine learning within reach for the first time. Note
that getML also includes automated model deployment via a HTTP endpoint or
database connectors. This topic is covered in other material.

All functionality of getML is implemented in the so-called getML engine. It is
written in C++ to achieve the highest performance and efficiency possible and
is responsible for all the heavy lifting. The getML Python API acts as a bridge
to communicate with engine. In addition, the getML monitor provides a Go-based
graphical user interface to ease working with getML and significantly
accelerate your workflow.


## Data Set


The data set used in this tutorial consists of 2 tables. The so-called
population table represents the entities we want to make a prediction about in
the analysis. The peripheral table contains additional information and is
related to the population table via a join key. Such a data set could appear
for example in a customer churn analysis where each row in the population table
represents a customer and each row in the peripheral table represents a
transaction. It could also be part of a predictive maintenance campaign where
each row in the population table corresponds to a particular machine in a
production line and each row in the peripheral table to a measurement from a
certain sensor.

In this project, however, we do not assume any particular use case. After all,
getML is applicable to a wide range of problems from different domains. Use
cases from specific fields are covered in other articles.

## Result

This project demonstrates the very basics of getML. Starting with raw data you
have completed a full project including feature learning and linear regression
using an automated end-to-end pipeline. The most tedious part of this process -
finding the right aggregations and subconditions to construct a feature table
from the relational data model - was also included in this pipeline. 

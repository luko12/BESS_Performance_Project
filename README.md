# BESS_Performance_Project
This project implements an ETL pipeline, data cleaning and transformation, and exploratory data analysis to understand BESS operating behavior.

* Datasets hosted in Datasets folder as CSVs
* Azure Synapse Analytics pipeline copies CSVs into Delta Tables in ADLS gen2 storage account in Bronze workspace
* Python notebook queries external weather API and loads into Delta Table in Bronze workspace with pySpark
* Python notebook cleans, transforms, and merges datasets together into a Delta Table in the Silver workspace with pySpark
* SQL query creates view of Delta Table in SQL serverless database
* PowerBI reads view into dashboard
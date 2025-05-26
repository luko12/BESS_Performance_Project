import os
import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import pyodbc
from sqlalchemy import create_engine
import datetime
from dotenv import load_dotenv

import urllib

load_dotenv()

server = os.getenv("SQL_SERVER")
database = os.getenv("SQL_DB")
username = os.getenv("SQL_USERNAME")
password = os.getenv("SQL_PASSWORD")

params = urllib.parse.quote_plus(
    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"UID={username};"
    f"PWD={password};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=30;"
)

engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")


df = pd.read_sql("SELECT * FROM dbo.merged_delta_view", engine)
df['datetime_minute'] = pd.to_datetime(df['datetime_minute'])
df = df.sort_values(by='datetime_minute')


# Build Dash app
assets_path = os.path.join(os.getcwd(), 'assets')
print("ASSETS PATH:", assets_path)

app = dash.Dash(__name__, assets_folder='assets')

# Layout
app.layout = html.Div([
    html.H1("BESS Performance Dashboard- Coding Assignment"),
    html.H3("Created by Lukas Houpt for esVolta"),

    html.H2("Contents:"),
    html.Ul([   
        html.Li("Dashboard Overview"),
        html.Li("Part 1: Data Ingestion and ETL Pipeline Implementation"),
        html.Li("Part 2: Data Merging and Analysis"),
        html.Li("Part 3: Exploratory Data Analysis"),
        html.Li("Part 4: Dashboard Implementation and Deployment"),
    ]),

    html.H2("Dashboard Overview"),
    html.P("""For an initial overview of the dataset, I chose the LMP, racks online, power, SOC, and temperature columns. 
           An immediate observation is that racks online value drops off right as the LMPs spike on 4/30 at 02:00 UTC. Correspondingly, the site basepoint and power was stunted, indicating a possible missed revenue opportunity."""),
    
    html.H4("Feel free to use the date slicer to explore the data further:"),
    html.Div([
        dcc.RangeSlider(
            id='date-range-slider',
            min=df['datetime_minute'].min().timestamp() * 1000,
            max=df['datetime_minute'].max().timestamp() * 1000,
            value=[
                df['datetime_minute'].min().timestamp() * 1000,
                df['datetime_minute'].max().timestamp() * 1000
            ],
            step=60 * 60 * 1000,
            marks=None,
            tooltip={"placement": "bottom", "always_visible": False}
        )
    ], style={'maxWidth': '600px', 'margin': '40px auto 10px'}),

    html.Div([
        html.Div(id='start-date-label', style={'marginBottom': '4px'}),
        html.Div(id='end-date-label', style={'marginBottom': '20px'})
    ], style={'textAlign': 'center'}),

    html.Div([
        html.Div([
            dcc.Graph(id='graph1', style={'width': '48%'}),
            dcc.Graph(id='graph2', style={'width': '48%'})
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'marginBottom': '20px'}),

        html.Div([
            dcc.Graph(id='graph3', style={'width': '48%'}),
            dcc.Graph(id='graph4', style={'width': '48%'})
        ], style={'display': 'flex', 'justifyContent': 'space-between'})
    ], id='graphs-container', style={'padding': '0 20px'}),


    html.H2("Part 1: Data Ingestion and ETL Pipeline Implementation"),
    html.P([
        "I started this project by creating a ",
        html.A("github repository", href="https://github.com/luko12/BESS_Performance_Project"),
        " and adding the three CSVs provided in the instructions to a ",   
        html.A("Datasets folder", href="https://github.com/luko12/BESS_Performance_Project/tree/main/Datasets"),
        ". In an effort to emulate an ETL workflow that I might use in a production environment, I created an Azure environment to host "
        "the dashboard and ETL services. Within a resource group labeled BESS_Resource_Group, I created an Azure Data Lake Storage Gen2 storage  "
        "account which supports my desired hierarchical namespace of Bronze, Silver, and Gold to separate raw data from cleaned and processed data. ",
        html.Br(),
        html.Br(),
        "The next resource I created was the Azure Data Factory, which I intended to use for my ETL workflows, "
        "however I quickly discovered that I could not create a Spark cluster within ADF Databricks due to free "
        "tier compute limitations. Instead, I pivoted to Synapse Analytics and, using a Spark cluster, developed a pipeline that"
        " copied the three CSVs from the external Github folder into the Bronze layer of my storage account in Delta Table format. "
        " The pipeline also queries data from the external weather API into a Delta Table within the Bronze layer. ",
        html.Br(),
        html.Br(),
        "Spark + Delta Tables make for efficient computation and storage for BESS "
        "Performance data because Spark uses distributed computing on multiple notes and Delta Tables are built off of parquet files."
        " In a production environment, "
        "this pipeline might be copying data from a site historian or other SCADA system and on a scheduled/automated basis rather than as "
        "a one-time copy. Synapse Analytics offers the functionality to connect to such SCADA systems and to schedule runs on a desired frequency.",
        html.Br(),
        html.Br(),
        html.A("A quick note about the suggested NWS weather API: this API only provides 7 days historical observations and primarily is used for forecasting. "
        "Therefore, I had to use an alternative weather API "),
        html.A("Open-Meteo", href="https://open-meteo.com/en/docs"),
        " to obtain historical data with timestamps matching those of the provided CSVs.",

        html.H4("Code and Screenshots of ETL Workflow:"),
        html.Ul([
            html.Li(html.A("Python Notebook to Write CSVs as Delta Tables", href="https://github.com/luko12/BESS_Performance_Project/blob/main/dev/WriteCSVasDeltaTable.ipynb"
            )),
            html.Li(html.A("Synapse Pipeline to Copy CSVs to Bronze Layer", href="https://github.com/luko12/BESS_Performance_Project/blob/main/dev/WriteWeatherDataasDeltaTable.ipynb"
            )),
        ]),
        html.P("Screenshot of Azure Portal resource group:"),
        html.Img(src='/assets/capture2.PNG', style={'width': '75%', 'height': 'auto'}),
        html.P("Screenshot of ADLS Gen2 storage account:"),
        html.Img(src='/assets/Capture3.PNG', style={'width': '75%', 'height': 'auto'}),
        html.P("Screenshot of ADLS Gen2 storage account Bronze layer with copied CSVs and Delta Tables:"),
        html.Img(src='/assets/capture1.PNG', style={'width': '75%', 'height': 'auto'}),
        html.P("Screenshot of Synapse Analytics pipeline to copy CSVs and Weather Data API into Bronze layer:"),
        html.Img(src='/assets/Capture.PNG', style={'width': '75%', 'height': 'auto'}),


        html.H2("Part 2: Data Merging and Analysis"),
        html.P("After copying the CSVs and weather data into the Bronze layer, I created another Synapse Spark notebook and " \
               "pipeline to merge the datasets "
               "into a single unified Delta Table in the Silver layer. This process involved the following steps:"),
        html.Ol([
            html.Li("Converting timestamps to a uniform datetetime format"),
            html.Li("Deleting null rows"),
            html.Li("Changing column data types as appropriate (string vs float)"),
            html.Li("Renaming ambiguous columns (the site and RTAC tables each had an LMP column)"),
            html.Li("Grouping by datetime_minute to ensure all datasets are aligned regardless of minute/second"),
            html.Li("Merging the site, RTAC, and meter datasets on the datetime_minute column"),
            html.Li("Calculating a rounded-down datetime_hour value and merging with the weather dataset"),
            html.Li("Filtering to datetime_minutes where all datasets have data"),
            html.Li("Writing the merged dataset to a Delta Table in the Silver layer")
        ]),
        html.P("With a prepped dataset, I was almost ready for analysis. Before diving into analysis, I created a SQL Serverless database" \
        " in Synapse and created a SQL View on top of the Delta Table that could be accessed externally. See a preview of the SQL View below"),

        html.H4("Code and Screenshots of ETL Workflow:"),
        html.Ul([
            html.Li(html.A("Python Notebook to Merge/Clean/Analyze Datasets", href="https://github.com/luko12/BESS_Performance_Project/blob/main/dev/MergeDatasetsIntoSilver.ipynb"
            )),
            html.Li(html.A("SQL Script to Create DB", href="https://github.com/luko12/BESS_Performance_Project/blob/main/dev/create_bess_analytics_database.sql"
            )),
            html.Li(html.A("SQL Script to Create a View of Merged Delta Table", href="https://github.com/luko12/BESS_Performance_Project/blob/main/dev/create_merged_silver_view.sql"
            ))
        ]),
        html.P("Screenshot of Synapse Analytics pipeline to clean and merge the datasets:"),
        html.Img(src='/assets/Capture4.PNG', style={'width': '75%', 'height': 'auto'}),
        html.P("Screenshot of ADLS Gen2 storage account Silver layer with merged Delta Table:"),
        html.Img(src='/assets/Capture5.PNG', style={'width': '75%', 'height': 'auto'}),
        html.P("Screenshot of SQL View of Merged Delta Table in Synapse Serverless SQL:"),
        html.Img(src='/assets/Capture6.PNG', style={'width': '75%', 'height': 'auto'}),

        html.H2("Part 3: Exploratory Data Analysis"),
                           
    ]),

])

@app.callback(
    [Output('graph1', 'figure'),
     Output('graph2', 'figure'),
     Output('graph3', 'figure'),
     Output('graph4', 'figure'),
     Output('start-date-label', 'children'),
     Output('end-date-label', 'children')],
    [Input('date-range-slider', 'value')]
)
def update_graphs(slider_range):
    start_ts, end_ts = slider_range
    start_dt = datetime.datetime.fromtimestamp(start_ts / 1000)
    end_dt = datetime.datetime.fromtimestamp(end_ts / 1000)

    filtered_df = df[(df['datetime_minute'] >= start_dt) & (df['datetime_minute'] <= end_dt)]

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=filtered_df['datetime_minute'], y=filtered_df['rtac_lmp'],
                              mode='lines', name='RTAC LMP'))
    fig1.add_trace(go.Scatter(x=filtered_df['datetime_minute'], y=filtered_df['racks_online'],
                              mode='lines', name='Racks Online', yaxis='y2'))

    fig1.update_layout(
        title=dict(text='LMP & Racks Online', y=0.99),
        yaxis=dict(title='LMP'),
        yaxis2=dict(title='Racks Online', overlaying='y', side='right', showgrid=False),
        margin=dict(l=60, r=60, t=60, b=40),  # Equal left/right margin
        height=300,
        xaxis=dict(dtick=6 * 60 * 60 * 1000, tickformat="%H:%M\n%b %d"),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5)
    )

    fig2 = go.Figure()
    for col in ['BESSkW', 'RTAC_P', 'gen_base_point']:
        fig2.add_trace(go.Scatter(x=filtered_df['datetime_minute'], y=filtered_df[col],
                                  mode='lines', name=col))
    fig2.update_layout(
        title=dict(text='BESSkW, RTAC_P, Gen Base Point', y=.99),
        margin=dict(l=20, r=20, t=60, b=20),
        height=300,
        xaxis=dict(dtick=6 * 60 * 60 * 1000, tickformat="%H:%M\n%b %d"),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5)
    )

    fig3 = px.line(filtered_df, x='datetime_minute', y='SOC', title='State of Charge (SOC)')
    fig3.update_layout(
        title=dict(text='SOC Over Time', y=0.95),
        margin=dict(l=60, r=60, t=60, b=40),  # Same margins
        height=300,
        xaxis=dict(dtick=6 * 60 * 60 * 1000, tickformat="%H:%M\n%b %d")
    )
    fig3.update_xaxes(dtick=6 * 60 * 60 * 1000, tickformat="%H:%M\n%b %d")

    fig4 = px.line(filtered_df, x='datetime_minute', y='temperature', title='Temperature')
    fig4.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=300)
    fig4.update_xaxes(dtick=6 * 60 * 60 * 1000, tickformat="%H:%M\n%b %d")

    start_str = f"Start Date: {start_dt.strftime('%m/%d %H:%M')}"
    end_str = f"End Date: {end_dt.strftime('%m/%d %H:%M')}"

    return fig1, fig2, fig3, fig4, start_str, end_str



server = app.server

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8050)))

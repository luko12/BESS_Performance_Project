import os
import dash
from dash import dcc, html, Input, Output, dash_table
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
import pandas as pd
import pyodbc
from sqlalchemy import create_engine
import datetime
from dotenv import load_dotenv
import math
import urllib
import figs


############################################
# Load environment variables and connect to SQL Server
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

# import merged df
df = pd.read_sql("SELECT * FROM dbo.merged_delta_view", engine)
df['datetime_minute'] = pd.to_datetime(df['datetime_minute'])
df = df.sort_values(by='datetime_minute')

# supporting calculations for RTE
df['RTAC_KWH'] = df['RTAC_P'] / 60
df['Charge_KWH'] = abs(df['RTAC_KWH'].where(df['RTAC_P'] < 0, 0))
df['Discharge_KWH'] = df['RTAC_KWH'].where(df['RTAC_P'] > 0, 0)

# supporting calculations for availability
max_racks = df['racks_online'].max()
max_units = df['UnitsOnline'].max()
df['Rack_Availability'] = df['racks_online'] / max_racks * 100
df['Unit_Availability'] = df['UnitsOnline'] / max_units * 100
avg_rack_availability = df['Rack_Availability'].mean()
avg_unit_availability = df['Unit_Availability'].mean()
df['Power_Availability'] = df['ActiveMaxP'] / 100000 * 100
avg_power_availability = df['Power_Availability'].mean()

# supporting calculations for temperature
avg_max_cell_temp = df['MaxCellT'].mean()
avg_weather_temp = df['temperature'].mean()

# import cycles df
cycles = pd.read_sql("SELECT * FROM dbo.cycles_delta_view", engine)
cycles['start_datetime_minute'] = pd.to_datetime(cycles['start_datetime_minute'])
cycles['end_datetime_minute'] = pd.to_datetime(cycles['end_datetime_minute'])
cycles = cycles.sort_values(by='start_datetime_minute')


############################################
# Complicated graph with dropdown for trace selection

columns_per_row = 5
col_names = df.columns.tolist()
rows = [
    col_names[i:i + columns_per_row]
    for i in range(0, len(col_names), columns_per_row)
]

status_cols = [
    '89_l1_status',
    'avr_status',
    'gen_virtual_breaker_status',
    '52_1_status',
    'gen_sc_status',
    '89_b1_status',
    'Status'
]

# Keep only float-type columns from the list
float_status_cols = [
    col for col in status_cols
    if col in df.columns and pd.api.types.is_float_dtype(df[col])
]

fig31 = go.Figure()
for i, col in enumerate(float_status_cols):
    axis_id = "" if i == 0 else str(i + 1)
    fig31.add_trace(go.Scatter(
        x=df['datetime_minute'],
        y=df[col],
        name=col,
        yaxis=f'y{axis_id}'
    ))

layout = dict(
    title="Float Status Signals Over Time",
    xaxis=dict(title="Time"),
)

for i, col in enumerate(float_status_cols):
    axis_id = "" if i == 0 else str(i + 1)
    layout[f'yaxis{axis_id}'] = dict(
        title=col,
        overlaying='y' if i != 0 else None,
        side='left' if i % 2 == 0 else 'right',
        position=0.05 + 0.05 * i if i != 0 else None,
        showgrid=False
    )

fig31.update_layout(layout)


###########################################################
# Build Dash app

assets_path = os.path.join(os.getcwd(), 'assets')
app = dash.Dash(__name__, assets_folder='assets')


###########################################################
# Structure app layout

app.layout = html.Div([
    html.H1("BESS Performance Dashboard- Coding Assignment"),
    html.H3("Created by Lukas Houpt for esVolta"),

    html.H2("Contents:"),
    html.Ul([   
        html.Li("Dashboard Overview and Summary"),
        html.Li("Part 1: Data Ingestion and ETL Pipeline Implementation"),
        html.Li("Part 2: Data Merging and Analysis"),
        html.Li("Part 3: Exploratory Data Analysis"),
        html.Li("Part 4: Dashboard Implementation and Deployment"),
    ]),

    ###########################################################
    # Dashboard Overview and Summary Section
    html.H2("Dashboard Overview and Summary"),
    html.P("""For an initial overview of the dataset, I chose the LMP, racks online, power, SOC, and temperature columns. 
           An immediate observation is that the racks online value drops off right as the LMPs spike on 4/30 at 02:00 UTC. 
           Correspondingly, the site basepoint and power was stunted, indicating a possible missed revenue 
           opportunity. I would be very interested to understand why the racks faulted offline, however
           the datasets provided do not include unit or rack-level information."""),
    
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
    html.H4("Key findings:"),
    html.Ul([   
        html.Li("Possible LMP forecasting/trading opportunity due to 0.55 correlation between LMP and BESS dispatch"),
        html.Li("High quality HSL logic with minimal basepoint deviations (.99 correlation between basepoint and BESS dispatch)"),
        html.Li("Site charges evenly across power levels but discharges most frequently at 60MW"),
        html.Li("Site never dispatches at full power, indicating conservative operation/underutilization of power capacity"),
        html.Li("Site idles at high SOC, and a reduction in resting SOC might be beneficial to mitigate degradation risk"),
        html.Li("Charge and discharge cycles rarely exceed 40 minutes, and DOD is always < 40%, indicating underutilization of energy capacity"),
        html.Li("2-day RTE is 56%, with individual cycles ranging up to 115%. RTE calculated from operational data can be misleading"),
        html.Li("2-day average unit availability of 80%, average rack availability of 65%, and average power availability of 50%"),
        html.Li("2-day average max cell temperature of 48degC runs slightly warmer than is be preferred"),
    ]),

    ###########################################################
    # Part 1 Section
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
        "Performance data because Spark uses distributed computing on multiple nodes and Delta Tables are built off of parquet files."
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
    ]),

    ###########################################################
    # Part 2 Section
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

    ###########################################################
    # Part 3 Section
    html.H2("Part 3: Exploratory Data Analysis"),
    html.H4("DataFrame Columns"),
    html.Table([
        html.Tbody([
            html.Tr([
                html.Td(col) for col in row
            ]) for row in rows
        ])
    ]),

    html.H4("Plot of Status Signals (with Dropdown)"),
    html.P("Note that statuses are unchanging over time"),
    dcc.Dropdown(
        id='status-selector',
        options=[{'label': col, 'value': col} for col in float_status_cols],
        value=float_status_cols[0],
        clearable=False
    ),

    dcc.Graph(id='status-graph'),

    html.H4("Scatterplot: LMP vs BESSkW"),
    html.P("There's a clear relationship between LMP and BESS dispatch, with higher prices " \
    "resulting in higher discharging and lower prices resulting in higher charging."
    " However, the dispatch activity is only moderately correlated with LMP which suggests" \
    " significant room" \
    " for improvement."),
    dcc.Graph(
        id='lmp-bess-scatter',
        figure=figs.render_scatter_lmp(df)
    ),
    html.H4("Scatterplot: Basepoint vs BESSkW"),
    html.P("There's a very strong correlation between power and base point, which indicates "
    "that HSL is calculated well and the system control logic is able to follow commands without "
    "surprises. This is a very good sign- many other BESS operators in ERCOT struggle with basepoint deviations."),
    dcc.Graph(
        id='power-basepoint-scatter',
        figure=figs.render_scatter_basepoint(df)
    ),
    html.H4("Scatterplot: Basepoint vs BESSkW at SOC Extremes"),
    html.P("As expected, the site's ability to follow basepoint deteriorates as it approaches SOC extremes," \
    " but only very slightly. " \
    "This indicates high quality PPC/HSL logic with a well-tuned lookahead function " \
    "to account for potential racks faulting offline within the SCED interval as they" \
    " hit SOC or cell voltage protection limits. There might be minor room" \
    " for improvement to the HSL lookahead function to better estimate behavior at " \
    " the extremes, but overall I am quite impressed with the performance!"),
    dcc.Graph(
        id='power-basepoint-scatter-extremes',
        figure=figs.render_scatter_basepoint_extremes(df)
    ),
    html.H4("Histogram: RTAC_P"),
    html.P("Filtering OUT idling periods when RTAC_P is between (-2MW, 2MW), we can see" \
    " an interesting distribution of power values. Since negative power indicates charging," \
    " we can see the the site charges relatively evenly across the range of power values. " \
    "On the other hand, we can observe that the site discharges mostly at high power (60MW+). " \
    "An observation is that despite the listed site spec of 100MW, we do not observe power beyond +/- 65MW."),
    dcc.Graph(
        id='power-histogram',
        figure=figs.render_power_histogram(df)
    ),
    html.H4("Histogram: Resting SOC"),
    html.P("Filtering ONLY idling periods when RTAC_P is between (-2MW, 2MW), we can see" \
    " that the site largely rests at high SOC (97.5%+). This can be beneficial, for example if the OEM " \
    "enables automatic cell balancing at high SOC (eg Powin). Not all OEMs enable balancing at high SOC though, " \
    "for example Sungrow enables balancing at the low end of the SOC/voltage curve. Either way, " \
    " outside of cell balancing it is generally not recommended " \
    " to idle the cells at their extremes and is instead recommended to enter the platform period of ~10-90%" \
    " for extended idling to mitigate cell degradation."),
    dcc.Graph(
        id='resting-soc-histogram',
        figure=figs.render_resting_SOC_histogram(df)
    ),
    html.H2("Cycles Analysis"),
    html.P("In this section, I further refined the silver dataset into a cycles dataset" \
    " which lives in the Gold layer of the ADLS Gen2 storage account. Like the silver " \
    "dataset, I created a SQL View on top of this Delta Table. To create this dataset, I " \
    'categorized each row in the silver dataset as "charging", "discharging", or "idling"' \
    " based on the RTAC_P value. I then looped over the dataset and associated " \
    "continuous rows into discharge cycles, charging cycles, and idles; each recorded with " \
    "their respective start time, end time, duration, average power, and SOC change."),
    html.P("Top 5 longest discharging cycles:"),
    dash_table.DataTable(
        columns=[{"name": col, "id": col} for col in cycles.columns],
        data=cycles[cycles['cycle_type']=='discharging'].sort_values(
            by='cycle_duration', ascending=False).head(5).to_dict('records'),
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left', 'padding': '5px'},
        style_header={'backgroundColor': 'lightgrey', 'fontWeight': 'bold'}
    ),
    html.P("Top 5 longest charging cycles:\n" \
    "Interestingly, the longest charging cycle results in a decrease in SOC. Upon further inspection" \
    " it appears that this is due to racks suddenly faulting offline at the end of the cycle. This illuminates " \
    "how the SOC value is calculated: it is the total SOC not the online SOC."),
    dash_table.DataTable(
        columns=[{"name": col, "id": col} for col in cycles.columns],
        data=cycles[cycles['cycle_type']=='charging'].sort_values(
            by='cycle_duration', ascending=False).head(5).to_dict('records'),
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left', 'padding': '5px'},
        style_header={'backgroundColor': 'lightgrey', 'fontWeight': 'bold'}
    ),
    html.H4("Cycle Duration Distribution"),
    html.P("The distribution of cycle duration shows that the majority of cycles are short (<20 minutes). The"\
    " charge cycles are slightly longer than the discharge cycles on average. Since the site is designed for 2hrs, this indicates "\
    "a possible under-utilization of energy capacity. Perhaps, with advanced SOC management, the site could be discharged "\
    "longer as the LMP spikes, or charged longer as the LMP dips. "),
    dcc.Graph(
        id='cycle-duration-distplot',
        figure=figs.render_cycle_duration_distplot(cycles)
    ),
    html.H4("Cycle Duration vs Average Power"),
    html.P("This plot shows a weak positive relationship between power and cycle duration. I would say this is expected " \
    "behavior: the shorter duration, low power applications are possibly reflective of frequency regulation/ancillary service trades" \
    " whereas the longer duration, high power cycles are possibly for energy trades"),
    dcc.Graph(
        id='cycle-duration-power-scatter',
        figure=figs.render_cycle_duration_power_scatter(cycles)
    ),
    html.H4("Depth of Discharge (DOD)"),
    html.P("This plot shows the SOC change achieved during each cycle, with a max SOC change of <40%. "\
            " Similar to the Cycle Duration Distribution plot, this indicates a possible under-utilization of the site's"\
            " installed energy capacity."),
    dcc.Graph(
        id='cycle-duration-soc-scatter',
        figure=figs.render_cycle_duration_soc_scatter(cycles)
    ),

    html.H2("RTE Analysis"),
    html.P("Round Trip Efficiency is typically calculated as discharge energy divided by charge energy. Often RTE is calculated " \
    "on a per-cycle basis, such as during a capacity test, however it can also be calculated over a longer period " \
    "of time. RTE can be heavily skewed by the following factors:"),
    html.Ul([
        html.Li("Self discharge and aux/parasitic loads: with more idling time, more " \
        "energy will be lost to these factors. Thus, long time frames typically show lower RTE"),
        html.Li("C-rate: higher C-rates result in reduced capacity. Thus, if the site is discharging at " \
        "full power, the RTE will be reduced compared to at a lower C-rate"),
        html.Li("Starting SOC: if the site starts at a high SOC, it may inflate the calculated RTE over a given timeframe (hence the 115% RTE)")
    ]),
    html.P("Over the entire date range, the site showed an RTE of 56%, however when slicing into individual charge/discharge " \
    "cycles we can see the RTE fluctuates to has high as ~115% (first cycle on 4/29). Overall, RTE is a fairly subjective" \
    " metric and, in order to accurately interpret it, one must consider how it is calculated. The RTE spec of 87% is likely" \
    " based on a capacity test, rather than operational data."),
    html.Div([
        dcc.RangeSlider(
            id='date-range-slider-rte',
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
        html.Div(id='start-date-label-rte', style={'marginBottom': '4px'}),
        html.Div(id='end-date-label-rte', style={'marginBottom': '20px'})
    ], style={'textAlign': 'center'}),
    html.Div([
        html.Div(id='discharge-MWH-label', style={'marginBottom': '4px'}),
        html.Div(id='charge-MWH-label', style={'marginBottom': '20px'}),
        html.Div(id='rte-label', style={'marginBottom': '20px'})
    ], style={'textAlign': 'center'}),
    dcc.Graph(id='rte-graph', style={'width': '48%'}),

    html.H2("Availability"),
    html.P("There are several way to calculate availability such as time-based, power-based, energy-based, " \
    "revenue weighted, etc. " \
    "and this is an evolving area in the BESS industry. For this analysis, I briefly calculate availability" \
    " in two ways:"),
    html.Ul([
        html.Li("As a function of equipment online: rack availability = racks online / total racks, assuming total racks = the " \
        "maximum racks online observed in the dataset (476). Units online is calculated similarly."),
        html.Li("As a function of power capability: given the site is rated for +/- 100MW, I calculate availability as " \
        "ActiveMaxP / 100MW."),
    ]),
    html.H4("Average Rack Availability: {:.2f}%".format(avg_rack_availability)),
    html.H4("Average Unit Availability: {:.2f}%".format(avg_unit_availability)),
    
    dcc.Graph(
        id='availability-graph',
        figure=figs.render_availability(df)
    ),
    html.H4("Average Power Availability: {:.2f}%".format(avg_power_availability)),
    dcc.Graph(
        id='power-availability-graph',
        figure=figs.render_power_availability(df)
    ),

    html.H2("Temperatures"),
    html.H4("Average Max Cell Temperature (degC): {:.2f}".format(avg_max_cell_temp)),
    html.H4("Average Weather (degC): {:.2f}".format(avg_weather_temp)),
    html.P("To start the very brief analysis on cell temperatures, we look at the correlation between " \
    "Max Cell Temperature and BESSkW. We see a very weak, negligible correlation which is surprising because " \
    "typically temperatures increase with power, especially when charging. An observation is that max cell temperatures "\
    "tend to run hot, on average {:.2f}degC. This likely indicates that the thermal management system is inadequate"
    " and that the cells are at risk of accelerated degradation.".format(avg_max_cell_temp)),
            dcc.Graph(
        id='cell-temp-power-graph',
        figure=figs.render_cell_temp_power(df)
    ),
    html.P("Looking at the correlation between Max Cell Temperature and Weather, we again see a weak relationship although" \
    " it is slightly stronger. This could also indicate that the thermal management system is inadequate against weather."),
            dcc.Graph(
        id='cell-temp-weather-graph',
        figure=figs.render_cell_temp_weather(df)
    ),

    ###########################################################
    # Part 4 Section
    html.H2("Part 4: Dashboard Implementation and Deployment"),
    html.P("I originally intended to use PowerBI for this dashboard, however I quickly discovered" \
           " that I was unable to publish the dashboard without a business account. Therefore, I pivoted to using " \
           "Dash and Plotly to create a quick Python web app, which I deployed to an Azure Web App service via Docker."),
    html.A("Dash/Plotly/Docker App code", href="https://github.com/luko12/BESS_Performance_Project/tree/main/App"),
    html.P("Screenshot of Azure Web App service:"),
        html.Img(src='/assets/Capture7.PNG', style={'width': '75%', 'height': 'auto'}),

    ###########################################################
    # Conclusion section
    html.H3("Closing Comments and use of Generative AI"),
    html.P("I had a lot of fun working on this project and I hope you enjoyed the dashboard! There is a lot to unpack" \
    " in BESS performance and I'm sure I am just scratching the surface here with a 2-day dataset that does not" \
    " include rack or cell level information, alarms etc. On the topic of next steps, I realized in Part 2 that I should have "\
    "summed, as opposed to averaged, the KWH and other counter values. On the topic of error handling, this could be improved " \
    "as my error handling was manual in nature: deleting null rows in the dataset, fixing ambiguous column names, etc. For sake " \
    "of time, I neglected try catch blocks to safely catch errors that could arise in a production setting. On the topic of Generative AI, " \
    "I used ChatGPT to help debug various aspects: producing the regex expression to identify columns with invalid characters, "\
    "brainstorming a workaround to Azure Data Factory / Data Bricks when I encounted the compute limit, and writing the Dockerfile" \
    " to deploy the app, specifically to resolve issues related to msodbcsql18 (ODBC Driver 18 for SQL Server) " \
    "which the app uses to query the synapse serverless sql database."),
])

###########################################################
# Interactive callbacks for updating graphs

# overview graphs with date range slider
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

    fig4 = px.line(filtered_df, x='datetime_minute', y='temperature', title='Weather (degC)')
    fig4.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=300)
    fig4.update_xaxes(dtick=6 * 60 * 60 * 1000, tickformat="%H:%M\n%b %d")

    start_str = f"Start Date: {start_dt.strftime('%m/%d %H:%M')}"
    end_str = f"End Date: {end_dt.strftime('%m/%d %H:%M')}"

    return fig1, fig2, fig3, fig4, start_str, end_str

###########################################################
# overview graphs with trace selector
@app.callback(
    Output('status-graph', 'figure'),
    Input('status-selector', 'value')
)
def update_status_graph(selected_col):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['datetime_minute'],
        y=df[selected_col],
        mode='lines',
        name=selected_col
    ))

    fig.update_layout(
        title=f"{selected_col} over Time",
        xaxis_title="Time",
        yaxis_title=selected_col,
        template="plotly_white"
    )
    return fig

###########################################################
# RTE graph with date range slider
@app.callback(
    [Output('rte-graph', 'figure'),
     Output('start-date-label-rte', 'children'),
     Output('end-date-label-rte', 'children'),
     Output('charge-MWH-label', 'children'),
     Output('discharge-MWH-label', 'children'),
     Output('rte-label', 'children')],
    [Input('date-range-slider-rte', 'value')]
)
def update_graphs(slider_range):
    start_ts, end_ts = slider_range
    start_dt = datetime.datetime.fromtimestamp(start_ts / 1000)
    end_dt = datetime.datetime.fromtimestamp(end_ts / 1000)

    filtered_df = df[(df['datetime_minute'] >= start_dt) & (df['datetime_minute'] <= end_dt)]
    charge_MWH = filtered_df['Charge_KWH'].sum() / 1000
    discharge_MWH = filtered_df['Discharge_KWH'].sum() / 1000
    rte = discharge_MWH / charge_MWH if discharge_MWH != 0 else 0

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=filtered_df['datetime_minute'], y=filtered_df['RTAC_P'],
                              mode='lines', name='RTAC_P'))
    fig1.add_trace(go.Scatter(x=filtered_df['datetime_minute'], y=filtered_df['Charge_KWH'],
                              mode='lines', name='Charge_KWH', yaxis='y2', visible='legendonly'))
    fig1.add_trace(go.Scatter(x=filtered_df['datetime_minute'], y=filtered_df['Discharge_KWH'],
                              mode='lines', name='Discharge_KWH', yaxis='y2', visible='legendonly'))

    fig1.update_layout(
        title=dict(text='RTE', y=0.99),
        yaxis=dict(title='RTAC_P'),
        yaxis2=dict(title='Charge/Discharge KWH', overlaying='y', side='right', showgrid=False),
        margin=dict(l=60, r=60, t=60, b=40),  # Equal left/right margin
        height=300,
        xaxis=dict(dtick=6 * 60 * 60 * 1000, tickformat="%H:%M\n%b %d"),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5)
    )

    start_str = f"Start Date: {start_dt.strftime('%m/%d %H:%M')}"
    end_str = f"End Date: {end_dt.strftime('%m/%d %H:%M')}"

    charge_KWH_str = f"Total Charge MWH: {charge_MWH:.2f}"
    discharge_KWH_str = f"Total Discharge MWH: {discharge_MWH:.2f}"
    rte_str = f"Round Trip Efficiency (RTE): {rte:.2%}"

    return fig1, start_str, end_str, charge_KWH_str, discharge_KWH_str, rte_str


server = app.server

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8050)))

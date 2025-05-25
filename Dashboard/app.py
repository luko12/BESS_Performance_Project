import dash
from dash import dcc, html
import plotly.express as px
import pandas as pd
import pyodbc
from sqlalchemy import create_engine



import urllib
from sqlalchemy import create_engine

server = 'synapsebess-ondemand.sql.azuresynapse.net'
database = 'MyDB'
username = 'sqladminuser'
password = 'eepspXHpZKuaKnbGK0Jp0P&R@D'

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


# Create Plotly figure
fig = px.line(df, x="datetime_minute", y="BESSkW", title="Power over Time")

# Build Dash app
app = dash.Dash(__name__)
app.layout = html.Div([
    html.H1("Battery Dashboard"),
    dcc.Graph(figure=fig)
])

server = app.server  # Required for Azure

if __name__ == "__main__":
    app.run(debug=True)

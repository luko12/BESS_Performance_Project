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

# TODO: probably could combine these into one function per plot type

def render_scatter_lmp(df):
    corr = df[['rtac_lmp', 'BESSkW']].corr().iloc[0, 1]

    fig = px.scatter(
        df,
        x='rtac_lmp',
        y='BESSkW',
        title="LMP vs BESSkW",
        labels={'rtac_lmp': 'Locational Marginal Price', 'BESSkW': 'Battery Power (kW)'},
        opacity=0.7
    )

    fig.add_annotation(
        xref='paper',
        yref='paper',
        x=0.5,
        y=1.1,
        showarrow=False,
        font=dict(size=14),
        text=f"Correlation Coefficient: {corr:.3f}"
    )

    fig.update_layout(template="plotly_white")
    return fig

# Second scatterplot: BESSkW vs gen_base_point
def render_scatter_basepoint(df):

    corr = df[['gen_base_point', 'BESSkW']].corr().iloc[0, 1]

    fig = px.scatter(
        df,
        x='gen_base_point',
        y='BESSkW',
        title="Basepoint vs BESSkW",
        labels={'gen_base_point': 'Base Point', 'BESSkW': 'Battery Power (kW)'},
        opacity=0.7
    )

    fig.add_annotation(
        xref='paper',
        yref='paper',
        x=0.5,
        y=1.1,
        showarrow=False,
        font=dict(size=14),
        text=f"Correlation Coefficient: {corr:.3f}"
    )

    fig.update_layout(template="plotly_white")
    return fig

# Third scatterplot: BESSkW vs gen_base_point at SOC extremes
def render_scatter_basepoint_extremes(df):

    df_filtered = df[(df['SOC'] < 10) | (df['SOC'] > 90)]
    corr = df_filtered[['gen_base_point', 'BESSkW']].corr().iloc[0, 1]

    fig = px.scatter(
        df_filtered,
        x='gen_base_point',
        y='BESSkW',
        title=r"Basepoint vs BESSkW at SOC Extremes (<10% or >90%)",
        labels={'gen_base_point': 'Base Point', 'BESSkW': 'Battery Power (kW)'},
        opacity=0.7
    )

    fig.add_annotation(
        xref='paper',
        yref='paper',
        x=0.5,
        y=1.1,
        showarrow=False,
        font=dict(size=14),
        text=f"Correlation Coefficient: {corr:.3f}"
    )

    fig.update_layout(template="plotly_white")
    return fig

def render_power_histogram(df):
    df_filtered = df[(df['RTAC_P'] > 2000) | (df['RTAC_P'] < -2000)]  # Filter out idling
    fig = px.histogram(
        df_filtered,
        x='RTAC_P',
        nbins=40,
        title="Histogram of RTAC_P",
        labels={'RTAC_P': 'RTAC Power'},
    )
    fig.update_layout(template="plotly_white")
    return fig

def render_resting_SOC_histogram(df):
    df_filtered = df[(df['RTAC_P'] < 2000) | (df['RTAC_P'] > -2000)]  # Filter only idling
    fig = px.histogram(
        df_filtered,
        x='SOC',
        nbins=40,
        title="Histogram of Resting SOC",
    )
    fig.update_layout(template="plotly_white")
    return fig

# cycles
def render_cycle_duration_distplot(cycles):
    charging = cycles[cycles["cycle_type"] == "charging"]["cycle_duration"]
    discharging = cycles[cycles["cycle_type"] == "discharging"]["cycle_duration"]

    fig = ff.create_distplot(
        [charging, discharging],
        group_labels=["Charging", "Discharging"],
        show_hist=False,
        show_rug=True
    )
    fig.update_layout(
        xaxis_title="Cycle Duration (minutes)",
        yaxis_title="Frequency",
        title="Cycle Duration"
    )
    return fig

def render_cycle_duration_power_scatter(cycles):
    fig = px.scatter(
        cycles,
        x="cycle_duration",
        y="average_power",  # all y=0 to align along x-axis
        color="cycle_type"
    )
    fig.update_layout(
        xaxis_title= "Cycle Duration (minutes)",
        yaxis_title= "Average Power (kW)",
        title="Cycle Duration vs Average Power"
    )
    return fig

def render_cycle_duration_soc_scatter(cycles):
    cycles['abs_soc_change'] = abs(cycles['soc_change'])
    fig = px.scatter(
        cycles,
        x="cycle_duration",
        y="abs_soc_change",  # all y=0 to align along x-axis
        color="cycle_type"
    )
    fig.update_layout(
        xaxis_title="Cycle Duration (minutes)",
        yaxis_title="Absolute SOC Change (%)",
        title="Depth of Discharge"
    )
    return fig

def render_availability(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['datetime_minute'], y=df['Rack_Availability'],
                          mode='lines', name='Rack Availability %'))
    fig.add_trace(go.Scatter(x=df['datetime_minute'], y=df['Unit_Availability'],
                        mode='lines', name='Unit Availability %'))

    fig.update_layout(
        title=dict(text='RTE', y=0.99),
        yaxis=dict(title='Equipment Availability %'),
        margin=dict(l=60, r=60, t=60, b=40),  # Equal left/right margin
        height=300,
        xaxis=dict(dtick=6 * 60 * 60 * 1000, tickformat="%H:%M\n%b %d"),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5)
    )
    return fig

def render_power_availability(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['datetime_minute'], y=df['Power_Availability'],
                    mode='lines', name='Power Availability %'))
    fig.add_trace(go.Scatter(x=df['datetime_minute'], y=df['ActiveMaxP'],
                          mode='lines', name='Max Power', yaxis='y2'))

    fig.update_layout(
        title=dict(text='RTE', y=0.99),
        yaxis=dict(title='Power Availability %'),
        yaxis2=dict(title='Max Power', overlaying='y', side='right', showgrid=False),
        margin=dict(l=60, r=60, t=60, b=40),
        height=300,
        xaxis=dict(dtick=6 * 60 * 60 * 1000, tickformat="%H:%M\n%b %d"),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5)
    )
    return fig

def render_cell_temp_power(df):
    corr = df[['MaxCellT', 'BESSkW']].corr().iloc[0, 1]
    fig = px.scatter(
        df,
        x='MaxCellT',
        y='BESSkW',
        title="Max Cell Temperature vs BESSkW",
        opacity=0.7
    )
    fig.add_annotation(
        xref='paper',
        yref='paper',
        x=0.5,
        y=1.1,
        showarrow=False,
        font=dict(size=14),
        text=f"Correlation Coefficient: {corr:.3f}"
    )
    return fig

def render_cell_temp_weather(df):
    corr = df[['MaxCellT', 'temperature']].corr().iloc[0, 1]
    fig = px.scatter(
        df,
        x='MaxCellT',
        y='temperature',
        title="Max Cell Temperature vs Weather Temperature",
        opacity=0.7
    )
    fig.add_annotation(
        xref='paper',
        yref='paper',
        x=0.5,
        y=1.1,
        showarrow=False,
        font=dict(size=14),
        text=f"Correlation Coefficient: {corr:.3f}"
    )
    return fig

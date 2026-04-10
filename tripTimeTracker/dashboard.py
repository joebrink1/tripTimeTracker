import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import pandas as pd
import plotly.graph_objects as go
import plotly.figure_factory as ff
import plotly.express as px
from tripTimeTracker.db import query_records, retrieve_tripNames
from tripTimeTracker.analytics import *

import datetime



def empty_figure(title="Placeholder"):
    fig = go.Figure()
    fig.update_layout(
        title=title,
        template="plotly_dark",
        paper_bgcolor="#1B2444",
        plot_bgcolor="#1B2444",
        font=dict(color="white"),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig

def create_timeseries_figure(df):
    """
    Create a time-series plot with one line per 'name'.
    """
    fig = px.line(
        df,
        x="time",
        y="tripTime",
        title="Time Series by Name"
    )
    fig.update_layout(
        title='Main Time Series',
        template="plotly_dark",
        paper_bgcolor="#1B2444",
        plot_bgcolor="#1B2444",
        showlegend=False,
        xaxis_title='Departure Time',
        yaxis_title='Trip Duration (minutes)',
        font=dict(color="white"),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig

def plot_test_day_forecast(df_original, df_completed):
    """
    Plot actual early-day data, historical average, and predicted remainder.

    Args:
        df_original  : dataframe BEFORE prediction (partial day actuals)
        df_completed : dataframe returned from predict_remaining_day()
    """

    # Ensure datetime conversion (same as training/predict)
    df_original = df_original.copy()
    df_original["dt"] = pd.to_datetime(df_original["dt"], unit='s').dt.tz_localize('UTC').dt.tz_convert('America/New_York')



    df_completed = df_completed.copy()

    # Determine prediction start time
    prediction_start = df_original["dt"].max()

    # Split actual vs predicted
    actual_known = df_completed[df_completed["dt"] <= prediction_start]
    predicted = df_completed[df_completed["dt"] > prediction_start]

    # Build historical average curve for that DOW
    dow = prediction_start.day_name()
    df_hist = df_original.copy()
    df_hist["time"] = df_hist["dt"].dt.strftime("%H:%M")
    df_hist["dow"] = df_hist["dt"].dt.day_name()

    hist_avg = (
        df_hist.groupby(["dow", "time"])["tripTime"]
        .mean()
        .loc[dow]
        .reset_index()
    )

    hist_avg["dt"] = pd.to_datetime(
        prediction_start.strftime("%Y-%m-%d") + " " + hist_avg["time"]
    ).dt.tz_localize('America/New_York')

    # Plot
    fig = go.Figure()

    # Historical average
    fig.add_trace(go.Scatter(
        x=hist_avg["dt"],
        y=hist_avg["tripTime"]/60,
        mode="lines",
        name="Historical Avg",
        line=dict(dash="dash")
    ))

    # Actual known
    fig.add_trace(go.Scatter(
        x=actual_known["dt"],
        y=actual_known["tripTime"]/60,
        mode="lines+markers",
        name="Actual",
        line=dict(width=3)
    ))

    # Predicted
    fig.add_trace(go.Scatter(
        x=predicted["dt"],
        y=predicted["tripTime"]/60,
        mode="lines",
        name="Predicted",
        line=dict(dash="dot")
    ))

    # Vertical line where prediction starts
    fig.add_vline(
        x=prediction_start,
        line_width=2,
        line_dash="dash",
        line_color="gray"
    )

    fig.update_layout(
        title=f"Forecast for {prediction_start.strftime('%Y-%m-%d')}",
        template="plotly_dark",
        paper_bgcolor="#1B2444",
        plot_bgcolor="#1B2444",
        #showlegend=False,
        xaxis_title='Departure Time',
        yaxis_title='Trip Duration (minutes)',
        font=dict(color="white"),
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig


def plot_historical_trend(df, selected_epoch):

    dow = selected_epoch.strftime('%A')
    time1 = (selected_epoch - datetime.timedelta(minutes=7)).strftime('%H:%M')
    time2 = (selected_epoch + datetime.timedelta(minutes=7)).strftime('%H:%M')

    df = df[
        (df["dow"] == dow) &
        (df["time"] >= time1) &
        (df["time"] <= time2)
    ].groupby("date")["tripTime"].max().reset_index()

    fig = ff.create_distplot([df.tripTime/60], ['Trip Time'], colors=['Red'],
                            bin_size=1, show_rug=False)

    fig.update_layout(
        title=f"Travel Time Variability: {selected_epoch.strftime('%H:%M')}",
        template="plotly_dark",
        paper_bgcolor="#1B2444",
        plot_bgcolor="#1B2444",
        showlegend=False,
        xaxis_title='Trip Duration (minutes)',
        font=dict(color="white"),
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig

def create_dow_heatmap(df, selected_epoch):
    dow = selected_epoch.strftime('%A')
    dow_df = df[df['dow'] == dow]

    heatmap_df = dow_df.pivot_table(index='date', columns='time', values='tripTime')
    heatmap_df = heatmap_df.sort_index()
    heatmap_df = heatmap_df.reindex(sorted(heatmap_df.columns), axis=1)
    heatmap_df = heatmap_df.interpolate(    axis=1, method="linear",    limit_direction="both")
    heatmap_df = heatmap_df.fillna(method="ffill", axis=1).fillna(method="bfill", axis=1)

    fig = go.Figure(data=go.Heatmap(    
                        z=heatmap_df.values,    
                        x=heatmap_df.columns,    
                        y=heatmap_df.index,    
                        colorscale="Jet",   
                        colorbar=dict(
                            title="Trip Time"
                        )
                    )
            )

    fig.update_layout(
        title=f"Historical {dow} Traffic",
        template="plotly_dark",
        paper_bgcolor="#1B2444",
        plot_bgcolor="#1B2444",
        showlegend=False,
        xaxis_title='Departure Time',
        yaxis_title='Date',
        font=dict(color="white"),
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig

def create_sidebar_radio():
    options = retrieve_tripNames()

    return dcc.RadioItems(
        id="sidebar-radio",
        options=[{"label": o.replace('_', ' '), "value": o} for o in options],
        value=options[0] if len(options)>0 else None,
        labelStyle={"display": "block", "padding": "10px"},
        inputStyle={"margin-right": "10px"},
        style={"color": "white"}
    )



CARD_STYLE = {
    "backgroundColor": "#1B2444",
    "padding": "15px",
    "borderRadius": "12px",
    "boxShadow": "0px 4px 12px rgba(0, 0, 0, 0.4)",
    "margin": "10px"
}

SIDEBAR_STYLE = {
    "backgroundColor": "#1B2444",
    "width": "220px",
    "padding": "20px",
    "boxShadow": "2px 0px 10px rgba(0,0,0,0.5)"
}

CONTENT_STYLE = {
    "flex": "1",
    "padding": "10px"
}



app = dash.Dash(__name__)
server = app.server 


app.layout = html.Div(
    style={
        "backgroundColor": "#161D33",
        "height": "100vh",
        "display": "flex",
        "color": "white",
        "fontFamily": "Arial"
    },
    children=[

        # Sidebar
        html.Div(
            style=SIDEBAR_STYLE,
            children=[
                html.H3("Controls"),
                create_sidebar_radio(),
                html.H4("Time Mode"),
                dcc.RadioItems(
                    id="time-mode-radio",
                    options=[
                        {"label": "Current", "value": "current"},
                        {"label": "Custom Epoch", "value": "custom"}
                    ],
                    value="current",
                    labelStyle={"display": "block", "padding": "10px", "color": "white"},
                    inputStyle={"margin-right": "10px"},
                    style={"color": "white"}
                ),
                html.Br(),
                dcc.Input(
                    id="epoch-input",
                    type="datetime-local",
                    placeholder="YYYY-MM-DDTHH:MM",
                    value=None,
                    style={"width": "100%"}
                )
            ]
        ),

        # Main Content Area
        html.Div(
            style=CONTENT_STYLE,
            children=[
                # Hidden store for filtered data
                dcc.Store(id="filtered-data-store"),

                # Interval for auto-refresh
                dcc.Interval(
                    id="interval-component",
                    interval=5 * 60 * 1000,  # 5 minutes
                    n_intervals=0
                ),

                # Top Large Card
                html.Div(
                    style={**CARD_STYLE, "height": "48vh"},
                    children=[
                        dcc.Graph(
                            id="plot-main",
                            figure=empty_figure("Main Plot"),
                            style={"height": "100%"}
                        )
                    ]
                ),

                # Bottom Row with 3 smaller cards
                html.Div(
                    style={"display": "flex", "height": "48vh"},
                    children=[
                        html.Div(
                            style={**CARD_STYLE, "flex": "1"},
                            children=[
                                dcc.Graph(
                                    id="plot-1",
                                    figure=empty_figure("Card 1"),
                                    style={"height": "100%"}
                                )
                            ]
                        ),
                        html.Div(
                            style={**CARD_STYLE, "flex": "1"},
                            children=[
                                dcc.Graph(
                                    id="plot-2",
                                    figure=empty_figure("Card 2"),
                                    style={"height": "100%"}
                                )
                            ]
                        ),
                    ]
                )
            ]
        )
    ]
)



@app.callback(
    Output("epoch-input", "disabled"),
    Input("time-mode-radio", "value")
)
def toggle_epoch_input(mode):
    return mode != "custom"



@app.callback(
    Output("filtered-data-store", "data"),
    Input("time-mode-radio", "value"),
    Input("epoch-input", "value"),
    Input("interval-component", "n_intervals"),
    Input("sidebar-radio", "value")
)
def filter_data(mode, selected_epoch, n, selected_trip):
    df = query_records()  # load full data from SQLite
    df = df[df['name'] == selected_trip]

    if df.empty:
        return df.to_json(date_format="iso", orient="split")

    if mode == "current":
        filtered_df = df[df["dt"] <= df["dt"].max()]
    elif mode == "custom" and selected_epoch:
        selected_epoch = datetime.datetime.timestamp(datetime.datetime.strptime(selected_epoch, '%Y-%m-%dT%H:%M'))
        filtered_df = df[df["dt"] <= selected_epoch]

    else:
        filtered_df = df[df["dt"] <= df["dt"].max()]

    return filtered_df.to_json(date_format="iso", orient="records")



@app.callback(
    Output("plot-main", "figure"),
    Output("plot-1", "figure"),
    Output("plot-2", "figure"),
    Input("filtered-data-store", "data"),
    State("epoch-input", "value")
)
def update_plots(filtered_data_json, selected_epoch):
    import json
    df = pd.DataFrame(json.loads(filtered_data_json))
    if selected_epoch:
        selected_epoch = datetime.datetime.strptime(selected_epoch, '%Y-%m-%dT%H:%M')
    else:
        selected_epoch = datetime.datetime.now()
    
    selected_time = selected_epoch.strftime('%H:%M')
    
    day_start = selected_epoch.replace(hour=0, minute=0, second=0, microsecond=0)

    print(f'Selected Epoch: {selected_epoch}')

    if len(df) > 0 and df.dt.max() > datetime.datetime.timestamp(day_start):

        model = trainModel(df)
        full_df = predict_remaining_day(model, df)
        #df = df[df['dt'] >= datetime.datetime.timestamp(day_start)]
        #full_df = full_df[full_df['dt']  >= datetime.datetime.timestamp(day_start)]
        full_df = full_df[full_df['date'] == df.date.max()]
        print(df.head())

        fig_main = plot_test_day_forecast(df, full_df)
        fig1 = plot_historical_trend(df, selected_epoch)
        fig2 = create_dow_heatmap(df, selected_epoch)
    
    else:
        fig_main = empty_figure("plot-main")
        fig1 = empty_figure("Card 1")
        fig2 = empty_figure("Card 2")

    return fig_main, fig1, fig2



def main():
    app.run(host="0.0.0.0", port=8050, debug=False)


if __name__ == "__main__":
    main()
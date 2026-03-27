import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
from tripTimeTracker.db import query_records


# --------------------------------------------------
# Load Data
# --------------------------------------------------
def load_data():
    df = query_records()
    df['time'] = pd.to_datetime(df['time'])
    df['displayName'] = [name.replace('_', ' ') for name in df.name]
    return df


# --------------------------------------------------
# Create Figures
# --------------------------------------------------
def create_timeseries_figure(df):
    """
    Create a time-series plot with one line per 'name'.
    """
    fig = px.line(
        df,
        x="time",
        y="tripTime",
        color="displayName",
        title="Time Series by Name"
    )
    fig.update_layout(
        title='Main Time Series',
        template="plotly_dark",
        paper_bgcolor="#1B2444",
        plot_bgcolor="#1B2444",
        font=dict(color="white"),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig


import dash
from dash import dcc, html
import plotly.graph_objects as go

# Create empty placeholder figure
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


app = dash.Dash(__name__)

# Common card style
CARD_STYLE = {
    "backgroundColor": "#1B2444",
    "padding": "15px",
    "borderRadius": "12px",
    "boxShadow": "0px 4px 12px rgba(0, 0, 0, 0.4)",
    "margin": "10px"
}

app.layout = html.Div(
    style={
        "backgroundColor": "#161D33",
        "height": "100vh",
        "padding": "10px"
    },
    children=[

        # Top Large Card
        html.Div(
            style={**CARD_STYLE, "height": "48vh"},
            children=[
                dcc.Graph(
                    figure=create_timeseries_figure(load_data()),
                    style={"height": "100%"}
                )
            ]
        ),

        # Bottom Row (3 Cards)
        html.Div(
            style={
                "display": "flex",
                "height": "48vh"
            },
            children=[
                html.Div(
                    style={**CARD_STYLE, "flex": "1"},
                    children=[
                        dcc.Graph(
                            figure=empty_figure("Card 1"),
                            style={"height": "100%"}
                        )
                    ]
                ),
                html.Div(
                    style={**CARD_STYLE, "flex": "1"},
                    children=[
                        dcc.Graph(
                            figure=empty_figure("Card 2"),
                            style={"height": "100%"}
                        )
                    ]
                ),
                html.Div(
                    style={**CARD_STYLE, "flex": "1"},
                    children=[
                        dcc.Graph(
                            figure=empty_figure("Card 3"),
                            style={"height": "100%"}
                        )
                    ]
                ),
            ]
        )
    ]
)


def main():
    app.run(host="0.0.0.0", port=8050, debug=False)


if __name__ == "__main__":
    main()
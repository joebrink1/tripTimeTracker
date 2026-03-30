import pandas as pd
import numpy as np
from lightgbm import LGBMRegressor, Booster

DATABASE_NAME = 'oldTrips.db'

from .db import retrieve_tripNames, query_records


def build_lookup_tables(df):

    df = df.copy()
    df["daily_cum"] = df.groupby("date")["tripTime"].cumsum()

    dow_time_avg = df.groupby(["dow", "time"])["tripTime"].mean()
    avg_cum = df.groupby(["dow", "time"])["daily_cum"].mean()

    return dow_time_avg, avg_cum


def create_features(df, dow_time_avg, avg_cum):

    df = df.copy()

    dow_map = {
        "Monday":0, "Tuesday":1, "Wednesday":2,
        "Thursday":3, "Friday":4, "Saturday":5, "Sunday":6
    }
    df["dow_num"] = df["dow"].map(dow_map)

    time_parsed = pd.to_datetime(df["time"], format="%H:%M")
    df["hour"] = time_parsed.dt.hour
    df["minute"] = time_parsed.dt.minute

    df["hour_sin"] = np.sin(2*np.pi*df["hour"]/24)
    df["hour_cos"] = np.cos(2*np.pi*df["hour"]/24)

    df["lag_1"] = df["tripTime"].shift(1)
    df["lag_24"] = df["tripTime"].shift(24)
    df["lag_168"] = df["tripTime"].shift(168)

    df["rolling_mean_3"] = df["tripTime"].rolling(3).mean()
    df["rolling_mean_24"] = df["tripTime"].rolling(24).mean()

    key = list(zip(df["dow"], df["time"]))
    df["dow_time_avg"] = dow_time_avg.reindex(key).values

    df["daily_cum"] = df.groupby("date")["tripTime"].cumsum()
    df["avg_cum"] = avg_cum.reindex(key).values
    df["progress_ratio"] = df["daily_cum"] / df["avg_cum"]

    return df

#TODO: Add in model saving/loading that supports previous epochs
def trainModel(df):

    train_df = df.copy()
    #TODO: Timezone handling - set in env file
    train_df["dt"] = pd.to_datetime(train_df["dt"], unit='s').dt.tz_localize('UTC').dt.tz_convert('America/New_York')
    train_df = train_df.sort_values("dt").reset_index(drop=True)

    dow_time_avg, avg_cum = build_lookup_tables(train_df)
    train_features = create_features(train_df, dow_time_avg, avg_cum)
    train_features = train_features.dropna()

    features = [
        "dow_num",
        "hour",
        #"hour_sin",
        #"hour_cos",
        "lag_1",
        "lag_24",
        "lag_168",
        #"rolling_mean_3",
        #"rolling_mean_24",
        "dow_time_avg"#,
        #"progress_ratio"
    ]

    X_train = train_features[features]
    y_train = train_features["tripTime"]

    model = LGBMRegressor(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=6
    )

    model.fit(X_train, y_train)

    return model


def predict_remaining_day(model, df):
    """
    Extend dataframe to end of last date and predict remaining values.

    Args:
        model: Trained LightGBM model (sklearn API)
        df: DataFrame with columns ["dt","dow","date","time","value"]
        freq: Frequency of future intervals (default 60min)
    
    Returns:
        df_full: DataFrame with historical and predicted values
    """

    df_full = df.copy().sort_values("dt").reset_index(drop=True)
    df_full["dt"] = pd.to_datetime(df_full["dt"], unit='s').dt.tz_localize('UTC').dt.tz_convert('America/New_York')
    df_full = df_full.sort_values("dt").reset_index(drop=True)

    # Identify last timestamp and end of day
    last_partial_dt = df_full["dt"].max()
    end_of_day = last_partial_dt.normalize() + pd.Timedelta(days=1)

    future_times = pd.date_range(
        start=last_partial_dt + pd.Timedelta(minutes=5),
        end=end_of_day,
        freq="5min",
        inclusive="left"
    )

    # Create future dataframe
    future_df = pd.DataFrame({"dt": future_times})
    future_df["dow"] = future_df["dt"].dt.day_name()
    future_df["date"] = future_df["dt"].dt.strftime("%Y-%m-%d")
    future_df["time"] = future_df["dt"].dt.strftime("%H:%M")
    future_df["tripTime"] = np.nan

    # Append to original dataframe
    df_full = pd.concat([df_full, future_df]).sort_values("dt").reset_index(drop=True)

    # Build historical lookup tables from the original df
    df_hist = df.copy()
    df_hist["daily_cum"] = df_hist.groupby("date")["tripTime"].cumsum()
    dow_time_avg = df_hist.groupby(["dow","time"])["tripTime"].mean()
    avg_cum = df_hist.groupby(["dow","time"])["daily_cum"].mean()

    # Features for sequential prediction
    features = [
        "dow_num",
        "hour",
        #"hour_sin",
        #"hour_cos",
        "lag_1",
        "lag_24",
        "lag_168",
        #"rolling_mean_3",
        #"rolling_mean_24",
        "dow_time_avg"#,
        #"progress_ratio"
    ]


    # Sequential prediction for future rows
    for t in future_times:
        df_full_features = create_features(df_full, dow_time_avg, avg_cum)
        row = df_full_features[df_full_features["dt"] == t]
        X_pred = row[features]
        pred = model.predict(X_pred)[0]
        df_full.loc[df_full["dt"] == t, "tripTime"] = pred

    return df_full

import sqlite3

import pandas as pd

def insert_record(tripName,
                  timestamp,
                  dow,
                  date_str,
                  time_str,
                  trip_time,
                  db_path='trips.db'):
    '''
    Docstring Here
    '''
    # Connect to SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create trips table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            dt REAL NOT NULL,
            dow TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            tripTime REAL NOT NULL
        )
    """)
    conn.commit()

    cursor.execute("""
        INSERT INTO trips (name, dt, dow, date, time, tripTime)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        tripName, timestamp, dow, date_str, time_str, trip_time
    ))

    conn.commit()
    conn.close()



def query_records(db_path="trips.db", name=None, date=None, dow=None, time=None):
    """
    Query trip data from SQLite and return a pandas DataFrame.
    
    Parameters:
    - db_path (str): Path to SQLite database file.
    - name (str): Trip name filter (format: "Origin_to_Destination").
    - date (str): Date filter in "YYYY-MM-DD".
    - dow (str): Day of week filter (e.g., "Monday").
    - time (str): Time filter in "HH:MM".
    
    Returns:
    - pandas.DataFrame of matching rows.
    """

    conn = sqlite3.connect(db_path)
    
    # Base query
    query = "SELECT * FROM trips"
    filters = []
    params = []

    if name is not None:
        filters.append("name = ?")
        params.append(name)
    if date is not None:
        filters.append("date = ?")
        params.append(date)
    if dow is not None:
        filters.append("dow = ?")
        params.append(dow)
    if time is not None:
        filters.append("time = ?")
        params.append(time)

    if filters:
        query += " WHERE " + " AND ".join(filters)
    
    query += " ORDER BY dt ASC"  # Always order by timestamp for time series

    # Execute query into pandas DataFrame
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df
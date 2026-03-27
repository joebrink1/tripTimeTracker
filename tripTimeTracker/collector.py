from tripTimeTracker.db import insert_record

from datetime import datetime, timezone
import requests
import json

def apple_maps_route(start, end):
    """
    Get Apple Maps routing response between two coordinates.
    Returns response JSON.
    """

    # Apple epoch: Jan 1, 2001 UTC
    apple_epoch = datetime(2001, 1, 1, tzinfo=timezone.utc)
    now_utc = datetime.now(timezone.utc)

    seconds_since_apple_epoch = int((now_utc - apple_epoch).total_seconds())

    # Time info fields
    timezone_offset_hours = int(abs(datetime.now().astimezone().utcoffset().total_seconds() / 3600))
    hour_of_day = datetime.now().hour
    day_of_week = datetime.now().weekday() + 1  # Apple uses 1–7

    url = "https://maps.apple.com/data/direction"

    payload = {
        "locations": [
            {"location": {"latitude": start['latitude'], "longitude": start['longitude']}},
            {"location": {"latitude": end['latitude'], "longitude": end['longitude']}}
        ],
        "dirflg": "driving",
        "userPreferences": {
            "AvoidHighways": False,
            "AvoidTolls": False
        },
        "clientTimeInfo": {
            "clientRequestTime": seconds_since_apple_epoch,
            "clientTimezoneOffset": timezone_offset_hours,
            "clientHourOfDay": hour_of_day,
            "clientDayOfWeek": day_of_week
        },
        "analyticMetadata": {
            "appIdentifier": "com.apple.MapsWeb",
            "appMajorVersion": "1",
            "appMinorVersion": "1.6.477",
            "isInternalInstall": False,
            "isFromAPI": False,
            "requestTime": {
                "timeRoundedToHour": seconds_since_apple_epoch,
                "timezoneOffsetFromGmtInHours": timezone_offset_hours
            },
            "serviceTag": {"tag": "86fffc2c-1e63-4eee-a08b-f05bce16303d"},
            "hardwareModel": "Windows",
            "osVersion": "Windows NT 10.0",
            "productName": "Windows"
        },
        "dcc": "US"
    }

    headers = {
        "authority": "maps.apple.com",
        "accept": "*/*",
        "accept-language": "en-US",
        "content-type": "application/json",
        "origin": "https://maps.apple.com",
        "referer": "https://maps.apple.com/",
        "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()

    return response.json()

#TODO: Add pydantic route dataclass
def parse_apple_routes(api_response):
    assert api_response['status'] == 'STATUS_SUCCESS'

    routes = api_response['waypointRoute']

    estimatedTimesSeconds = [route['tripTimes']['estimatedSeconds'] for route in routes]

    return min(estimatedTimesSeconds)

def update_db(db_path="trips.db"):
    """
    Updates SQLite database with trip times.
    Each call adds a new row for each trip and optional return trip
    """

    # Current time info
    now = datetime.now()
    days = {1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 4: 'Thursday',
            5: 'Friday', 6: 'Saturday', 7: 'Sunday'}
    timestamp = now.timestamp()
    dow = days[now.isoweekday()]
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H:%M')

    # Load trips
    with open('trips.json', 'r') as f:
        trips = json.load(f)

    for trip in trips:
        # Outbound trip
        trip_time = parse_apple_routes(apple_maps_route(trip['origin'], trip['destination']))
        tripName = f"{trip['origin']['name']}_to_{trip['destination']['name']}"

        insert_record(tripName, timestamp, dow, date_str, time_str, trip_time)

        # Optional return trip
        if trip.get('return', False):
            return_time = parse_apple_routes(apple_maps_route(trip['destination'], trip['origin']))
            returnName = f"{trip['destination']['name']}_to_{trip['origin']['name']}"

            insert_record(returnName, timestamp, dow, date_str, time_str, return_time)

    return timestamp
from datetime import datetime
import json
import os
import re
import webbrowser

from environs import Env
from flask import Flask, request
import pandas as pd
import requests

# === CONFIGURATION ===

env = Env()
env.read_env()
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
START_DATE = os.environ.get("START_DATE")

REDIRECT_URI = "http://localhost:5000/callback"

AUTH_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"
ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"
ACTIVITY_BY_ID_URL = "https://www.strava.com/api/v3/activities/"

CACHE_DIR = "cache"
TOKEN_FILE = "strava_token.json"
ACTIVITIES_FILE = "strava_activities.json"
ACTIVITIES_CSV_FILE = "strava_activities.csv"

# === FLASK APP SETUP ===

app = Flask(__name__)
access_token = None


@app.route("/")
def authorize():
    url = (
        f"{AUTH_URL}?"
        f"client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}"
        f"&approval_prompt=auto&scope=activity:read_all"
    )
    return f'Click here to authorize: <a href="{url}">{url}</a>'


# === TOKEN CACHING ===


def load_token():
    token_path = os.path.join(CACHE_DIR, TOKEN_FILE)
    if os.path.exists(token_path):
        with open(token_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("access_token")
    return None


def save_token(token):
    os.makedirs(CACHE_DIR, exist_ok=True)
    token_path = os.path.join(CACHE_DIR, TOKEN_FILE)
    with open(token_path, "w", encoding="utf-8") as f:
        json.dump({"access_token": token}, f)


# === Handling Activities data ===


def print_activities(activities_json):
    if not activities_json:
        print("No activities found.")
        return

    print("== Your Strava Activities ==")

    dog_counter = 0

    for act in activities_json:
        dog_counter_match = re.search(r"(\d+)\s*dog", act["description"], re.IGNORECASE)
        try:
            dogs_in_activity = int(dog_counter_match.group(1)) if dog_counter_match else 0
        except (IndexError, ValueError):
            dogs_in_activity = 0
        act["dogs_counted"] = dogs_in_activity
        dog_counter += dogs_in_activity
        print(
            f"Activity: {act['name']}, ID: {act['id']}, Date: {act['start_date_local']}, Dogs: {dogs_in_activity}, Description: {act['description']}"
        )
    print(f"Total dog counter across all activities: {dog_counter}")
    print("== End Strava Activities ==")

    os.makedirs(CACHE_DIR, exist_ok=True)
    activities_csv_path= os.path.join(CACHE_DIR, ACTIVITIES_CSV_FILE)
    with open(activities_csv_path, "w", encoding="utf-8") as f:
        pd.DataFrame(activities_json).replace({r'\n': r'\\n'}, regex=True).to_csv(f, index=False)


def read_activities():
    activities_path = os.path.join(CACHE_DIR, ACTIVITIES_FILE)
    if os.path.exists(activities_path):
        with open(activities_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_activities(activities_json):
    os.makedirs(CACHE_DIR, exist_ok=True)
    activities_path = os.path.join(CACHE_DIR, ACTIVITIES_FILE)
    with open(activities_path, "w", encoding="utf-8") as f:
        json.dump(activities_json, f)


def fetch_activities():
    print("\n== Fetching Strava Activities ==")

    headers: dict = {"Authorization": f"Bearer {access_token}"}
    params: dict = {"per_page": 200, "page": 0}

    if START_DATE:
        params["after"] = int(datetime.strptime(START_DATE, "%Y-%m-%d").timestamp())\
        
    all_activities = []

    while True:
        params["page"] += 1
        activities_response: dict = requests.get(
            ACTIVITIES_URL, headers=headers, params=params, timeout=10
        )

        if activities_response.status_code != 200:
            print(f"Failed to fetch activities: {activities_response.text}")
            break

        activities_json = activities_response.json()
        if not activities_json:
            break

        for act in activities_json:
            activity_response: dict = requests.get(
                f"{ACTIVITY_BY_ID_URL}/{act['id']}", headers=headers, timeout=10
            )
            activity_json = activity_response.json()
            summarized_act = {}
            summarized_act["id"] = activity_json.get("id", "")
            summarized_act["name"] = activity_json.get("name", "")
            summarized_act["start_date_local"] = activity_json.get("start_date_local", "")
            summarized_act["distance"] = activity_json.get("distance", "")
            summarized_act["sport_type"] = activity_json.get("sport_type", "")
            summarized_act["description"] = activity_json.get("description", "")
            summarized_act["start_latlng"] = activity_json.get("start_latlng", "")
            print(
                f"Fetched activity {len(all_activities) + 1} description: {summarized_act['name']} on {summarized_act['start_date_local']} with description: {summarized_act["description"]}"
            )
            all_activities.append(summarized_act)

    print(f"Fetched {len(all_activities)} activities.")
    return all_activities


# === Flask app behavior ===


@app.route("/callback")
def callback():
    global access_token
    code = request.args.get("code")
    if not code:
        return "Authorization failed or denied."

    # Exchange code for access token
    token_response = requests.post(
        TOKEN_URL,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )

    if token_response.status_code != 200:
        return f"Token exchange failed: {token_response.text}"

    token_data = token_response.json()
    access_token = token_data["access_token"]

    if access_token:
        save_token(access_token)
        activities_json = fetch_activities()
        save_activities(activities_json)
        print_activities(activities_json)
        return "Authorization complete! You can close this window. Listing activities in your terminal..."
    else:
        return "Authorization failed. Please try again."


def start_auth_flow():
    webbrowser.open("http://localhost:5000/")
    app.run(port=5000)


# === MAIN ENTRY POINT ===

if __name__ == "__main__":
    cached_activities = read_activities()
    if cached_activities:
        print("Using cached activities.")
        print_activities(cached_activities)
    else:
        access_token = load_token()
        if access_token:
            print("Using saved access token.")

            response: dict = requests.get(
                ACTIVITIES_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            if response.status_code == 200:
                activities = fetch_activities()
                save_activities(activities)
                print_activities(activities)
            else:
                print(
                    f"Failed to fetch activities with saved token, requesting new token..."
                )
                start_auth_flow()
        else:
            start_auth_flow()

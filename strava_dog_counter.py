"""
If you write "# dog" to count dogs you've encountered in your
Strava descriptions, this is the app for you 🐶
It fetches all activities, matches , and adds them all up for you.
Bonus CSV output included!
"""

import json
import multiprocessing
import os
import re
import sys
import time
import webbrowser
from datetime import datetime

import pandas as pd
import requests
from environs import Env
from flask import Flask, request

# === CONFIGURATION ===

env = Env()
env.read_env()
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
START_DATE = os.environ.get("START_DATE")

REDIRECT_URI = "http://localhost:3001/callback"

AUTH_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"
ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"
ACTIVITY_BY_ID_URL = "https://www.strava.com/api/v3/activities/"

CACHE_DIR = "cache"
TOKEN_FILE = "strava_token.json"
ACTIVITIES_FILE = "strava_activities.json"
ACTIVITIES_CSV_FILE = "strava_activities.csv"


# === TOKEN CACHING ===


def load_token():
    """Load the access token from the cache if it exists."""
    token_path = os.path.join(CACHE_DIR, TOKEN_FILE)
    if os.path.exists(token_path):
        with open(token_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("access_token")
    return None


def save_token(token):
    """Save the access token to the cache."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    token_path = os.path.join(CACHE_DIR, TOKEN_FILE)
    with open(token_path, "w", encoding="utf-8") as f:
        json.dump({"access_token": token}, f)


# === Handling Activities data ===


def process_activities(activities_json):
    """
    Counts the number of dogs mentioned in activity descriptions and
    exports the data to a CSV file.
    """
    if not activities_json:
        print("No activities found.")
        return

    print("== Your Strava Activities ==")

    dog_counter = 0

    for act in activities_json:
        act.pop("start_date", None)
        try:
            dog_counter_match = re.search(
                r"(\d+)\s*dog", act["description"], re.IGNORECASE
            )
            dogs_in_activity = (
                int(dog_counter_match.group(1)) if dog_counter_match else 0
            )
        except (IndexError, ValueError, TypeError):
            dogs_in_activity = 0
        act["dogs_counted"] = dogs_in_activity
        dog_counter += dogs_in_activity
        print(
            f"Activity: {act['name']}, ID: {act['id']}, Date: {act['start_date_local']}, "
            f"Dogs: {dogs_in_activity}, Description: {act['description']}"
        )
    print(f"Total dog counter across all activities: {dog_counter}")
    print("== End Strava Activities ==")

    with open(ACTIVITIES_CSV_FILE, "w", encoding="utf-8") as f:
        pd.DataFrame(activities_json).replace({r"\n": r"\\n"}, regex=True).to_csv(
            f, index=False
        )


def read_activities():
    """Reads activities stored in the cache."""
    activities_path = os.path.join(CACHE_DIR, ACTIVITIES_FILE)
    if os.path.exists(activities_path):
        with open(activities_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_activities(activities_json):
    """Saves activities to the cache."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    activities_path = os.path.join(CACHE_DIR, ACTIVITIES_FILE)
    with open(activities_path, "w", encoding="utf-8") as f:
        json.dump(activities_json, f)


def latest_start_timestamp_from_activities(cached_activities):
    """Finds the latest start timestamp from cached activities."""
    cached_activities = read_activities()
    latest_start_timestamp = datetime.strptime(
        START_DATE if START_DATE else "2000-01-01", "%Y-%m-%d"
    ).timestamp()

    if cached_activities:
        for act in reversed(cached_activities):
            start_date = act.get("start_date", "")
            if start_date:
                try:
                    # Assumes the last-most activity is the most recent one.
                    # + 1 so that we only fetch activities after the latest one.
                    start_timestamp = (
                        datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%SZ").timestamp()
                        + 1
                    )
                    if start_timestamp > latest_start_timestamp:
                        latest_start_timestamp = start_timestamp
                        break
                except ValueError:
                    print(f"Invalid date format for activity {act['id']}: {start_date}")

    return latest_start_timestamp


def fetch_activities(strava_access_token):
    """Fetches as many activities from Strava API as it can and stores them as JSON in the cache."""
    print("== Fetching Strava Activities ==")

    cached_activities = read_activities()
    latest_start_timestamp = latest_start_timestamp_from_activities(cached_activities)

    headers: dict = {"Authorization": f"Bearer {strava_access_token}"}
    params: dict = {"per_page": 200, "page": 0, "after": int(latest_start_timestamp)}
    print(
        "Fetching activities after "
        f"{datetime.fromtimestamp(latest_start_timestamp).strftime('%Y-%m-%d %H:%M:%S')}"
    )

    all_activities = cached_activities if cached_activities else []
    only_sport_types = env.list("ONLY_SPORT_TYPES", default=[])

    while True:
        params["page"] += 1
        try:
            activities_response: dict = requests.get(
                ACTIVITIES_URL,
                headers=headers,
                params=params,
                timeout=30,
            )
        except requests.RequestException as e:
            print(
                "Failed to fetch activities, try running again later.\n"
                f"Error message: {e}"
            )
            break

        if activities_response.status_code != 200:
            print(
                "Failed to fetch activities due to unexpected status code, "
                f"try running again later.\nError message: {activities_response.text}"
            )
            break

        activities_json = activities_response.json()
        if not activities_json:
            break

        for act in activities_json:
            if only_sport_types:
                if act["sport_type"] not in only_sport_types:
                    continue

            try:
                activity_response: dict = requests.get(
                    f"{ACTIVITY_BY_ID_URL}/{act['id']}", headers=headers, timeout=30
                )
            except requests.RequestException as e:
                print(
                    f"Failed to fetch activity {act["id"]}, "
                    f"try running again later.\nError message: {e}"
                )
                break

            activity_json = activity_response.json()

            # This handles cases where the rate limit has been hit
            if (
                not activity_json
                or not activity_json.get("id", "")
                or not activity_json.get("start_date_local", "")
            ):
                break

            summarized_act = {}
            summarized_act["id"] = activity_json.get("id", "")

            summarized_act["name"] = activity_json.get("name", "")
            summarized_act["start_date_local"] = activity_json.get(
                "start_date_local", ""
            )
            summarized_act["start_date"] = activity_json.get("start_date", "")
            summarized_act["distance"] = activity_json.get("distance", "")
            summarized_act["sport_type"] = activity_json.get("sport_type", "")
            summarized_act["start_latlng"] = activity_json.get("start_latlng", "")
            summarized_act["description"] = activity_json.get("description", "")
            print(
                f"Fetched activity {len(all_activities) + 1} description: {summarized_act['name']} "
                f"on {summarized_act['start_date_local']} with description: "
                f"{summarized_act.get("description")}"
            )
            all_activities.append(summarized_act)

        print(f"Total activities: {len(all_activities)}")
    return all_activities


# === FLASK APP (runs in separate process) ===


def run_auth_server():
    """Runs the Flask server in a separate process."""
    auth_flow_app = Flask(__name__)

    @auth_flow_app.route("/")
    def authorize_auth_flow():
        """Prompts user to authorize this app via Strava authorization page."""
        url = (
            f"{AUTH_URL}?"
            f"client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}"
            f"&approval_prompt=auto&scope=activity:read_all"
        )
        return f'Click here to authorize: <a href="{url}">{url}</a>'

    @auth_flow_app.route("/callback")
    def callback_auth_flow():
        """Handles the callback from Strava after user authorization."""
        code = request.args.get("code")
        if not code:
            return "Authorization failed or denied."

        # Exchange code for access token
        try:
            token_response = requests.post(
                TOKEN_URL,
                data={
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                },
                timeout=30,
            )
        except requests.RequestException:
            return "Token exchange request failed"

        if token_response.status_code != 200:
            return f"Token exchange failed: {token_response.text}"

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        if access_token:
            save_token(access_token)
            return (
                "Authorization complete! You can close this window. "
                "Listing activities in your terminal..."
            )

        return "Authorization failed. Please try again."

    # Run the Flask server
    auth_flow_app.run(port=3001, debug=False, use_reloader=False)


def start_auth_flow():
    """Starts the authorization flow using a separate process."""
    print("Starting authorization flow...")

    # Start Flask server in a separate process
    server_process = multiprocessing.Process(target=run_auth_server)
    server_process.start()

    # Give the server a moment to start
    time.sleep(1)

    # Open browser to start auth flow
    webbrowser.open("http://localhost:3001/")

    # Wait for token to be saved (poll for token file)
    print("Waiting for authorization...")
    timeout = 300  # 5 minutes timeout
    start_time = time.time()

    while time.time() - start_time < timeout:
        if load_token():
            print("Authorization complete!")
            break
        time.sleep(1)
    else:
        print("Authorization timed out.")

    # Terminate the server process
    if server_process.is_alive():
        server_process.terminate()
        server_process.join(timeout=5)
        if server_process.is_alive():
            server_process.kill()


# === MAIN ENTRY POINT ===

if __name__ == "__main__":
    cached_access_token = load_token()
    if cached_access_token:
        print("Using saved access token.")

        try:
            response: dict = requests.get(
                ACTIVITIES_URL,
                headers={"Authorization": f"Bearer {cached_access_token}"},
                timeout=30,
            )
        except requests.RequestException as e:
            print(f"Failed to test saved token: {e}")
            response = None

        if not response or response.status_code != 200:
            print(
                "Failed to fetch activities with saved token, requesting new token..."
            )
            start_auth_flow()
            cached_access_token = load_token()
    else:
        start_auth_flow()
        cached_access_token = load_token()

    if cached_access_token:
        activities = fetch_activities(cached_access_token)
        save_activities(activities)
        process_activities(activities)
        print(f"Activities saved to {ACTIVITIES_CSV_FILE}")
    else:
        print("Failed to obtain access token. Please try again.")
        sys.exit(1)

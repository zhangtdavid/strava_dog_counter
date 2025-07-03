# python3 -m venv .venv
# source .venv/bin/activate
# open the Command Palette and run Python: Select Interpreter and pick .venv/bin/python
# deactivate

import os
import webbrowser
from flask import Flask, request
import requests
from environs import Env
import json
import re

# === CONFIGURATION ===
env = Env()
env.read_env()
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
REDIRECT_URI = 'http://localhost:5000/callback'

# === STEP 1: OAuth Authorization URL ===
AUTH_URL = 'https://www.strava.com/oauth/authorize'
TOKEN_URL = 'https://www.strava.com/oauth/token'
ACTIVITIES_URL = 'https://www.strava.com/api/v3/athlete/activities'
ACTIVITY_BY_ID_URL = 'https://www.strava.com/api/v3/activities/'

# === FLASK APP SETUP ===
app = Flask(__name__)
access_token = None

@app.route('/')
def authorize():
    url = (
        f"{AUTH_URL}?"
        f"client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}"
        f"&approval_prompt=auto&scope=activity:read_all"
    )
    return f'Click here to authorize: <a href="{url}">{url}</a>'

# TOKEN CACHING

TOKEN_FILE = 'strava_token.json'

def load_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            data = json.load(f)
            return data.get('access_token')
    return None

def save_token(token):
    with open(TOKEN_FILE, 'w') as f:
        json.dump({'access_token': token}, f)

# === STEP 3: After OAuth, list activities ===
def list_activities():
    global access_token

    print("\n== Your Strava Activities ==")

    headers:dict = {
      'Authorization': f'Bearer {access_token}'
    }
    params:dict = {
      'per_page': 200,
      'page': 0
    }
    while True:
      params['page'] += 1
      response:dict = requests.get(ACTIVITIES_URL, headers=headers, params=params)
      
      if response.status_code != 200:
        print(f"Failed to fetch activities: {response.text}")
        break
      
      activities = response.json()
      if not activities:
        break

      dog_counter = 0
      
      for act in activities:
        activity_response:dict = requests.get(f"{ACTIVITY_BY_ID_URL}/{act['id']}", headers=headers)
        description = activity_response.json().get('description', 'No description')

        dog_counter_match = re.search(r'\d+\s*dog', description, re.IGNORECASE)
        if dog_counter_match:
          dog_counter += int(dog_counter_match.group(0))
        else:
          print(f"Activity '{act['name']}' on {act['start_date']} has no dog counter in description.")
    print(f"\nTotal dog counter across all activities: {dog_counter}")
    print("\n== End Strava Activities ==")

# === STEP 2: Handle Redirect and Exchange Code ===
@app.route('/callback')
def callback():
    global access_token
    code = request.args.get('code')
    if not code:
        return 'Authorization failed or denied.'

    # Exchange code for access token
    response = requests.post(TOKEN_URL, data={
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code'
    })

    if response.status_code != 200:
        return f"Token exchange failed: {response.text}"

    token_data = response.json()
    access_token = token_data['access_token']

    if access_token:
      save_token(access_token)
      list_activities()
      return 'Authorization complete! You can close this window. Listing activities in your terminal...'
    else:
      return 'Authorization failed. Please try again.'

def start_auth_flow():
    webbrowser.open('http://localhost:5000/')
    app.run(port=5000)

# === MAIN ENTRY POINT ===
if __name__ == '__main__':
    access_token = load_token()
    if access_token:
      print('Using saved access token.')

      response:dict = requests.get(ACTIVITIES_URL, headers={
        'Authorization': f'Bearer {access_token}'
      })
      if response.status_code == 200:
        list_activities()
      else:
        print(f"Failed to fetch activities with saved token, requesting new token...")
        start_auth_flow()
    else:
        start_auth_flow()

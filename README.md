# Strava Dog Counter

If you write `# dog` to count dogs you've encountered in your Strava descriptions, this is the app for you 🐶
It fetches all activities, looks for that line, and adds them all up for you. Bonus CSV output included!

## Requirements

- `python3` (developed with 3.13.3)
- `pip` (developed with 25.0.1)

## Setup

1. Run the following commands in the project directory:
```
python3 -m venv .venv
source .venv/bin/activate
```
2. Followed by:
```
pip install -r requirements.txt
```
3. Create a `.env` file with the following:
```
CLIENT_ID=##########
CLIENT_SECRET=##########
START_DATE=YYYY-MM-DD
ONLY_SPORT_TYPES=...
```
  - `CLIENT_ID` and `CLIENT_SECRET` should be taken from the [My API Application](https://www.strava.com/settings/api) section of your Strava account.
    - For details on how to set this up, check out [Strava's documentation](https://developers.strava.com/docs/getting-started/#account) - you only need to complete part B.
  - `START_DATE` is optional, it's there to only retrieve activities after the specified date. If blank, the start date is 2020-01-01
  - `ONLY_SPORT_TYPES` is optional; if left blank it'll consider all sports. To filter to specific sports, use a comma-separated list like `Run,TrailRun,Hike,VirtualRun,Walk` with values from [Strava's API documentation](https://developers.strava.com/docs/reference/#api-models-SportType)

## Usage

1. Run the script with:
```
python3 strava_dog_counter.py
```
2. It will open up a web page with a hyperlink. Click that link to go to a page that asks you for Strava permissions. You'll need to keep the following checkbox checked: "View data about your private activities"
3. If successful, it will do the following:
  - Output a summary of each activity along with the total number of dogs logged across all activities.
```
Activity: Evening Run, ID: ####, Date: ####-##-##, Dogs: 0, Description: Test
Activity: Afternoon Run, ID: ####, Date: ####-##-##, Dogs: 2, Description: // 2 doggos
Activity: Afternoon Run, ID: ####, Date: ####-##-##, Dogs: 4, Description: Test\n// 4 doggos Test

...

Total dog counter across all activities: 6
```
  - Generate a `strava_activities.csv` file with the following columns:
```
id
name
start_date_local
distance
sport_type
start_latlng
description
dogs_counted
```
  - Generate a `cache` folder with `strava_token.json` (you can ignore this) and `strava_activities.json`, the latter of which is a JSON blob with information about all relevant activities
4. When re-running the script, it will use the cached `cache/strava_activities.json` file to count dogs.
  - If you'd like it to re-fetch all the data, delete `cache/strava_activities.json`

NOTE: Strava [rate limits](https://developers.strava.com/docs/rate-limits/) their API to 200 requests every 15 minutes, with up to 2,000 requests per day, so you may have to re-run the script multiple times accordingly. In this case, the script will pick up where it left off, so it won't re-fetch activities it already fetched.

## Miscellaneous

- If you want to run/debug in VS Code, you may have to open the Command Palette `(CMD/CTRL + SHIFT + P)` and run `Python: Select Interpreter`, then pick `.venv/bin/python`
- To deactivate the virtual environment, run the following. NOTE that you'll have to rerun [step 1 of Setup](#setup) to run the script again.
```
deactivate
```

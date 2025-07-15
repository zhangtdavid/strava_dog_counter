# Strava Dog Counter

If you write `# dog` in your Strava descriptions, this is the app for you 🐶
It fetches all activities, looks for that line, and adds them all up for you. Bonus CSV output included!

## Requirements

- `python3` and `pip`

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
```
  - `CLIENT_ID` and `CLIENT_SECRET` should be taken from the [My API Application](https://www.strava.com/settings/api) section of your Strava account.
    - For details on how to set this up, check out [Strava's documentation](https://developers.strava.com/docs/getting-started/#account) - you only need to complete part B.
  - START_DATE is optional, it's there to only retrieve activities after the specified date

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
4. When re-running the script, it will use the cached `strava_activities.json` file to count dogs.
  - If you'd like it to re-fetch the data, delete `strava_activities.json`

## Miscellaneous

- If you want to run/debug in VS Code, you may have to open the Command Palette `(CMD/CTRL + SHIFT + P)` and run `Python: Select Interpreter`, then pick `.venv/bin/python`
- To deactivate the virtual environment, run the following:
```
deactivate
```
  - NOTE: you'll have to rerun [step 1 of Setup](#setup) to run the script again.

## USER REQUIREMENTS

Filter by sport type
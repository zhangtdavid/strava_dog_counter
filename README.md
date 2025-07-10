# Strava Dog Counter

If you write `# dog` in your Strava descriptions, this is the app for you 🐶
It fetches all activities, looks for that line, and adds them all up for you. Bonus CSV output included!

## Requirements

- `python3` and `pip`

## SETUP

1. Run the following commands in the project directory:
```
python3 -m venv .venv
source .venv/bin/activate
```
2. Followed by:
```
pip install -r requirements.txt
```

## Usage
1. Run the script with:
```
python3 strava_dog_counter.py
```
2. It will open up a web page with a hyperlink. Click that link to go to a page that asks you for Strava permissions. You'll need to keep the following checkbox checked: "View data about your private activities"
3. If successful, it will do the following:
  - Output a summary of each activity along with the total number of dogs logged across all activities.
  - Generate a `cache` folder with `strava_token.json` (you can ignore this) and `strava_activities.json`, the latter of which is a JSON blob with information about all relevant activities
4. When re-running the script, it will use the cached `strava_activities.json` file to count dogs.
  - If you'd like it to re-fetch the data, delete `strava_activities.json`

## Miscellaneous
- If you want to run/debug in VS Code, you may have to open the Command Palette `(CMD/CTRL + SHIFT + P)` and run `Python: Select Interpreter`, then pick `.venv/bin/python`
- To deactivate the virtual environment, run the following:
```
deactivate
```
  - NOTE: you'll have to rerun step 1 to run the script again.

## USER REQUIREMENTS

- id
- start_date_local
- distance
- sport_type
- description
- start_latlng

import requests
from datetime import date, datetime as dt, timedelta, time as t
import time as sleepyTime
import tabulate
import os
from typing import Dict, Any

# --- Configuration ---
# ID for Oslo from bonnetid.no
OSLO_ID = 122
API_TOKEN = "750e83c3-4cc2-4e68-a3ac-add5b747d636"
API_URL_TEMPLATE = "https://api.bonnetid.no/prayertimes/{location_id}/{year}/{month}/{day}/"
SLEEP_SECONDS = 30 
FAJR_AZAN_FILE = "fajrAzan.mp3"
GENERIC_AZAN_FILE = "AzanNotFajr_Safe.mp3" # <-- Updated Filename

# Global state for prayer times and the current date we fetched
current_prayer_times: Dict[str, str] = {}
current_date: date = date.today()

# --- Utility Functions ---

def fetch_prayer_times() -> bool:
    """
    Fetches prayer times for the current_date from the API and updates
    the current_prayer_times global dictionary.
    """
    global current_prayer_times, current_date

    year = current_date.year
    month = current_date.month
    day = current_date.day

    url = API_URL_TEMPLATE.format(location_id=OSLO_ID, year=year, month=month, day=day)
    headers = {'Accept': 'application/json', 'Api-Token': API_TOKEN}

    print(f"\n🕋 Fetching prayer times for: {current_date}")

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() 
        data = response.json()

        if all(key in data for key in ["fajr", "duhr", "asr_2x_shadow", "maghrib", "isha"]):
            current_prayer_times = {
                "Fajr": data["fajr"],
                "Zuhr": data["duhr"], 
                "Asr": data["asr_2x_shadow"],
                "Maghrib": data["maghrib"],
                "Isha": data["isha"]
            }
            return True
        else:
            print("❌ Error: Missing expected keys in API response data.")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Error during API request: {e}")
        return False
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        return False


def get_dt_from_time_str(time_str: str, date_obj: date) -> dt:
    """Combines a 'HH:MM' time string with a date object to create a datetime object."""
    try:
        time_obj = dt.strptime(time_str, "%H:%M").time()
        return dt.combine(date_obj, time_obj)
    except ValueError:
        print(f"⚠️ Warning: Could not parse time string '{time_str}'.")
        return dt.min


def display_prayer_times():
    """Prints the current day's prayer times in a tabulated format."""
    if not current_prayer_times:
        print("No prayer times available to display.")
        return

    table = [["Name", "Time"]]
    for prayer, time in current_prayer_times.items():
        table.append([prayer, time])

    print(f"\n🗓️ Prayer Times for {current_date.strftime('%Y-%m-%d')}:")
    print(tabulate.tabulate(table, headers='firstrow', tablefmt="fancy_grid"))
    print("-" * 40)


def find_next_prayer(now: dt) -> tuple[str, dt, timedelta]:
    """
    Finds the next prayer time after the current moment 'now'.
    Returns the prayer name, its datetime, and the timedelta until it.
    """
    next_prayers_after_now = []

    for name, time_str in current_prayer_times.items():
        prayer_dt = get_dt_from_time_str(time_str, current_date)
        if prayer_dt > now:
            next_prayers_after_now.append((name, prayer_dt))

    if not next_prayers_after_now:
        return "None", dt.min, timedelta.max

    next_prayer_name, next_prayer_dt = min(next_prayers_after_now, key=lambda x: x[1])
    time_until = next_prayer_dt - now

    return next_prayer_name, next_prayer_dt, time_until


def play_azan(prayer_name: str):
    """
    Plays the Azan using the external 'mpg123' command via os.system.
    Requires 'mpg123' to be installed on the system (e.g., DietPi).
    """
    if prayer_name == "Fajr":
        file_path = FAJR_AZAN_FILE
    else:
        file_path = GENERIC_AZAN_FILE # <-- Uses the new filename
        
    print(f"📢 Playing Azan for {prayer_name} via mpg123: {file_path}...")
    try:
        # We run the command and pipe the output to /dev/null to keep the console clean
        # The '&' runs it in the background, preventing the script from blocking.
        os.system(f"mpg123 --buffer 8192 -q '{file_path}' &") 
    except Exception as e:
        print(f"❌ Could not execute mpg123 command. Error: {e}")

# --- Main Logic ---

# 1. Initial Fetch
if fetch_prayer_times():
    display_prayer_times()
else:
    print("🔴 FATAL: Could not retrieve initial prayer times. Exiting.")
    exit()

# 2. Main Loop
while True:
    now = dt.now()

    next_prayer_name, next_prayer_dt, time_until = find_next_prayer(now)

    # --- Handling Day Transition ---
    if next_prayer_name == "None":
        if now.date() > current_date:
            print("\n✨ All prayers for today are complete. Fetching tomorrow's times.")
            current_date = now.date()
            if not fetch_prayer_times():
                print("⚠️ Warning: Failed to fetch tomorrow's times. Trying again in 5 minutes.")
                sleepyTime.sleep(300) 
                continue
            display_prayer_times()
            next_prayer_name, next_prayer_dt, time_until = find_next_prayer(now)
        else:
            tomorrow = dt.combine(current_date + timedelta(days=1), t(0, 0))
            time_until_midnight = tomorrow - now
            print(f"\n💤 Waiting for midnight to fetch tomorrow's times in {time_until_midnight.total_seconds():.0f} seconds.")
            sleepyTime.sleep(min(time_until_midnight.total_seconds(), 300)) 
            continue

    # --- Time Calculation and Display ---
    
    if time_until.total_seconds() < 0:
        time_to_sleep = SLEEP_SECONDS
    else:
        total_seconds = time_until.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)

        time_to_sleep = min(total_seconds - 2, SLEEP_SECONDS)
        time_to_sleep = max(1, time_to_sleep) 

        # Continuous countdown display
        print(f"\r🕐 Current Time: {now.strftime('%H:%M:%S')} | Next Prayer: **{next_prayer_name}** at {next_prayer_dt.strftime('%H:%M')}. Time until: **{hours}h {minutes}m {seconds}s**", end="")

        # --- Azan Trigger ---
        if total_seconds < 30 and total_seconds > 0:
            print(f"\n🚨 Prayer is IMMINENT! ({int(total_seconds)} seconds remaining)")
        
        if total_seconds < 5 and total_seconds > -SLEEP_SECONDS:
            play_azan(next_prayer_name)

    # --- Wait ---
    sleepyTime.sleep(time_to_sleep)

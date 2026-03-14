import logging
import os
import shutil
import subprocess
import sys
import time as sleepy_time
from datetime import date, datetime as dt, timedelta, time as time_of_day
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests
import tabulate


BASE_DIR = Path(__file__).resolve().parent
LOCATION_ID = int(os.getenv("PRAYER_LOCATION_ID", "122"))
API_TOKEN = os.getenv("BONNETID_API_TOKEN", "750e83c3-4cc2-4e68-a3ac-add5b747d636")
API_URL_TEMPLATE = "https://api.bonnetid.no/prayertimes/{location_id}/{year}/{month}/{day}/"
REQUEST_TIMEOUT_SECONDS = int(os.getenv("PRAYER_REQUEST_TIMEOUT", "10"))
POLL_SECONDS = int(os.getenv("PRAYER_POLL_SECONDS", "30"))
FETCH_RETRY_SECONDS = int(os.getenv("PRAYER_FETCH_RETRY_SECONDS", "300"))
IMMINENT_WINDOW_SECONDS = int(os.getenv("PRAYER_IMMINENT_WINDOW_SECONDS", "30"))
TRIGGER_WINDOW_SECONDS = int(os.getenv("PRAYER_TRIGGER_WINDOW_SECONDS", "5"))
AZAN_ASYNC_PLAYBACK = os.getenv("AZAN_ASYNC_PLAYBACK", "0") == "1"
FAJR_AZAN_FILE = BASE_DIR / "fajrAzan.mp3"
GENERIC_AZAN_FILE = BASE_DIR / "Recording.mp3"
EXPECTED_API_FIELDS = {
    "Fajr": "fajr",
    "Zuhr": "duhr",
    "Asr": "asr_2x_shadow",
    "Maghrib": "maghrib",
    "Isha": "isha",
}


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def fetch_prayer_times(session: requests.Session, target_date: date) -> Dict[str, str]:
    url = API_URL_TEMPLATE.format(
        location_id=LOCATION_ID,
        year=target_date.year,
        month=target_date.month,
        day=target_date.day,
    )
    headers = {"Accept": "application/json", "Api-Token": API_TOKEN}

    logging.info("Fetching prayer times for %s", target_date.isoformat())
    response = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()

    missing_keys = [api_key for api_key in EXPECTED_API_FIELDS.values() if api_key not in data]
    if missing_keys:
        raise ValueError(f"Missing expected API fields: {', '.join(missing_keys)}")

    return {
        prayer_name: str(data[api_key])
        for prayer_name, api_key in EXPECTED_API_FIELDS.items()
    }


def load_prayer_times_with_retry(session: requests.Session, target_date: date) -> Dict[str, str]:
    while True:
        try:
            return fetch_prayer_times(session, target_date)
        except requests.RequestException as error:
            logging.warning(
                "Prayer time request failed for %s: %s. Retrying in %s seconds.",
                target_date.isoformat(),
                error,
                FETCH_RETRY_SECONDS,
            )
        except ValueError as error:
            logging.warning(
                "Prayer time data for %s was invalid: %s. Retrying in %s seconds.",
                target_date.isoformat(),
                error,
                FETCH_RETRY_SECONDS,
            )

        sleepy_time.sleep(FETCH_RETRY_SECONDS)


def get_dt_from_time_str(time_str: str, target_date: date) -> dt:
    try:
        parsed_time = dt.strptime(time_str, "%H:%M").time()
    except ValueError as error:
        raise ValueError(f"Could not parse prayer time '{time_str}'") from error
    return dt.combine(target_date, parsed_time)


def display_prayer_times(target_date: date, prayer_times: Dict[str, str]) -> None:
    table = [["Name", "Time"]]
    for prayer_name, prayer_time in prayer_times.items():
        table.append([prayer_name, prayer_time])

    print()
    print(tabulate.tabulate(table, headers="firstrow", tablefmt="fancy_grid"))
    logging.info("Loaded prayer times for %s", target_date.isoformat())


def find_next_prayer(
    now: dt, prayer_times: Dict[str, str], target_date: date
) -> Optional[Tuple[str, dt, timedelta]]:
    upcoming_prayers = []

    for prayer_name, prayer_time in prayer_times.items():
        prayer_dt = get_dt_from_time_str(prayer_time, target_date)
        if prayer_dt > now:
            upcoming_prayers.append((prayer_name, prayer_dt))

    if not upcoming_prayers:
        return None

    next_prayer_name, next_prayer_dt = min(upcoming_prayers, key=lambda item: item[1])
    return next_prayer_name, next_prayer_dt, next_prayer_dt - now


def get_azan_file(prayer_name: str) -> Path:
    if prayer_name == "Fajr":
        return FAJR_AZAN_FILE
    return GENERIC_AZAN_FILE


def play_azan(prayer_name: str) -> bool:
    mpg123_path = shutil.which("mpg123")
    if not mpg123_path:
        logging.error("mpg123 is not installed or not in PATH. Cannot play Azan.")
        return False

    azan_file = get_azan_file(prayer_name)
    if not azan_file.is_file():
        logging.error("Audio file not found for %s: %s", prayer_name, azan_file)
        return False

    logging.info("Playing %s Azan using %s", prayer_name, azan_file.name)
    command = [mpg123_path, str(azan_file)]
    try:
        if AZAN_ASYNC_PLAYBACK:
            subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return True

        completed_process = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if completed_process.returncode != 0:
            logging.error(
                "mpg123 exited with status %s while playing %s.",
                completed_process.returncode,
                azan_file.name,
            )
            return False
    except OSError as error:
        logging.error("Failed to start mpg123: %s", error)
        return False

    return True


def validate_runtime_environment() -> None:
    if not shutil.which("mpg123"):
        logging.warning("mpg123 is not available in PATH. Audio playback will fail until it is installed.")

    for audio_file in (FAJR_AZAN_FILE, GENERIC_AZAN_FILE):
        if not audio_file.is_file():
            logging.warning("Audio file is missing: %s", audio_file)


def seconds_until_midnight(now: dt) -> float:
    tomorrow = dt.combine(now.date() + timedelta(days=1), time_of_day(0, 0))
    return max(1.0, (tomorrow - now).total_seconds())


def run() -> int:
    session = requests.Session()
    validate_runtime_environment()
    loaded_date = date.today()
    prayer_times = load_prayer_times_with_retry(session, loaded_date)
    display_prayer_times(loaded_date, prayer_times)
    last_azan_attempt: Optional[Tuple[date, str]] = None
    last_imminent_prayer: Optional[Tuple[date, str]] = None
    idle_logged_for_date: Optional[date] = None

    while True:
        now = dt.now()

        if now.date() != loaded_date:
            loaded_date = now.date()
            prayer_times = load_prayer_times_with_retry(session, loaded_date)
            display_prayer_times(loaded_date, prayer_times)
            last_azan_attempt = None
            last_imminent_prayer = None
            idle_logged_for_date = None

        next_prayer = find_next_prayer(now, prayer_times, loaded_date)
        if next_prayer is None:
            sleep_seconds = min(seconds_until_midnight(now), float(POLL_SECONDS))
            if idle_logged_for_date != loaded_date:
                logging.info(
                    "All prayers for %s are complete. Waiting %.0f seconds for the next refresh.",
                    loaded_date.isoformat(),
                    sleep_seconds,
                )
                idle_logged_for_date = loaded_date
            sleepy_time.sleep(sleep_seconds)
            continue

        idle_logged_for_date = None

        next_prayer_name, next_prayer_dt, time_until = next_prayer
        total_seconds = int(time_until.total_seconds())
        hours, remainder = divmod(max(total_seconds, 0), 3600)
        minutes, seconds = divmod(remainder, 60)

        status_line = (
            f"\rCurrent Time: {now.strftime('%H:%M:%S')} | "
            f"Next Prayer: {next_prayer_name} at {next_prayer_dt.strftime('%H:%M')} | "
            f"Time until: {hours}h {minutes}m {seconds}s"
        )
        print(status_line, end="", flush=True)

        prayer_key = (loaded_date, next_prayer_name)
        if 0 < total_seconds <= IMMINENT_WINDOW_SECONDS and prayer_key != last_imminent_prayer:
            logging.info(
                "%s is imminent: %s seconds remaining.",
                next_prayer_name,
                total_seconds,
            )
            last_imminent_prayer = prayer_key

        if total_seconds > IMMINENT_WINDOW_SECONDS and prayer_key == last_imminent_prayer:
            last_imminent_prayer = None

        if -POLL_SECONDS < total_seconds <= TRIGGER_WINDOW_SECONDS and prayer_key != last_azan_attempt:
            print()
            play_azan(next_prayer_name)
            last_azan_attempt = prayer_key

        if total_seconds <= 1:
            sleep_seconds = 1.0
        else:
            sleep_seconds = min(float(POLL_SECONDS), max(1.0, time_until.total_seconds() - 1.0))

        sleepy_time.sleep(sleep_seconds)


def main() -> int:
    configure_logging()

    try:
        return run()
    except KeyboardInterrupt:
        print()
        logging.info("Shutdown requested. Exiting cleanly.")
        return 0
    except Exception:
        logging.exception("Fatal error in prayer clock.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

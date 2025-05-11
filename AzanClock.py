import salat
import datetime as dt
import pytz
from pytz import timezone
import tabulate
import time as t
import os

# set up calculation methods
calcMethod = salat.CalculationMethod.ISNA
pt = salat.PrayerTimes(calcMethod, salat.AsrMethod.HANAFI)

# January 1, 2000
date = dt.datetime.today()
print(date.strftime("%d-%m-%Y %H:%M"), calcMethod)

# using Oslo as an example
longitude = 11.1629 # degrees East
latitude = 59.5835 # degrees North
eastern = pytz.timezone('Europe/Oslo')

# calculate times
prayer_times = pt.calc_times(date, eastern, longitude, latitude)

# print in a table
table = [["Name", "Time"]]
for name, time in prayer_times.items():
    readable_time = time.strftime("%H:%M:%S")
    table.append([name, readable_time])
print(tabulate.tabulate(table, headers='firstrow'))
while True:
    # every 5 seconds print how many hours and minutes until the next prayer with name and time
    now = dt.datetime.now(eastern)
    next_prayers=[time for time in prayer_times.values() if time > now]
    if len(next_prayers)==0:
        print("The next prayer is tomorrow!")
        date = dt.datetime.today() + dt.timedelta(days=1) # add a day to the date
        prayer_times = pt.calc_times(date, eastern, longitude, latitude)
        next_prayers=[time for time in prayer_times.values() if time > now]
    time_until_next_prayer = min(next_prayers, key=lambda x: abs(x - now))
    next = time_until_next_prayer - now
    print(next)
    hours, remainder = divmod(next.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    print(f"{hours} hours and {minutes} minutes until the next prayer")
    t.sleep(5)
    # get the name of the next prayer
    next_prayer = [name for name, time in prayer_times.items() if name == min(prayer_times, key=lambda x: abs(prayer_times[x] - dt.datetime.now(eastern)))][0]
    print(f"The next prayer is {next_prayer}, in {next.seconds} seconds")
    # if the next prayer is less than 5 seconds away, dont check date only time, print a message
    if next.seconds < 5:
        print("The next prayer is now!", next.seconds)
        if next_prayer == "fajr":
            os.system("mpg123 " + "fajrAzan.mp3")
            print("Playing Fajr Azan...")
        elif next_prayer == "sunrise":
            print("Fajr time is now over as it is sunrise")
        else:
            os.system("mpg123 " + "Recording.mp3")
            print("Playing Azan...")

import salat
import datetime as dt
import pytz
import tabulate
import time as t
import os

# set up calculation methods
calcMethod = salat.CalculationMethod.ISNA
pt = salat.PrayerTimes(calcMethod, salat.AsrMethod.HANAFI)

# January 1, 2000
date = dt.datetime.today()
print(date.strftime("%d-%m-%Y"), calcMethod)

# using Oslo as an example
longitude = 11.1629 # degrees East
latitude = 59.5835 # degrees North
eastern = pytz.timezone('Europe/Oslo')

# calculate times
prayer_times = pt.calc_times(date, eastern, longitude, latitude)

# print in a table
table = [["Name", "Time"]]
for name, time in prayer_times.items():
    readable_time = time.strftime("%I:%M:%S %p %Z")
    table.append([name, readable_time])
print(tabulate.tabulate(table, headers='firstrow'))

while True:
    # every 5 seconds print how many hours and minutes until the next prayer with name and time
    time_until_next_prayer = min(time - dt.datetime.now(eastern) for time in prayer_times.values())
    hours, remainder = divmod(time_until_next_prayer.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    print(f"{hours} hours and {minutes} minutes until the next prayer")
    t.sleep(3)
    # get the name of the next prayer
    next_prayer = [name for name, time in prayer_times.items() if name == min(prayer_times, key=lambda x: abs(prayer_times[x] - dt.datetime.now(eastern)))][0]
    convert = t.strftime("%I:%M", t.gmtime(time_until_next_prayer.seconds))
    print(f"The next prayer is {next_prayer} in {convert} hours and minutes")
    os.system("mpg123 " + "AzanNotFajr.mp4")
    # if the next prayer is less than 5 seconds away, dont check date only time, print a message
    if time_until_next_prayer.seconds < 5:
        print("The next prayer is now!", time_until_next_prayer.seconds)
        if next_prayer == "fajr":
            os.system("mpg123 " + "fajrAzan.mp4")
            print("Playing Fajr Azan...")
        else:
            os.system("mpg123 " + "AzanNotFajr.mp4")
            print("Playing Azan...")
        
    # if the next prayer is tomorrow, print a message
    if time_until_next_prayer.days > 0:
        print("The next prayer is tomorrow!")
        date = dt.datetime.today() + dt.timedelta(days=1) # add a day to the date
        prayer_times = pt.calc_times(date, eastern, longitude, latitude)


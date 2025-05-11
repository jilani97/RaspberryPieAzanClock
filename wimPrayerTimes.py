import requests
from datetime import date, datetime as dt, timedelta, time as t
import time as sleepyTime
import tabulate
import os

prayerNames = {}
oslo = 122
today = date.today()
day = today.day
month = today.month
year = today.year

def getPrayerTimes():
    global prayerNames
    global today
    global day
    global month
    global year
    day = today.day
    month = today.month
    year = today.year
    url = "https://api.bonnetid.no/prayertimes/{0}/{1}/{2}/{3}/".format(oslo, year, month, day)
    headers = {'Accept': 'application/json', 'Api-Token' : "750e83c3-4cc2-4e68-a3ac-add5b747d636"}
    print("getPrayerTimes:",today)
    response = requests.get(url, headers=headers)
    data = response.json()
    #Prayer times
    Fajr = data["fajr"]
    Zuhr = data["duhr"]
    Asr = data["asr_2x_shadow"]
    Maghrib = data["maghrib"]
    Isha = data["isha"]
    prayerNames = {"Fajr": Fajr, "Zuhr":Zuhr, "Asr":Asr, "Maghrib":Maghrib, "Isha":Isha}

getPrayerTimes()
# print in a table
table = [["Name", "Time"]]
for prayer in prayerNames:
    table.append([prayer, prayerNames[prayer]])
print(tabulate.tabulate(table, headers='firstrow'))

def combineTime(time):
    return dt.combine(date(year,month,day),t(int(time[:2]),int(time[-2:])))
next_prayers = []
while True:
    # every 5 seconds print how many hours and minutes until the next prayer with name and time
    now = dt.now()
    print(now)
    next_prayers=[time for time in prayerNames.values() if combineTime(time) > now]
    if len(next_prayers)==0:
        print("The next prayer is tomorrow!")
        today = date.today() + timedelta(days=1) # add a day to the date
        getPrayerTimes()
        next_prayers=[time for time in prayerNames.values() if combineTime(time) > now]
    time_until_next_prayer = min(next_prayers, key=lambda x: abs(combineTime(x) - now))
    nextP = combineTime(time_until_next_prayer) - now
    print(nextP)
    hours, remainder = divmod(nextP.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    print(f"{hours} hours and {minutes} minutes until the next prayer")
    sleepyTime.sleep(30)
    # get the name of the next prayer
    next_prayer = next(name for name, pTime in prayerNames.items() if pTime == time_until_next_prayer)
    print(f"The next prayer is {next_prayer}, in {nextP.seconds} seconds \n")
    # if the next prayer is less than 5 seconds away, dont check date only time, print a message
    if nextP.seconds < 30:
        print("The next prayer is now!", nextP.seconds)
        if next_prayer == "Fajr":
            os.system("mpg123 " + "fajrAzan.mp3")
            print("Playing Fajr Azan...")
        else:
            os.system("mpg123 " + "Recording.mp3")
            print("Playing Azan...")

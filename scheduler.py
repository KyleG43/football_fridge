from datetime import datetime, timedelta
import os
from dateutil import parser
import requests
from zoneinfo import ZoneInfo

leagues = {
  'mlb': {
    'teams': ['Padres'],
    'url': 'https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard'
  },
  'mls': {
    'teams': ['San Diego FC'],
    'url': 'https://site.api.espn.com/apis/site/v2/sports/soccer/usa.1/scoreboard'
  },
  'nfl': {
    'teams': ['49ers'],
    'url': 'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard'
  }
}

event_length_hours = {
  'mlb': 3,
  'mls': 2.25,
  'nfl': 3.5
}

teams_to_schedule = {}

for league, details in leagues.items():
  if len(details['teams']) > 0:
    response = requests.get(details['url'])
    response.raise_for_status()
    events = response.json()['events']
  
  for team in details['teams']:
    for event in events:
      for competitor in event['competitions'][0]['competitors']:
        if competitor['team']['name'] == team:
          time = parser.isoparse(event['date']).astimezone(ZoneInfo("America/Los_Angeles"))
          if time.date() == datetime.today().date():
            teams_to_schedule[team] = {
              'time': time,
              'league': league,
            }
          break

teams_to_schedule = sorted_events = dict(sorted(teams_to_schedule.items(), key=lambda item: item[1]['time']))

schedule_order = {}
last_time = None
last_league = None
for team, details in teams_to_schedule.items():
  formatted_datetime = details['time'].strftime("%H:%M %Y-%m-%d")
  if len(schedule_order) == 0:
    schedule_order[formatted_datetime] = [team]
  else:
    if details['time'] - last_time <= timedelta(hours = event_length_hours[last_league]):
      schedule_order[last_time.strftime("%H:%M %Y-%m-%d")].append(team)
    else:
      schedule_order[formatted_datetime] = [team]

  last_time = details['time']
  last_league = details['league']

for time, teams in schedule_order.items():
  command_string = 'echo "python ~/src/football_fridge/score_trackers/all_sports.py'
  for team in teams:
    command_string += f" '{team}'"
  command_string += f'" | at {time}'
  os.system(command_string)

exit(0)

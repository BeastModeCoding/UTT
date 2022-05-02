import requests
from chessdotcom import get_tournament_details
from bs4 import BeautifulSoup as BS
import pandas as pd
from datetime import date

#### TO_DO
# 1.Добавить автоматическую проверку на бан
# 2.Добавить функцию единичного суммирования результатов (+запись в файл)

####### Manual settings ########
countEvents = False
# Put here links of excluded events starting after ...live/
excluded_events = []
# ties_for_chart = {'mikechesser':[0,0,0,0,0,2,0,0,0,0,0,0], 'smyslovfan':[0,0,0,0,0,0,0,0,0,0,0,0], 'peterchaplin':[0,0,0,0,0,0,1,0,0,0,0,0]}
################################
lb = {}
awards = [30, 25, 20, 18, 16, 14, 12, 10, 8, 6, 5, 4, 3, 2, 1]
Months = {'Jan':0,'Feb':1,'Mar':2,'Apr':3,'May':4,'Jun':5,'Jul':6,'Aug':7,'Sep':8,'Oct':9,'Nov':10,'Dec':11}
current_month = date.today().month
year = date.today().year
playerDataLen = 5 if countEvents else 4
# Fill list with banned players
banned = []
with open('banned.txt', 'r') as f:
  banned = f.read().splitlines()
# Fill dict with tied and points
tied = {}
with open("tied.txt") as f:
    for line in f:
      key,val = line.split(":")
      tied[key] = int(val.strip())

def update_lb(tnmt):
  query = get_tournament_details(tnmt) 
  query = query.json['tournament']['players'] # Gets a list of dictionaries - {username:place}

  # Remove banned players from the tournament
  query = [player for player in query if player['username'] not in banned]

  for place in range(len(awards)): 
    # print("Place = ", place+1," : ","Name = ", query[place]['username'])
    # Checking if a query[place] finished the tnmt
    if query[place]['status'] != 'withdrew':
      # Get player's points in lb
      players_points = lb.get(query[place]['username'], 0)
      if players_points == 0:
        # print("Not in the list. Adding")
        lb[query[place]['username']] = [0 for i in range(playerDataLen)]  #(!) In range of 5 if counting played in tmnts, otherwise 4 (!)
        # print("Has Points", lb[(query[place]['username'])]['pts'])
      else:
        players_points = players_points[0]
        # print("Has Points:", players_points)

      players_points += awards[place]
      # print("New pts:", players_points)
      lb[query[place]['username']][0] = players_points

      if place+1 == 1:
        lb[query[place]['username']][1] += 1
      elif place+1 == 2:
        lb[query[place]['username']][2] += 1
      elif place+1 == 3:
        lb[query[place]['username']][3] += 1  
  
  # Add +1 participation 
  if countEvents:
    for i in range(len(query)):
      player = lb.get(query[i]['username'], 0)
      if player == 0:
        lb[query[i]['username']] = [0 for i in range(5)]
      lb[query[i]['username']][4] += 1 

def print_lb():
  print("\nCurrent Leaderboard:\n")
  print(lb)

# Sort a dictionary by value then key desc
def sort_dict(dictionary):
  return dict(sorted(dictionary.items(), key=lambda x: (-x[1][0], -x[1][1], -x[1][2], -x[1][3], x[0]) ))

def update_last_tnmt():
  req = requests.get("https://www.chess.com/club/live-tournaments/untitled-tuesday?&page=1")
  html = BS(req.content, 'html.parser')

  events = html.select_one('.tournaments-table-name')   # Gets a list of tags <a> from the page

  url = events.select_one('a').get('href')
  url = url.partition("live/")[2]
  print("Last tnmt:", url)
  update_lb(url)

# Добавить открытие файла (и суммирование результатов)
def form_table(leaderboard, toExcel=False):
  lb = leaderboard.items()
  if countEvents:
    lb = {
    'Player': [player[0] for player in lb],
    'Points': [player[1][0] for player in lb],
    '1st': [player[1][1] for player in lb],
    '2nd': [player[1][2] for player in lb],
    '3rd': [player[1][3] for player in lb],
    'Played': [player[1][4] for player in lb]
    }
  else:
    lb = {
    'Player': [player[0] for player in lb],
    'Points': [player[1][0] for player in lb],
    '1st': [player[1][1] for player in lb],
    '2nd': [player[1][2] for player in lb],
    '3rd': [player[1][3] for player in lb]
    }
  df = pd.DataFrame(lb)
  df.index += 1

  if toExcel:
    df.to_excel('./UTT_LB.xlsx', sheet_name='Leaderboard', index_label="Rank")
    print("Printed to Excel")

  # Print to HTML format
  html_string = '''
    <html>
      <head><title>UTT Leaderboard</title>
      <style>
        @import url('https://fonts.googleapis.com/css2?family=Josefin+Sans:wght@500&family=Supermercado+One&display=swap');
      </style>
      </head>
      <link rel="stylesheet" type="text/css" href="df_style.css"/>
      <body>
        <div class="container">
          <div class="bg"> 
            <img class="logo" src="Utt_logo.png" alt="UTT_logo">
          </div>
          {table}
        </div>
      </body>
    </html>
  '''
  with open('UTT_Leaderboard.html', 'w') as f:
    f.write(html_string.format(table=df.to_html(classes="redTable")))
  print("Printed to HTML")

# Select all tourneys from this year
def select_all_tnmts():
  tnmts = []
  for page in range(3):
    req = requests.get("https://www.chess.com/club/live-tournaments/untitled-tuesday?&page="+str(page+1))
    html = BS(req.content, 'html.parser')

    events = html.select('.tournaments-table-name')   # Gets a list of tags <a> from the page
    dates = html.select('.tournaments-live-date')

    # Select events from year
    for i in range(len(dates)):
      date = int(dates[i].get_text().split(', ')[1])
      if date == year:
        url = events[i].select_one('a').get('href')
        url = url.partition("live/")
        tnmts.append(url[2])
  return tnmts

# Print data of players' points for leaderboard chart
def get_chart_values(player:str):
  points = [0 for i in range(12)]
  total_points = 0
  for page in reversed(range(3)):
    req = requests.get("https://www.chess.com/club/live-tournaments/untitled-tuesday?&page="+str(page+1))
    html = BS(req.content, 'html.parser')

    events = html.select('.tournaments-table-name')   # Gets a list of tags <a> from the page
    dates = html.select('.tournaments-live-date')
    events.reverse()  # Reverse the list to start countig points from the Jan to Dec
    dates.reverse()

    # Select events from year
    for i in range(len(dates)):
      yr = int(dates[i].get_text().split(', ')[1])
      # print("Date:", date)
      month = dates[i].get_text().rsplit()[0]
      # print("Month:", month)
      if yr == year:
        url = events[i].select_one('a').get('href')
        url = url.partition("live/")[2]
        # Do not count event if it's in excluded list
        if url not in excluded_events:
          tnmt_info = get_tournament_details(url)
          tnmt_info = tnmt_info.json['tournament']['players']
          # Remove banned players from the tournament
          for p in tnmt_info:
            if p['username'] in banned:
              tnmt_info.remove(p)

          # found = False 
          for place in range(len(awards)):
            # Checking if a query[place] finished the tnmt
            if tnmt_info[place]['username'] == player and tnmt_info[place]['status'] != 'withdrew':
              # print("Placed:", place+1)
              month_number = Months.get(month)
              # print("Got month:", m)
              total_points += awards[place]
              points[month_number] = total_points
              # print("Points Added:", awards[place])
              # found = True
          # if found == False:
            # print("Not in top-15")
  points = points[:current_month]
  # print(points)
  info = {player : points}
  # print(info)
  return info

def draw_chart_top3(players:list):
  top_3 = {}
  month = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  for p in players:
    top_3.update(get_chart_values(p))
  print("Top-3:\n", top_3)

  df1 = pd.DataFrame(top_3)
  df1.index = month[:current_month]
  df1.to_excel('./Top3.xlsx', sheet_name='Top-3 Chart')
  print("Printed Top-3")

# Correct points for ties
def lb_corrections():
  for player in tied:
    # print(lb.get(player))
    if lb.get(player, 0):
      lb[player][0] += tied[player]
      # print("Added", tied[player], "points")
    else:
      lb[player] = [0 for i in range(playerDataLen)]
      lb[player][0] += tied[player]

def update_all_tnmts():
  # Test for one tourney:
  # links = ['saturday-event---january-1892407']

  links = select_all_tnmts()
  if len(excluded_events) != 0:
    for event in excluded_events:
      print("Removing:", event)
      links.remove(event)
  print("Output:\n")
  if len(links):
    print("Selected tnmts:", len(links))
  else:
    print("Nothing was selected")

  for i in range(len(links)):
    update_lb(links[i])
    print("Tnmts updated:", i+1)  

  print("Last event:", links[0])
  lb_corrections()

# Delete from lb players with 0 points
def remove_zeros(lbrd:dict):
  new_lb = {}
  for k, v in lbrd.items():
    if v[0] != 0:
        new_lb.update({k: v})
  return new_lb

# Returns the number of tnmts a player successfully finished
# def tnmts_played(player:str):
#   played = 0
#   tnmts = select_all_tnmts()
#   for tnmt in tnmts:
#     query = get_tournament_details(tnmt) 
#     query = query.json['tournament']['players'] # Gets a list of dictionaries - {username:place}

#     for pl in range(len(query)):
#       if query[pl]['status'] != 'withdrew':
#         if player == query[pl]['username']:
#           played += 1
#           break
#       query[pl]['username'].append(played)

if __name__ == "__main__":
  update_all_tnmts()
  # update_last_tnmt()
  lb = sort_dict(lb)
  lb = remove_zeros(lb)
  form_table(lb)
  # draw_chart_top3(['mikechesser', 'smyslovfan', 'peterchaplin'])

  ################# NOTES ###############
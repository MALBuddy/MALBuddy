import requests
import re
import pandas as pd
import time
import random


def download_page(url: str) -> str:
    """Returns the contents of the html page of the given URL"""
    response = requests.get(url)
    if response.ok:
        return response.text
    else:
        print(response)
        return None

def download_all_ratings(anime_id: str, num_pages) -> list:
    """Returns all the html pages of user ratings from the given anime"""
    user_page = 0
    pages = []
    print("Successfully loaded pages: : ", end = "")
    for x in range(num_pages):  # first 99 pages of reviews
        url = f"https://myanimelist.net/anime/{anime_id}/anime_title/stats?m=all&show" \
              f"={user_page}.html"
        page = download_page(url)
        if page == None:  # response is not ok so break loop
            break
        else:
            pages.append(page)
            print(f"{x+1},", end="")

        #delay = random.randint(1, 3)
        #time.sleep(delay)  # wait before requesting again

        user_page += 75
    return pages

def parse_users(soup) -> list:
    """Returns all the users from the given html page soup"""
    users = soup.findAll('a', attrs={'class': 'image-member'})
    pat = "[^/]+$"  # character string without '/' at the end of the string

    for i in range(len(users)):
        users[i] = re.findall(pat, users[i].get('href'))[0]
    return users

def parse_ratings(soup) -> list:
    """Retruns all the ratings from the given html page soup"""
    pat = "^.{1,2}$"  # only 1 or 2 character in entire string (the rating the user gave the anime)
    ratings = []
    for x in soup.findAll('td', attrs={'class': 'borderClass ac'}):
        if re.match(pat, x.getText()) != None:
            ratings.append(x.getText())
    return ratings

import requests
import json
import secrets
from MALToken import MALToken
import pandas as pd
import re
import MALScraper
import bs4
import os


def fp_is_okay(fp, folder):
    if folder is not None and not os.path.exists(folder):
        print(f"Error, folder {folder} not found!")
        return False

    if fp is None:  # create filepath to write json
        print("Please give a file name to write to")
        return False
    else:
        return True

class MALBuddy:
    def __init__(self, client_info_fp, token_filepath=None):
        self.token = MALToken(client_info_fp, token_filepath)

    def get_anime_list(self, user: str, limit=500) -> pd.DataFrame:
        """Returns a DataFrame of the given users Animelist

        Keyword Arguments:
            limit -- max number of entries to load from the user's animelist
        """
        url = f"https://api.myanimelist.net/v2/users/{user}/animelist?fields=list_status&limit={limit}"

        resp = requests.get(url, headers={
            "Authorization": f"Bearer {self.token.get_access_token()}"})

        if (resp.ok):
            mal = resp.json()['data']
        else:
            self.token.refresh_token()
            resp = requests.get(url, headers={
                "Authorization": f"Bearer {self.token.get_access_token()}"})
            if (not resp.ok):
                print("Error requesting anime list. Aborting...")
                return

        data = []
        for anime in mal:
            dictionary = anime['node']
            dictionary.update(anime['list_status'])
            data.append(dictionary)

        mal_df = pd.DataFrame(data)
        return mal_df

    def get_token(self) -> MALToken:
        return self.token.get_token()

    def generate_ratings(self, anime_id: str, num_pages=99) -> dict:
        """Webscrapes latest 99 pages of ratings from MAL for the given anime"""
        if num_pages > 99:
            print("Cannot scrape more than 99 pages!")
            return

        pages = MALScraper.download_all_ratings(anime_id, num_pages)
        user_list = []
        rating_list = []
        for page in pages:
            if page == None:
                break
            soup = bs4.BeautifulSoup(page, features='lxml')
            user_list += MALScraper.parse_users(soup)
            rating_list += MALScraper.parse_ratings(soup)

        user_ratings = pd.DataFrame({"user": user_list, 'rating': rating_list})
        user_ratings = user_ratings.drop_duplicates(subset=['user'],
                                                    keep='first')  # drop duplicates, keep most recent
        user_ratings = user_ratings[user_ratings['rating'] != '-']
        user_ratings = user_ratings.astype({'rating': 'int32'})
        user_ratings = user_ratings.reset_index(drop=True)

        return user_ratings.to_dict()

    def generate_and_write_ratings(self, id: str, title: str, fp=None,
                                   folder='anime_ratings',
                                   num_pages=99) -> dict:
        """Web scrapes latest 99 pages of rating from MAL and then writes the data to a
        json file"""

        if not os.path.exists(folder):
            print(f"Error, folder {folder} not found!")
            return {}

        print(f"Downloading ratings for: {title}")
        rating_df = pd.DataFrame(self.generate_ratings(id, num_pages=num_pages))

        if fp is None:  # create filepath to write json
            fp = os.path.join(folder, f'{self.format_title(title)}.json')

        if os.path.exists(fp):  # load ratings that have been previously scraped
            with open(fp, 'r') as file:
                existing_ratings = json.load(file)
                file.close()
            rating_df = pd.concat([rating_df, pd.DataFrame(existing_ratings)])
            rating_df = rating_df.drop_duplicates(subset=['user'], keep='first').reset_index(drop=True)
        
        with open(fp, 'w') as file:
            json.dump(rating_df.to_dict(), file)
        file.close()
        print(f"\nRatings saved to {fp} ")
        return rating_df

    def generate_users(self, anime_id, num_pages=99):
        """Webscrapes latest 99 pages of ratings from MAL for the given anime"""
        if num_pages > 99:
            print("Cannot scrape more than 99 pages!")
            return

        pages = MALScraper.download_all_ratings(anime_id, num_pages)
        user_list = []
        for page in pages:
            if page == None:
                break
            soup = bs4.BeautifulSoup(page, features='lxml')
            user_list += MALScraper.parse_users(soup)

        users = pd.Series(user_list)
        users = users.drop_duplicates(keep='first')  # drop duplicates, keep most recent
        users = users.reset_index(drop=True)

        return users

    def generate_and_write_users(self, id: str, title: str, fp=None,
                                   folder='mal_users',
                                   num_pages=99) -> dict:
        """Web scrapes latest 99 pages of ratings from MAL and then writes the data to a
        json file"""

        if not os.path.exists(folder):
            print(f"Error, folder {folder} not found!")
            return {}

        print(f"Downloading users who watched {title}...")
        users = self.generate_users(id, num_pages=num_pages)

        if fp is None:  # create filepath to write json
            fp = os.path.join(folder, f'{self.format_title(title)}.json')

        if os.path.exists(fp):  # load users that have been previously scraped
            with open(fp, 'r') as file:
                existing_users = json.load(file)
                file.close()
            users = pd.concat([users, pd.Series(existing_users)])
            # remove duplicate users
            users = users.drop_duplicates(keep='first').reset_index(drop=True)

        with open(fp, 'w') as file:
            json.dump(users.to_dict(), file)
        file.close()
        print(f"\nRatings saved to {fp} ")
        return users

    def load_ratings(self, anime: str, folder='anime_ratings') -> pd.DataFrame:
        if os.path.exists(folder):
            save_folder = folder
        else:
            print(f"Error, folder {folder} not found!")
            return

        fp = os.path.join(save_folder, f'{self.format_title(anime)}.json')
        print(fp)

        with open(fp, 'r') as file:
            ratings = json.load(file)
        file.close()
        return pd.DataFrame(ratings)

    def load_users(self, anime: str, folder='mal_users') -> pd.Series:
        if os.path.exists(folder):
            save_folder = folder
        else:
            print(f"Error, folder {folder} not found!")
            return

        fp = os.path.join(save_folder, f'{self.format_title(anime)}.json')
        print(fp)

        with open(fp, 'r') as file:
            users = json.load(file)
        file.close()
        return pd.Series(users)

    def make_users_to_load(self, fp='unloaded_users.json', folder='mal_users'):
        if not os.path.exists(folder):
            print(f"Error, folder {folder} not found!")
            return False
        users = pd.Series()
        for anime_file in os.listdir(folder):
            fp1 = os.path.join(folder, anime_file)
            with open(fp1, 'r') as file:
                users = pd.concat([users, pd.Series(json.load(file))]).drop_duplicates()
            file.close()
        with open(fp, 'w') as file:
            json.dump(users.to_dict(), file)
            file.close()
        return True

    def get_unloaded_users(self, fp='unloaded_users.json'):
        with open(fp,'r') as file:
            users = json.load(file)
        file.close()
        return pd.Series(users)


    def remove_from_user_list(self, user: str, fp='unloaded_users.json'):
        with open(fp,'r') as file:
            users = json.load(file)
            file.close()
        users = pd.Series(users)
        users = users[users != user].to_dict()
        with open(fp,'w+') as file:
            json.dump(users, file)
            file.close()
            return True
        return False


    def load_anime_details(self, id_list: list):
        def genre_from_dict_list(genre_list):
            genres = []
            try:
                for entry in genre_list:
                    genres.append(entry['name'])
                return genres
            except:
                return []


        anime_details = pd.DataFrame(columns=['id','title','main_picture','start_date',
                                              'end_date','genres'])
        for anime_id in id_list:
            url = f"https://api.myanimelist.net/v2/anime/{anime_id}?fields=id,title," \
                  f"start_date,end_date,genres"
            resp = requests.get(url, headers={
                "Authorization": f"Bearer {self.token.get_access_token()}"})
            if (resp.ok):
                anime_details = anime_details.append(pd.Series(resp.json()),
                                                     ignore_index=True)
            else:
                self.token.refresh_token()
                resp = requests.get(url, headers={
                    "Authorization": f"Bearer {self.token.get_access_token()}"})
                if (not resp.ok):
                    print(resp)
                    print(f"Error requesting anime details for id: {anime_id}. "
                          "Aborting...")


        anime_details['genres'] = anime_details['genres'].apply(genre_from_dict_list)

        return anime_details

    def write_anime_df(self, df, fp: str, folder=None, append=False,
                       drop_duplicates=True):
        if not fp_is_okay(fp,folder):
            return False
        if folder is not None:  # create filepath to write json
            fp = os.path.join(folder, fp)

        if append:
            if os.path.exists(fp):
                with open(fp, 'r+') as file:
                    existing_df = json.load(file)
                    existing_df = pd.concat([pd.DataFrame(existing_df),
                                           df]).reset_index(
                        drop=True).drop_duplicates(subset='id')
                    existing_df = existing_df.to_dict()
                    file.close()
                with open(fp, 'w+') as file:
                    json.dump(existing_df, file)
                    file.close()
                    return True
        else:
            with open(fp, 'w+') as file:
                json.dump(df.to_dict(), file)
                file.close()
                return True



    def write_user_df(self, df, fp: str, folder=None, append=False,
                       drop_duplicates=True):
        if not fp_is_okay(fp, folder):
            print("fp does not exist")
            return False

        if folder is not None:  # create filepath to write json
            fp = os.path.join(folder, fp)
        if append:
            if os.path.exists(fp):
                with open(fp, 'r+') as file:
                    existing_df = json.load(file)
                    existing_df = pd.concat([pd.DataFrame(existing_df),
                                           df]).reset_index(
                        drop=True).drop_duplicates(subset=['user','movie_id'])
                    existing_df = existing_df.to_dict()
                    file.close()
                with open(fp, 'w+') as file:
                    json.dump(existing_df, file)
                    file.close()
                    return True
        else:
            with open(fp, 'w+') as file:
                json.dump(df.to_dict(), file)
                file.close()
                return True

    def read_json(self, fp):
        with open(fp, 'r') as file:
            df = json.load(file)
            file.close()
        return df


    def format_title(self, title: str) -> str:
        """removes any non-word symbols and replaces any spaces with underscores """
        title = re.sub(' ', '_', title.lower())
        title = re.sub('\W', '', title)
        return title

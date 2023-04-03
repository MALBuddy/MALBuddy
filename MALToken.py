import requests
import json
import secrets


class MALToken:
    """Represents  a user token for interacting with the MAL api"""

    def __init__(self, client_info_fp, token_filepath=None):
        self.token = None
        self.token_filepath = token_filepath
        
        with open(client_info_fp) as file:
            client_info = json.load(file)
            self.client_id = client_info['CLIENT_ID']
            self.client_secret = client_info['CLIENT_SECRET']

        if self.token_filepath is not None:
            self.refresh_token(token_filepath)

    def get_token(self) -> dict:
        return self.token

    def get_access_token(self) -> str:
        return self.token['access_token']

    def refresh_token(self, token_fp="token.json"):
        """Refreshes the given token"""
        with open(token_fp, 'r') as file:
            token = json.load(file)
        url = "https://myanimelist.net/v1/oauth2/token"
        data = {
            'client_id': self.client_id,
            'client_secret':self.client_secret,
            'grant_type': "refresh_token",
            'refresh_token': token['refresh_token']
        }

        resp = requests.post(url, data=data)
        if(resp.ok):
            new_token = resp.json()
            resp.close()
            self.token = new_token
        else:
            print(f"Error refreshing token: {resp}")




    def generate_user_token(self, token_fp="token.json"):
        if self.token is not None:
            print("Token already generated!")
            return

        """Generates a new token for accessing MAL api and writes it to given file path"""

        def get_new_code_verifier() -> str:
            """creates new code verifier (needed to request a token)"""
            token = secrets.token_urlsafe(100)
            return token[:128]  # 128 characters

        def print_auth_link(code_verifier: str):
            """print link for user to get authorization code"""
            url = f'https://myanimelist.net/v1/oauth2/authorize?response_type=code&client_id={self.client_id}&code_challenge={code_verifier}'
            print(f"Authorize Here : {url}\n")

        def request_user_token(auth_code: str, code_verifier: str) -> dict:
            """makes the request to MAL for the token"""
            url = 'https://myanimelist.net/v1/oauth2/token'
            data = {"client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": auth_code,
                    "code_verifier": code_verifier,
                    "grant_type": "authorization_code"
                    }
            resp = requests.post(url, data=data)
            resp.raise_for_status()  # if 400 reponse error may need to generate new code with above link
            token = resp.json()
            resp.close()
            print('Token generated')

            with open(token_fp, 'w') as file:
                json.dump(token, file, indent=4)
                print(f'Token saved in "{token_fp}"')
            return token

        def print_user_info(access_token: str):
            """prints the """
            url = 'https://api.myanimelist.net/v2/users/@me'
            response = requests.get(url, headers={
                'Authorization': f'Bearer {access_token}'
            })

            response.raise_for_status()
            user = response.json()
            response.close()

            print(f"\n>>> Greetings {user['name']}! <<<")

        code_verifier = get_new_code_verifier()
        print_auth_link(code_verifier)

        authorisation_code = input("You must first authenticate your MyAnimeList account in order to to make requests on behalf of the account. Please login to this link and copy-paste the Authorisation Code and the end of the url.  (eg http://localhost/oauth?code={YOUR AUTHORIZATION CODE}: ").strip()
        self.token = request_user_token(authorisation_code, code_verifier)

        print_user_info(self.token['access_token'])

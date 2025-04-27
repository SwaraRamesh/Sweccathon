import requests
import base64
import json
from flask import current_app

class SpotifyClient:
    def __init__(self):
        self.client_id = "YOUR_CLIENT_ID"
        self.client_secret = "YOUR_CLIENT_SECRET"
        self.redirect_uri = "http://localhost:5000/callback"
        self.token_url = "https://accounts.spotify.com/api/token"
        self.api_base_url = "https://api.spotify.com/v1"
        self.access_token = None

    def get_auth_url(self):
        scopes = "user-modify-playback-state user-read-playback-state"
        auth_url = (
            f"https://accounts.spotify.com/authorize?response_type=code"
            f"&client_id={self.client_id}&scope={scopes}&redirect_uri={self.redirect_uri}"
        )
        return auth_url

    def get_tokens(self, code):
        auth_str = f"{self.client_id}:{self.client_secret}"
        headers = {
            "Authorization": "Basic " + base64.b64encode(auth_str.encode()).decode()
        }
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        response = requests.post(self.token_url, headers=headers, data=payload)
        response_data = response.json()
        self.access_token = response_data.get("access_token")

    def adjust_music(self, activity_score):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        if activity_score > 0.7:
            playlist_id = "energetic_playlist_id"
            volume = 80
        elif activity_score > 0.3:
            playlist_id = "medium_playlist_id"
            volume = 65
        else:
            playlist_id = "focus_playlist_id"
            volume = 50

        # Adjust volume
        requests.put(
            f"{self.api_base_url}/me/player/volume?volume_percent={volume}",
            headers=headers,
        )
        # Change playlist
        requests.put(
            f"{self.api_base_url}/me/player/play",
            headers=headers,
            json={"context_uri": f"spotify:playlist:{playlist_id}"},
        )
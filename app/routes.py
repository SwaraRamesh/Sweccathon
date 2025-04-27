from flask import Flask, request, jsonify, redirect, url_for
from .spotify_client import SpotifyClient

app = Flask(__name__)
spotify = SpotifyClient()

@app.route('/auth')
def auth():
    auth_url = spotify.get_auth_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    spotify.get_tokens(code)
    return jsonify({"message": "Authentication successful!"})

@app.route('/api/activity', methods=['POST'])
def activity():
    data = request.json
    activity_score = (data.get('keyCount', 0) + data.get('mouseCount', 0)) / 100
    spotify.adjust_music(activity_score)
    return jsonify({"status": "success", "activity_score": activity_score})
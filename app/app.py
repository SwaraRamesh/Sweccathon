from flask import Flask, request, redirect, session, render_template, jsonify, url_for
import os
import time
import json
import requests
from urllib.parse import urlencode
import secrets
import base64

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Spotify API credentials - store these securely in production
CLIENT_ID = "YOUR_SPOTIFY_CLIENT_ID"
CLIENT_SECRET = "YOUR_SPOTIFY_CLIENT_SECRET"
REDIRECT_URI = "http://localhost:5000/callback"
SCOPE = "user-read-private user-read-email user-modify-playback-state user-read-playback-state playlist-read-private streaming"

# Routes
@app.route('/')
def index():
    if 'access_token' not in session:
        return render_template('login.html')
    else:
        return render_template('dashboard.html')

@app.route('/login')
def login():
    # Generate a random state value for security
    state = secrets.token_hex(16)
    session['state'] = state
    
    # Create authorization URL
    auth_params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': REDIRECT_URI,
        'state': state,
        'scope': SCOPE
    }
    
    auth_url = f"https://accounts.spotify.com/authorize?{urlencode(auth_params)}"
    return redirect(auth_url)

@app.route('/callback')
def callback():
    # Verify state parameter
    if request.args.get('state') != session.get('state'):
        return jsonify({"error": "State mismatch"}), 403
    
    # Check for error in callback
    if 'error' in request.args:
        return jsonify({"error": request.args.get('error')}), 400
    
    # Exchange code for access token
    if 'code' in request.args:
        code = request.args.get('code')
        
        # Prepare token exchange request
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI
        }
        
        # Base64 encode client ID and secret
        client_creds = f"{CLIENT_ID}:{CLIENT_SECRET}"
        client_creds_b64 = base64.b64encode(client_creds.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {client_creds_b64}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        # Make token request
        token_response = requests.post(
            'https://accounts.spotify.com/api/token',
            data=token_data,
            headers=headers
        )
        
        if token_response.status_code == 200:
            token_info = token_response.json()
            session['access_token'] = token_info['access_token']
            session['refresh_token'] = token_info['refresh_token']
            session['token_expiry'] = time.time() + token_info['expires_in']
            
            # Get user info
            headers = {'Authorization': f"Bearer {session['access_token']}"}
            user_response = requests.get('https://api.spotify.com/v1/me', headers=headers)
            
            if user_response.status_code == 200:
                session['user_info'] = user_response.json()
                return redirect(url_for('index'))
            
        return jsonify({"error": "Failed to get token"}), 400
    
    return jsonify({"error": "No code provided"}), 400

@app.route('/api/playlists')
def get_playlists():
    if 'access_token' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    # Check if token is expired
    if time.time() > session.get('token_expiry', 0):
        refresh_token()
    
    headers = {'Authorization': f"Bearer {session['access_token']}"}
    response = requests.get('https://api.spotify.com/v1/me/playlists', headers=headers)
    
    if response.status_code == 200:
        return jsonify(response.json())
    
    return jsonify({"error": "Failed to fetch playlists"}), response.status_code

@app.route('/api/player/play', methods=['POST'])
def play():
    if 'access_token' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    # Check if token is expired
    if time.time() > session.get('token_expiry', 0):
        refresh_token()
    
    data = request.json
    context_uri = data.get('context_uri')  # Spotify URI for playlist, album, etc.
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}",
        'Content-Type': 'application/json'
    }
    
    payload = {}
    if context_uri:
        payload['context_uri'] = context_uri
    
    response = requests.put(
        'https://api.spotify.com/v1/me/player/play',
        headers=headers,
        data=json.dumps(payload)
    )
    
    if response.status_code in [200, 204]:
        return jsonify({"status": "success"})
    
    return jsonify({"error": f"Failed to play", "status_code": response.status_code}), response.status_code

@app.route('/api/player/pause', methods=['PUT'])
def pause():
    if 'access_token' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    # Check if token is expired
    if time.time() > session.get('token_expiry', 0):
        refresh_token()
    
    headers = {'Authorization': f"Bearer {session['access_token']}"}
    response = requests.put('https://api.spotify.com/v1/me/player/pause', headers=headers)
    
    if response.status_code in [200, 204]:
        return jsonify({"status": "success"})
    
    return jsonify({"error": "Failed to pause"}), response.status_code

@app.route('/api/player/volume', methods=['PUT'])
def set_volume():
    if 'access_token' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    # Check if token is expired
    if time.time() > session.get('token_expiry', 0):
        refresh_token()
    
    volume = request.json.get('volume', 50)  # Default to 50% volume
    
    headers = {'Authorization': f"Bearer {session['access_token']}"}
    response = requests.put(
        f'https://api.spotify.com/v1/me/player/volume?volume_percent={volume}',
        headers=headers
    )
    
    if response.status_code in [200, 204]:
        return jsonify({"status": "success"})
    
    return jsonify({"error": "Failed to set volume"}), response.status_code

@app.route('/api/activity', methods=['POST'])
def process_activity():
    if 'access_token' not in session:
        return jsonify({"error": "Not logged in"}), 401

    # Get activity data from request
    activity_data = request.json
    key_count = activity_data.get('keyCount', 0)
    mouse_count = activity_data.get('mouseCount', 0)
    
    # Calculate activity level (simple algorithm)
    # This could be made more sophisticated
    activity_level = min(1.0, (key_count + mouse_count/10) / 100)
    
    # Store activity level in session
    session['activity_level'] = activity_level
    
    # Adjust music based on activity level
    adjust_music_for_activity(activity_level)
    
    return jsonify({
        "status": "success",
        "activity_level": activity_level
    })

def adjust_music_for_activity(activity_level):
    """Adjust music based on activity level"""
    if 'access_token' not in session:
        return
    
    # Check if token is expired
    if time.time() > session.get('token_expiry', 0):
        refresh_token()
    
    headers = {'Authorization': f"Bearer {session['access_token']}"}
    
    # Set volume based on activity level
    volume = int(50 + (activity_level * 30))  # Scale between 50-80%
    requests.put(
        f'https://api.spotify.com/v1/me/player/volume?volume_percent={volume}',
        headers=headers
    )
    
    # Could also switch playlists based on activity level
    # This would require predefined playlist IDs

def refresh_token():
    """Refresh the access token"""
    if 'refresh_token' not in session:
        return False
    
    refresh_token = session['refresh_token']
    
    # Prepare token refresh request
    token_data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    
    # Base64 encode client ID and secret
    client_creds = f"{CLIENT_ID}:{CLIENT_SECRET}"
    client_creds_b64 = base64.b64encode(client_creds.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {client_creds_b64}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    # Make token request
    token_response = requests.post(
        'https://accounts.spotify.com/api/token',
        data=token_data,
        headers=headers
    )
    
    if token_response.status_code == 200:
        token_info = token_response.json()
        session['access_token'] = token_info['access_token']
        session['token_expiry'] = time.time() + token_info['expires_in']
        
        # May also get a new refresh token
        if 'refresh_token' in token_info:
            session['refresh_token'] = token_info['refresh_token']
        
        return True
    
    return False

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)




// static/js/app.js

document.addEventListener('DOMContentLoaded', function() {
    // Initialize variables
    let keyCount = 0;
    let mouseCount = 0;
    let activityLevel = 0;
    let isAutoMode = true;
    let updateFrequency = 30; // seconds
    let activityThreshold = 5;
    let adjustVolumeEnabled = true;
    let changePlaylistEnabled = false;
    let currentPlaylistId = null;
    let playlists = [];
    let updateTimer;

    // DOM elements
    const activityBar = document.getElementById('activityBar');
    const keystrokeCount = document.getElementById('keystrokeCount');
    const mouseCountElement = document.getElementById('mouseCount');
    const playBtn = document.getElementById('playBtn');
    const pauseBtn = document.getElementById('pauseBtn');
    const volumeSlider = document.getElementById('volumeSlider');
    const volumeValue = document.getElementById('volumeValue');
    const playlistContainer = document.getElementById('playlistContainer');
    const activityThresholdSlider = document.getElementById('activityThreshold');
    const thresholdValue = document.getElementById('thresholdValue');
    const updateFrequencySelect = document.getElementById('updateFrequency');
    const adjustVolumeCheckbox = document.getElementById('adjustVolume');
    const changePlaylistCheckbox = document.getElementById('changePlaylist');
    const modeButtons = document.querySelectorAll('.mode-btn');
    const trackName = document.getElementById('trackName');
    const artistName = document.getElementById('artistName');
    const albumArt = document.getElementById('albumArt');

    // Track keypresses
    document.addEventListener('keydown', function() {
        keyCount++;
        updateActivityIndicators();
    });

    // Track mouse movement
    document.addEventListener('mousemove', function() {
        mouseCount++;
        updateActivityIndicators();
    });

    // Initialize the UI
    function init() {
        // Load playlists
        fetchPlaylists();
        
        // Set up event listeners
        setupEventListeners();
        
        // Start activity monitoring
        startActivityMonitoring();
    }

    // Fetch user playlists from Spotify
    function fetchPlaylists() {
        fetch('/api/playlists')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to fetch playlists');
                }
                return response.json();
            })
            .then(data => {
                playlists = data.items || [];
                renderPlaylists();
            })
            .catch(error => {
                console.error('Error:', error);
                playlistContainer.innerHTML = '<p>Failed to load playlists. Please try again.</p>';
            });
    }

    // Render playlists in the UI
    function renderPlaylists() {
        if (playlists.length === 0) {
            playlistContainer.innerHTML = '<p>No playlists found.</p>';
            return;
        }

        let html = '';
        playlists.forEach(playlist => {
            const imageUrl = playlist.images && playlist.images.length > 0 
                ? playlist.images[0].url 
                : '';
            
            html += `
                <div class="playlist-item" data-id="${playlist.id}" data-uri="${playlist.uri}">
                    <div class="playlist-img" style="background-image: url('${imageUrl}')"></div>
                    <div class="playlist-info">
                        <h3>${playlist.name}</h3>
                        <p>${playlist.tracks.total} tracks</p>
                    </div>
                </div>
            `;
        });

        playlistContainer.innerHTML = html;

        // Add click event to playlists
        document.querySelectorAll('.playlist-item').forEach(item => {
            item.addEventListener('click', function() {
                const playlistId = this.dataset.id;
                const playlistUri = this.dataset.uri;
                
                // Mark as active
                document.querySelectorAll('.playlist-item').forEach(pl => {
                    pl.classList.remove('active');
                });
                this.classList.add('active');
                
                // Play this playlist
                currentPlaylistId = playlistId;
                playPlaylist(playlistUri);
            });
        });
    }

    // Set up event listeners
    function setupEventListeners() {
        // Play button
        playBtn.addEventListener('click', function() {
            if (currentPlaylistId) {
                const playlistItem = document.querySelector(`.playlist-item[data-id="${currentPlaylistId}"]`);
                if (playlistItem) {
                    playPlaylist(playlistItem.dataset.uri);
                }
            } else {
                alert('Please select a playlist first');
            }
        });

        // Pause button
        pauseBtn.addEventListener('click', function() {
            pausePlayback();
        });

        // Volume slider
        volumeSlider.addEventListener('input', function() {
            const volume = this.value;
            volumeValue.textContent = `${volume}%`;
            setVolume(volume);
        });

        // Activity threshold slider
        activityThresholdSlider.addEventListener('input', function() {
            activityThreshold = this.value;
            thresholdValue.textContent = activityThreshold;
        });

        // Update frequency select
        updateFrequencySelect.addEventListener('change', function() {
            updateFrequency = parseInt(this.value);
            resetActivityMonitoring();
        });

        // Adjust volume checkbox
        adjustVolumeCheckbox.addEventListener('change', function() {
            adjustVolumeEnabled = this.checked;
        });

        // Change playlist checkbox
        changePlaylistCheckbox.addEventListener('change', function() {
            changePlaylistEnabled = this.checked;
        });

        // Mode buttons
        modeButtons.forEach(button => {
            button.addEventListener('click', function() {
                modeButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');
                isAutoMode = this.dataset.mode === 'auto';
            });
        });
    }

    // Update activity indicators in the UI
    function updateActivityIndicators() {
        keystrokeCount.textContent = keyCount;
        mouseCountElement.textContent = mouseCount;
    }

    // Start activity monitoring
    function startActivityMonitoring() {
        // Clear any existing timer
        if (updateTimer) {
            clearInterval(updateTimer);
        }

        // Set up new timer
        updateTimer = setInterval(() => {
            // Calculate activity level
            const normalizedKeyCount = Math.min(keyCount / (activityThreshold * 20), 1);
            const normalizedMouseCount = Math.min(mouseCount / (activityThreshold * 100), 1);
            activityLevel = (normalizedKeyCount * 0.7) + (normalizedMouseCount * 0.3);

            // Update activity bar
            activityBar.style.width = `${activityLevel * 100}%`;

            // Send activity data to server
            if (isAutoMode) {
                sendActivityData();
            }

            // Reset counts
            keyCount = 0;
            mouseCount = 0;
        }, updateFrequency * 1000);
    }

    // Reset activity monitoring (when frequency changes)
    function resetActivityMonitoring() {
        clearInterval(updateTimer);
        startActivityMonitoring();
    }

    // Send activity data to server
    function sendActivityData() {
        fetch('/api/activity', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                keyCount: keyCount,
                mouseCount: mouseCount,
                activityLevel: activityLevel
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to send activity data');
            }
            return response.json();
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }

    // Play a playlist
    function playPlaylist(playlistUri) {
        fetch('/api/player/play', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                context_uri: playlistUri
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to play playlist');
            }
            return response.json();
        })
        .then(() => {
            // Update UI to show playing state
            updateNowPlaying();
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to play playlist. Make sure Spotify is open on your device.');
        });
    }

    // Pause playback
    function pausePlayback() {
        fetch('/api/player/pause', {
            method: 'PUT'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to pause playback');
            }
            return response.json();
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }

    // Set volume
    function setVolume(volume) {
        fetch('/api/player/volume', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                volume: parseInt(volume)
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to set volume');
            }
            return response.json();
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }

    // Update now playing information
    function updateNowPlaying() {
        // In a real implementation, we would fetch the currently playing track
        // This is a simplified version for the hackathon
        // You would need to implement a /api/player/current-track endpoint

        // For now, we'll just update the UI with placeholder data
        trackName.textContent = "Now Playing";
        artistName.textContent = "Spotify Artist";
        
        // Set a timer to periodically update the now playing info
        setInterval(() => {
            // In a real implementation, this would fetch current track data
        }, 5000);
    }

    // Initialize the app
    init();
});
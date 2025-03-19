import os
import json
import re
import requests
import uuid
import datetime
import threading
import time

# Data paths
ANIME_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'anime')
COVERS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'covers')

# Ensure directories exist
os.makedirs(ANIME_DATA_PATH, exist_ok=True)
os.makedirs(COVERS_PATH, exist_ok=True)

# Anime offline database URL
ANIME_DB_URL = "https://raw.githubusercontent.com/manami-project/anime-offline-database/master/anime-offline-database.json"
ANIME_DB_LOCAL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'anime-offline-database.json')

# Get anime list
def get_anime_list(sort='alpha', search=''):
    anime_list = []
    
    # Get all anime files
    for filename in os.listdir(ANIME_DATA_PATH):
        if filename.endswith('.json'):
            with open(os.path.join(ANIME_DATA_PATH, filename), 'r') as f:
                anime_data = json.load(f)
                
                # Apply search filter if provided
                if search:
                    # Try to match with regex
                    try:
                        pattern = re.compile(search, re.IGNORECASE)
                        
                        # Check title
                        if not pattern.search(anime_data.get('title', '')):
                            # Check alternative titles
                            alt_titles = anime_data.get('alternative_titles', [])
                            if not any(pattern.search(title) for title in alt_titles):
                                # Check genres
                                genres = anime_data.get('genres', [])
                                if not any(pattern.search(genre) for genre in genres):
                                    # No match, skip this anime
                                    continue
                    except re.error:
                        # If regex is invalid, fall back to simple substring search
                        search_lower = search.lower()
                        
                        # Check title
                        if search_lower not in anime_data.get('title', '').lower():
                            # Check alternative titles
                            alt_titles = anime_data.get('alternative_titles', [])
                            if not any(search_lower in title.lower() for title in alt_titles):
                                # Check genres
                                genres = anime_data.get('genres', [])
                                if not any(search_lower in genre.lower() for genre in genres):
                                    # No match, skip this anime
                                    continue
                
                anime_list.append({
                    'id': anime_data.get('id', ''),
                    'title': anime_data.get('title', ''),
                    'cover': anime_data.get('cover', ''),
                    'genres': anime_data.get('genres', []),
                    'description': anime_data.get('description', ''),
                    'score': anime_data.get('average_score', 0),
                    'is_r18': anime_data.get('is_r18', False)
                })
    
    # Sort the list
    if sort == 'alpha':
        anime_list.sort(key=lambda x: x['title'].lower())
    elif sort == 'score':
        anime_list.sort(key=lambda x: x['score'], reverse=True)
    elif sort == 'genre':
        anime_list.sort(key=lambda x: ','.join(x['genres']))
    
    return anime_list

# Get anime details
def get_anime_details(anime_id):
    anime_file = os.path.join(ANIME_DATA_PATH, f'{anime_id}.json')
    if os.path.exists(anime_file):
        with open(anime_file, 'r') as f:
            return json.load(f)
    return None

# Download and process anime offline database
def update_anime_offline_database():
    try:
        # Download the database
        response = requests.get(ANIME_DB_URL)
        if response.status_code == 200:
            # Save the database locally
            with open(ANIME_DB_LOCAL, 'wb') as f:
                f.write(response.content)
            
            # Process the database
            process_anime_offline_database()
            return True
        else:
            print(f"Failed to download anime offline database: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"Error updating anime offline database: {e}")
        return False

# Process anime offline database
def process_anime_offline_database():
    if not os.path.exists(ANIME_DB_LOCAL):
        print("Anime offline database not found")
        return False
    
    try:
        # Load the database
        with open(ANIME_DB_LOCAL, 'r') as f:
            anime_db = json.load(f)
        
        # Process each anime
        for anime_entry in anime_db.get('data', []):
            anime_id = str(uuid.uuid5(uuid.NAMESPACE_URL, anime_entry.get('sources', [''])[0]))
            
            # Check if anime already exists
            anime_file = os.path.join(ANIME_DATA_PATH, f'{anime_id}.json')
            if os.path.exists(anime_file):
                # Update existing anime
                with open(anime_file, 'r') as f:
                    anime_data = json.load(f)
                
                # Update fields from database
                anime_data['title'] = anime_entry.get('title', anime_data.get('title', ''))
                anime_data['alternative_titles'] = anime_entry.get('synonyms', anime_data.get('alternative_titles', []))
                anime_data['genres'] = anime_entry.get('tags', anime_data.get('genres', []))
                anime_data['episodes'] = anime_entry.get('episodes', anime_data.get('episodes', 0))
                anime_data['status'] = anime_entry.get('status', anime_data.get('status', ''))
                anime_data['type'] = anime_entry.get('type', anime_data.get('type', ''))
                anime_data['sources'] = anime_entry.get('sources', anime_data.get('sources', []))
                anime_data['updated_at'] = datetime.datetime.now().isoformat()
                anime_data['is_r18'] = 'Hentai' in anime_data['genres'] or anime_data.get('is_r18', False)
                
                # Save updated anime data
                with open(anime_file, 'w') as f:
                    json.dump(anime_data, f, indent=4)
            else:
                # Create new anime entry
                anime_data = {
                    'id': anime_id,
                    'title': anime_entry.get('title', ''),
                    'alternative_titles': anime_entry.get('synonyms', []),
                    'genres': anime_entry.get('tags', []),
                    'description': '',
                    'episodes': anime_entry.get('episodes', 0),
                    'status': anime_entry.get('status', ''),
                    'type': anime_entry.get('type', ''),
                    'sources': anime_entry.get('sources', []),
                    'cover': '',
                    'cover_url': anime_entry.get('picture', ''),
                    'characters': [],
                    'relations': [],
                    'watch_order': {
                        'prequels': [],
                        'sequels': []
                    },
                    'scores': {
                        'kitsu': None,
                        'anilist': None,
                        'mal': None
                    },
                    'average_score': 0,
                    'is_r18': 'Hentai' in anime_entry.get('tags', []),
                    'created_at': datetime.datetime.now().isoformat(),
                    'updated_at': datetime.datetime.now().isoformat(),
                    'fetched_metadata': False
                }
                
                # Save new anime data
                with open(anime_file, 'w') as f:
                    json.dump(anime_data, f, indent=4)
                
                # Queue for metadata fetching
                queue_metadata_fetch(anime_id)
            
            # Download cover if available
            if anime_entry.get('picture'):
                download_anime_cover(anime_id, anime_entry['picture'])
        
        return True
    
    except Exception as e:
        print(f"Error processing anime offline database: {e}")
        return False

# Download anime cover
def download_anime_cover(anime_id, cover_url):
    try:
        # Check if cover already exists
        cover_file = os.path.join(COVERS_PATH, f'anime_{anime_id}.jpg')
        if os.path.exists(cover_file):
            return
        
        # Download cover
        response = requests.get(cover_url, stream=True)
        if response.status_code == 200:
            with open(cover_file, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            
            # Update anime data with local cover path
            anime_file = os.path.join(ANIME_DATA_PATH, f'{anime_id}.json')
            if os.path.exists(anime_file):
                with open(anime_file, 'r') as f:
                    anime_data = json.load(f)
                
                anime_data['cover'] = f'/data/covers/anime_{anime_id}.jpg'
                
                with open(anime_file, 'w') as f:
                    json.dump(anime_data, f, indent=4)
    
    except Exception as e:
        print(f"Error downloading cover for anime {anime_id}: {e}")

# Queue anime for metadata fetching
def queue_metadata_fetch(anime_id):
    # In a real application, this would add the anime ID to a queue
    # For simplicity, we'll fetch metadata immediately
    fetch_anime_metadata(anime_id)

# Fetch anime metadata from external APIs
def fetch_anime_metadata(anime_id):
    anime_file = os.path.join(ANIME_DATA_PATH, f'{anime_id}.json')
    if not os.path.exists(anime_file):
        return False
    
    with open(anime_file, 'r') as f:
        anime_data = json.load(f)
    
    # Get anime title
    title = anime_data.get('title', '')
    if not title:
        return False
    
    # Fetch from Kitsu
    kitsu_data = fetch_from_kitsu(title)
    if kitsu_data:
        anime_data['scores']['kitsu'] = kitsu_data.get('score')
        
        # Update description if empty
        if not anime_data['description'] and 'description' in kitsu_data:
            anime_data['description'] = kitsu_data['description']
        
        # Update characters if empty
        if not anime_data['characters'] and 'characters' in kitsu_data:
            anime_data['characters'] = kitsu_data['characters']
        
        # Update relations if empty
        if not anime_data['relations'] and 'relations' in kitsu_data:
            anime_data['relations'] = kitsu_data['relations']
    
    # Fetch from AniList
    anilist_data = fetch_from_anilist(title)
    if anilist_data:
        anime_data['scores']['anilist'] = anilist_data.get('score')
        
        # Update description if empty
        if not anime_data['description'] and 'description' in anilist_data:
            anime_data['description'] = anilist_data['description']
        
        # Update characters if empty
        if not anime_data['characters'] and 'characters' in anilist_data:
            anime_data['characters'] = anilist_data['characters']
        
        # Update relations if empty
        if not anime_data['relations'] and 'relations' in anilist_data:
            anime_data['relations'] = anilist_data['relations']
    
    # Fetch from MAL
    mal_data = fetch_from_mal(title)
    if mal_data:
        anime_data['scores']['mal'] = mal_data.get('score')
        
        # Update description if empty
        if not anime_data['description'] and 'description' in mal_data:
            anime_data['description'] = mal_data['description']
        
        # Update characters if empty
        if not anime_data['characters'] and 'characters' in mal_data:
            anime_data['characters'] = mal_data['characters']
        
        # Update relations if empty
        if not anime_data['relations'] and 'relations' in mal_data:
            anime_data['relations'] = mal_data['relations']
        
        # Update watch order if available
        if 'watch_order' in mal_data:
            anime_data['watch_order'] = mal_data['watch_order']
    
    # Calculate average score
    scores = [s for s in [
        anime_data['scores']['kitsu'],
        anime_data['scores']['anilist'],
        anime_data['scores']['mal']
    ] if s is not None]
    
    if scores:
        anime_data['average_score'] = sum(scores) / len(scores)
    
    # Mark as fetched
    anime_data['fetched_metadata'] = True
    anime_data['updated_at'] = datetime.datetime.now().isoformat()
    
    # Save updated anime data
    with open(anime_file, 'w') as f:
        json.dump(anime_data, f, indent=4)
    
    return True

# Fetch from Kitsu API
def fetch_from_kitsu(title):
    try:
        # This is a simplified mock implementation
        # In a real application, you would make actual API calls to Kitsu
        
        # Simulate API response
        return {
            'score': 7.5,
            'description': 'Description from Kitsu API',
            'characters': [
                {
                    'id': str(uuid.uuid4()),
                    'name': 'Character 1',
                    'image': '',
                    'role': 'Main'
                },
                {
                    'id': str(uuid.uuid4()),
                    'name': 'Character 2',
                    'image': '',
                    'role': 'Supporting'
                }
            ],
            'relations': [
                {
                    'id': str(uuid.uuid4()),
                    'title': 'Related Anime 1',
                    'relation_type': 'sequel'
                }
            ]
        }
    except Exception as e:
        print(f"Error fetching from Kitsu: {e}")
        return None

# Fetch from AniList API
def fetch_from_anilist(title):
    try:
        # This is a simplified mock implementation
        # In a real application, you would make actual API calls to AniList
        
        # Simulate API response
        return {
            'score': 8.2,
            'description': 'Description from AniList API',
            'characters': [
                {
                    'id': str(uuid.uuid4()),
                    'name': 'Character 1',
                    'image': '',
                    'role': 'Main'
                },
                {
                    'id': str(uuid.uuid4()),
                    'name': 'Character 3',
                    'image': '',
                    'role': 'Supporting'
                }
            ],
            'relations': [
                {
                    'id': str(uuid.uuid4()),
                    'title': 'Related Anime 2',
                    'relation_type': 'prequel'
                }
            ]
        }
    except Exception as e:
        print(f"Error fetching from AniList: {e}")
        return None

# Fetch from MAL API
def fetch_from_mal(title):
    try:
        # This is a simplified mock implementation
        # In a real application, you would make actual API calls to MAL
        
        # Simulate API response
        return {
            'score': 7.8,
            'description': 'Description from MAL API',
            'characters': [
                {
                    'id': str(uuid.uuid4()),
                    'name': 'Character 1',
                    'image': '',
                    'role': 'Main'
                },
                {
                    'id': str(uuid.uuid4()),
                    'name': 'Character 4',
                    'image': '',
                    'role': 'Supporting'
                }
            ],
            'relations': [
                {
                    'id': str(uuid.uuid4()),
                    'title': 'Related Anime 3',
                    'relation_type': 'side_story'
                }
            ],
            'watch_order': {
                'prequels': ['Related Anime 2'],
                'sequels': ['Related Anime 1'],
                'watch_order_prequels': ['Related Anime 2'],
                'watch_order_sequels': ['Related Anime 1', 'Related Anime 3']
            }
        }
    except Exception as e:
        print(f"Error fetching from MAL: {e}")
        return None

# Start anime database updater thread
def start_anime_updater():
    def updater_thread():
        while True:
            print("Updating anime offline database...")
            update_anime_offline_database()
            
            # Wait for 24 hours before updating again
            time.sleep(24 * 60 * 60)
    
    # Start the updater thread
    thread = threading.Thread(target=updater_thread)
    thread.daemon = True
    thread.start()

# Initialize anime database updater
start_anime_updater()
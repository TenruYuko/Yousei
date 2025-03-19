import os
import json
import re
import requests
import uuid
import datetime
from flask import session
from werkzeug.utils import secure_filename

# Data paths
MANGA_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'manga')
COVERS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'covers')

# Ensure directories exist
os.makedirs(MANGA_DATA_PATH, exist_ok=True)
os.makedirs(COVERS_PATH, exist_ok=True)

# Get manga list
def get_manga_list(sort='alpha', search=''):
    manga_list = []
    
    # Get all manga files
    for filename in os.listdir(MANGA_DATA_PATH):
        if filename.endswith('.json'):
            with open(os.path.join(MANGA_DATA_PATH, filename), 'r') as f:
                manga_data = json.load(f)
                
                # Apply search filter if provided
                if search:
                    # Try to match with regex
                    try:
                        pattern = re.compile(search, re.IGNORECASE)
                        
                        # Check title
                        if not pattern.search(manga_data.get('title', '')):
                            # Check alternative titles
                            alt_titles = manga_data.get('alternative_titles', [])
                            if not any(pattern.search(title) for title in alt_titles):
                                # Check genres
                                genres = manga_data.get('genres', [])
                                if not any(pattern.search(genre) for genre in genres):
                                    # No match, skip this manga
                                    continue
                    except re.error:
                        # If regex is invalid, fall back to simple substring search
                        search_lower = search.lower()
                        
                        # Check title
                        if search_lower not in manga_data.get('title', '').lower():
                            # Check alternative titles
                            alt_titles = manga_data.get('alternative_titles', [])
                            if not any(search_lower in title.lower() for title in alt_titles):
                                # Check genres
                                genres = manga_data.get('genres', [])
                                if not any(search_lower in genre.lower() for genre in genres):
                                    # No match, skip this manga
                                    continue
                
                manga_list.append({
                    'id': manga_data.get('id', ''),
                    'title': manga_data.get('title', ''),
                    'cover': manga_data.get('cover', ''),
                    'genres': manga_data.get('genres', []),
                    'description': manga_data.get('description', ''),
                    'score': manga_data.get('average_score', 0),
                    'is_r18': manga_data.get('is_r18', False)
                })
    
    # Sort the list
    if sort == 'alpha':
        manga_list.sort(key=lambda x: x['title'].lower())
    elif sort == 'score':
        manga_list.sort(key=lambda x: x['score'], reverse=True)
    elif sort == 'genre':
        manga_list.sort(key=lambda x: ','.join(x['genres']))
    
    return manga_list

# Get manga details
def get_manga_details(manga_id):
    manga_file = os.path.join(MANGA_DATA_PATH, f'{manga_id}.json')
    if os.path.exists(manga_file):
        with open(manga_file, 'r') as f:
            return json.load(f)
    return None

# Process manga from MangaDex index
def process_manga_from_index(index_data):
    for manga_entry in index_data:
        manga_id = manga_entry.get('id')
        if not manga_id:
            continue
        
        # Check if manga already exists
        manga_file = os.path.join(MANGA_DATA_PATH, f'{manga_id}.json')
        if os.path.exists(manga_file):
            # Update existing manga
            with open(manga_file, 'r') as f:
                manga_data = json.load(f)
            
            # Update fields from index
            manga_data['title'] = manga_entry.get('title', manga_data.get('title', ''))
            manga_data['description'] = manga_entry.get('description', manga_data.get('description', ''))
            manga_data['cover_url'] = manga_entry.get('cover_url', manga_data.get('cover_url', ''))
            
            # Save updated manga data
            with open(manga_file, 'w') as f:
                json.dump(manga_data, f, indent=4)
        else:
            # Create new manga entry
            manga_data = {
                'id': manga_id,
                'title': manga_entry.get('title', ''),
                'description': manga_entry.get('description', ''),
                'cover_url': manga_entry.get('cover_url', ''),
                'alternative_titles': [],
                'genres': [],
                'volumes': [],
                'is_r18': False,
                'scores': {
                    'kitsu': None,
                    'anilist': None,
                    'mal': None
                },
                'average_score': 0,
                'created_at': datetime.datetime.now().isoformat(),
                'updated_at': datetime.datetime.now().isoformat(),
                'fetched_metadata': False
            }
            
            # Save new manga data
            with open(manga_file, 'w') as f:
                json.dump(manga_data, f, indent=4)
            
            # Queue for metadata fetching
            queue_metadata_fetch(manga_id)
        
        # Download cover if available
        if manga_entry.get('cover_url'):
            download_manga_cover(manga_id, manga_entry['cover_url'])

# Download manga cover
def download_manga_cover(manga_id, cover_url):
    try:
        # Check if cover already exists
        cover_file = os.path.join(COVERS_PATH, f'{manga_id}.jpg')
        if os.path.exists(cover_file):
            return
        
        # Download cover
        response = requests.get(cover_url, stream=True)
        if response.status_code == 200:
            with open(cover_file, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            
            # Update manga data with local cover path
            manga_file = os.path.join(MANGA_DATA_PATH, f'{manga_id}.json')
            if os.path.exists(manga_file):
                with open(manga_file, 'r') as f:
                    manga_data = json.load(f)
                
                manga_data['cover'] = f'/data/covers/{manga_id}.jpg'
                
                with open(manga_file, 'w') as f:
                    json.dump(manga_data, f, indent=4)
    
    except Exception as e:
        print(f"Error downloading cover for manga {manga_id}: {e}")

# Queue manga for metadata fetching
def queue_metadata_fetch(manga_id):
    # In a real application, this would add the manga ID to a queue
    # For simplicity, we'll fetch metadata immediately
    fetch_manga_metadata(manga_id)

# Fetch manga metadata from external APIs
def fetch_manga_metadata(manga_id):
    manga_file = os.path.join(MANGA_DATA_PATH, f'{manga_id}.json')
    if not os.path.exists(manga_file):
        return False
    
    with open(manga_file, 'r') as f:
        manga_data = json.load(f)
    
    # Get manga title
    title = manga_data.get('title', '')
    if not title:
        return False
    
    # Fetch from Kitsu
    kitsu_data = fetch_from_kitsu(title)
    if kitsu_data:
        manga_data['scores']['kitsu'] = kitsu_data.get('score')
        
        # Update genres if empty
        if not manga_data['genres'] and 'genres' in kitsu_data:
            manga_data['genres'] = kitsu_data['genres']
        
        # Update alternative titles if empty
        if not manga_data['alternative_titles'] and 'alternative_titles' in kitsu_data:
            manga_data['alternative_titles'] = kitsu_data['alternative_titles']
        
        # Update description if empty
        if not manga_data['description'] and 'description' in kitsu_data:
            manga_data['description'] = kitsu_data['description']
        
        # Check for R18 content
        if 'is_r18' in kitsu_data:
            manga_data['is_r18'] = kitsu_data['is_r18']
    
    # Fetch from AniList
    anilist_data = fetch_from_anilist(title)
    if anilist_data:
        manga_data['scores']['anilist'] = anilist_data.get('score')
        
        # Update genres if empty
        if not manga_data['genres'] and 'genres' in anilist_data:
            manga_data['genres'] = anilist_data['genres']
        
        # Update alternative titles if empty
        if not manga_data['alternative_titles'] and 'alternative_titles' in anilist_data:
            manga_data['alternative_titles'] = anilist_data['alternative_titles']
        
        # Update description if empty
        if not manga_data['description'] and 'description' in anilist_data:
            manga_data['description'] = anilist_data['description']
        
        # Check for R18 content
        if 'is_r18' in anilist_data:
            manga_data['is_r18'] = manga_data['is_r18'] or anilist_data['is_r18']
    
    # Fetch from MAL
    mal_data = fetch_from_mal(title)
    if mal_data:
        manga_data['scores']['mal'] = mal_data.get('score')
        
        # Update genres if empty
        if not manga_data['genres'] and 'genres' in mal_data:
            manga_data['genres'] = mal_data['genres']
        
        # Update alternative titles if empty
        if not manga_data['alternative_titles'] and 'alternative_titles' in mal_data:
            manga_data['alternative_titles'] = mal_data['alternative_titles']
        
        # Update description if empty
        if not manga_data['description'] and 'description' in mal_data:
            manga_data['description'] = mal_data['description']
    
    # Calculate average score
    scores = [s for s in [
        manga_data['scores']['kitsu'],
        manga_data['scores']['anilist'],
        manga_data['scores']['mal']
    ] if s is not None]
    
    if scores:
        manga_data['average_score'] = sum(scores) / len(scores)
    
    # Mark as fetched
    manga_data['fetched_metadata'] = True
    manga_data['updated_at'] = datetime.datetime.now().isoformat()
    
    # Save updated manga data
    with open(manga_file, 'w') as f:
        json.dump(manga_data, f, indent=4)
    
    return True

# Fetch from Kitsu API
def fetch_from_kitsu(title):
    try:
        # This is a simplified mock implementation
        # In a real application, you would make actual API calls to Kitsu
        
        # Simulate API response
        return {
            'score': 7.5,
            'genres': ['Action', 'Adventure', 'Fantasy'],
            'alternative_titles': ['Alternative Title 1', 'Alternative Title 2'],
            'description': 'Description from Kitsu API',
            'is_r18': False
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
            'genres': ['Action', 'Adventure', 'Fantasy', 'Drama'],
            'alternative_titles': ['Alternative Title 1', 'Alternative Title 3'],
            'description': 'Description from AniList API',
            'is_r18': False
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
            'genres': ['Action', 'Adventure', 'Fantasy', 'Shounen'],
            'alternative_titles': ['Alternative Title 1', 'Alternative Title 4'],
            'description': 'Description from MAL API'
        }
    except Exception as e:
        print(f"Error fetching from MAL: {e}")
        return None

# Search character by regex
def search_character_by_regex(query, type='manga'):
    results = []
    
    try:
        pattern = re.compile(query, re.IGNORECASE)
        
        # Search all manga/anime for matching characters
        data_path = MANGA_DATA_PATH if type == 'manga' else os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            'data', 
            'anime'
        )
        
        for filename in os.listdir(data_path):
            if filename.endswith('.json'):
                with open(os.path.join(data_path, filename), 'r') as f:
                    data = json.load(f)
                    
                    # Check if the data has characters
                    if 'characters' in data:
                        for character in data['characters']:
                            if pattern.search(character.get('name', '')):
                                results.append({
                                    'id': character.get('id', ''),
                                    'name': character.get('name', ''),
                                    'image': character.get('image', ''),
                                    'source_id': data.get('id', ''),
                                    'source_title': data.get('title', '')
                                })
        
        # Limit results
        return results[:20]
    
    except re.error:
        # If regex is invalid, fall back to simple substring search
        query_lower = query.lower()
        
        # Search all manga/anime for matching characters
        data_path = MANGA_DATA_PATH if type == 'manga' else os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            'data', 
            'anime'
        )
        
        for filename in os.listdir(data_path):
            if filename.endswith('.json'):
                with open(os.path.join(data_path, filename), 'r') as f:
                    data = json.load(f)
                    
                    # Check if the data has characters
                    if 'characters' in data:
                        for character in data['characters']:
                            if query_lower in character.get('name', '').lower():
                                results.append({
                                    'id': character.get('id', ''),
                                    'name': character.get('name', ''),
                                    'image': character.get('image', ''),
                                    'source_id': data.get('id', ''),
                                    'source_title': data.get('title', '')
                                })
        
        # Limit results
        return results[:20]
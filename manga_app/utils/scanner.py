import os
import json
import time
import threading
import requests
import uuid
import datetime

# Data paths
MANGA_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'manga')
ANIME_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'anime')

# Hakuneko MangaDex index file path (mock path)
MANGADEX_INDEX_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'mangadex_index.json')

# Ensure directories exist
os.makedirs(MANGA_DATA_PATH, exist_ok=True)
os.makedirs(ANIME_DATA_PATH, exist_ok=True)

# Start scanner thread
def start_scanner_thread():
    def scanner():
        while True:
            print("Starting manga and anime scan...")
            
            # Scan manga
            scan_manga()
            
            # Scan anime
            scan_anime()
            
            # Wait for 1 hour before scanning again
            time.sleep(60 * 60)
    
    # Start the scanner thread
    scanner()

# Scan manga
def scan_manga():
    try:
        # Check if MangaDex index exists
        if not os.path.exists(MANGADEX_INDEX_PATH):
            # For demonstration, create a mock index
            create_mock_mangadex_index()
        
        # Load MangaDex index
        with open(MANGADEX_INDEX_PATH, 'r') as f:
            mangadex_index = json.load(f)
        
        # Process each manga in the index
        from utils.manga import process_manga_from_index
        process_manga_from_index(mangadex_index)
        
        print(f"Processed {len(mangadex_index)} manga from MangaDex index")
    
    except Exception as e:
        print(f"Error scanning manga: {e}")

# Scan anime
def scan_anime():
    try:
        # Update anime offline database
        from utils.anime import update_anime_offline_database
        update_anime_offline_database()
        
        print("Updated anime database")
    
    except Exception as e:
        print(f"Error scanning anime: {e}")

# Create mock MangaDex index for demonstration
def create_mock_mangadex_index():
    mock_index = []
    
    # Create 10 mock manga entries
    for i in range(1, 11):
        manga_id = str(uuid.uuid4())
        
        mock_index.append({
            'id': manga_id,
            'title': f'Mock Manga {i}',
            'description': f'This is a mock manga #{i} for demonstration purposes.',
            'cover_url': f'https://via.placeholder.com/200x300?text=Manga+{i}'
        })
    
    # Save mock index
    os.makedirs(os.path.dirname(MANGADEX_INDEX_PATH), exist_ok=True)
    with open(MANGADEX_INDEX_PATH, 'w') as f:
        json.dump(mock_index, f, indent=4)
    
    print("Created mock MangaDex index for demonstration")
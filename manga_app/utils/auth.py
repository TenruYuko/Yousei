import os
import json
import hashlib
import secrets
import uuid
import re
import datetime
from flask import session, redirect, url_for, flash, request
from functools import wraps

# User data path
USER_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'users')

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# User registration
def register_user(username, email, password):
    # Validate input
    if not username or not email or not password:
        return False
    
    # Check if username or email already exists
    if user_exists(username, email):
        return False
    
    # Create user ID
    user_id = str(uuid.uuid4())
    
    # Hash password
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    # Generate verification token
    verification_token = secrets.token_urlsafe(32)
    
    # Create user data
    user_data = {
        'user_id': user_id,
        'username': username,
        'display_name': username,
        'email': email,
        'password_hash': password_hash,
        'created_at': datetime.datetime.now().isoformat(),
        'verified': False,
        'verification_token': verification_token,
        'profile': {
            'bio': '',
            'profile_picture': '',
            'banner': '',
            'favorites': {
                'manga': [],
                'anime': [],
                'manga_characters': [],
                'anime_characters': []
            },
            'top_favorites': {
                'manga': {'gold': None, 'silver': None, 'bronze': None},
                'anime': {'gold': None, 'silver': None, 'bronze': None},
                'manga_characters': {'gold': None, 'silver': None, 'bronze': None},
                'anime_characters': {'gold': None, 'silver': None, 'bronze': None}
            },
            'lists': {
                'manga': {
                    'reading': [],
                    'completed': [],
                    'planning': []
                },
                'anime': {
                    'watching': [],
                    'completed': [],
                    'planning': []
                }
            },
            'public': True,
            'custom_css': '',
            'theme': 'default'
        },
        'social': {
            'friends': [],
            'friend_requests': {
                'sent': [],
                'received': []
            },
            'notifications': []
        }
    }
    
    # Save user data
    save_user_data(user_id, user_data)
    
    # Send verification email (mock function)
    send_verification_email(email, verification_token)
    
    return True

# Check if user exists
def user_exists(username, email):
    # Check all user files
    for filename in os.listdir(USER_DATA_PATH):
        if filename.endswith('.json'):
            with open(os.path.join(USER_DATA_PATH, filename), 'r') as f:
                user_data = json.load(f)
                if user_data.get('username') == username or user_data.get('email') == email:
                    return True
    return False

# Save user data
def save_user_data(user_id, user_data):
    os.makedirs(USER_DATA_PATH, exist_ok=True)
    with open(os.path.join(USER_DATA_PATH, f'{user_id}.json'), 'w') as f:
        json.dump(user_data, f, indent=4)

# Send verification email (mock function)
def send_verification_email(email, token):
    # In a real application, this would send an actual email
    print(f"Sending verification email to {email} with token {token}")

# Authenticate user
def authenticate_user(email, password):
    # Hash password
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    # Check all user files
    for filename in os.listdir(USER_DATA_PATH):
        if filename.endswith('.json'):
            with open(os.path.join(USER_DATA_PATH, filename), 'r') as f:
                user_data = json.load(f)
                if user_data.get('email') == email and user_data.get('password_hash') == password_hash:
                    # Check if user is verified
                    if not user_data.get('verified', False):
                        return False
                    
                    # Set session
                    session['user_id'] = user_data['user_id']
                    session['username'] = user_data['username']
                    
                    return True
    
    return False

# Get user by ID
def get_user_by_id(user_id):
    user_file = os.path.join(USER_DATA_PATH, f'{user_id}.json')
    if os.path.exists(user_file):
        with open(user_file, 'r') as f:
            return json.load(f)
    return None

# Get user by username
def get_user_by_username(username):
    for filename in os.listdir(USER_DATA_PATH):
        if filename.endswith('.json'):
            with open(os.path.join(USER_DATA_PATH, filename), 'r') as f:
                user_data = json.load(f)
                if user_data.get('username') == username:
                    # If profile is private and not current user, limit data
                    if not user_data.get('profile', {}).get('public', True) and (
                        'user_id' not in session or session['user_id'] != user_data['user_id']):
                        return {
                            'username': user_data['username'],
                            'display_name': user_data.get('display_name', user_data['username']),
                            'profile': {
                                'profile_picture': user_data.get('profile', {}).get('profile_picture', ''),
                                'banner': user_data.get('profile', {}).get('banner', ''),
                                'private': True
                            }
                        }
                    return user_data
    return None

# Get current user
def get_current_user():
    if 'user_id' in session:
        return get_user_by_id(session['user_id'])
    return None

# Update user settings
def update_user_settings(form_data):
    if 'user_id' not in session:
        return False
    
    user_data = get_user_by_id(session['user_id'])
    if not user_data:
        return False
    
    # Update display name
    if 'display_name' in form_data:
        user_data['display_name'] = form_data['display_name']
    
    # Update bio
    if 'bio' in form_data:
        user_data['profile']['bio'] = form_data['bio']
    
    # Update privacy
    if 'public' in form_data:
        user_data['profile']['public'] = form_data['public'] == 'true'
    
    # Update theme
    if 'theme' in form_data:
        user_data['profile']['theme'] = form_data['theme']
    
    # Update custom CSS
    if 'custom_css' in form_data:
        # Sanitize CSS (basic implementation)
        css = form_data['custom_css']
        # Remove potentially harmful CSS
        css = re.sub(r'@import', '', css)
        css = re.sub(r'javascript:', '', css)
        user_data['profile']['custom_css'] = css
    
    # Save updated user data
    save_user_data(session['user_id'], user_data)
    
    return True

# Toggle favorite
def toggle_favorite(type, item_id):
    if 'user_id' not in session:
        return False
    
    user_data = get_user_by_id(session['user_id'])
    if not user_data:
        return False
    
    # Determine which list to update
    if type == 'manga':
        favorites_list = user_data['profile']['favorites']['manga']
    elif type == 'anime':
        favorites_list = user_data['profile']['favorites']['anime']
    elif type == 'manga_character':
        favorites_list = user_data['profile']['favorites']['manga_characters']
    elif type == 'anime_character':
        favorites_list = user_data['profile']['favorites']['anime_characters']
    else:
        return False
    
    # Toggle favorite
    if item_id in favorites_list:
        favorites_list.remove(item_id)
    else:
        favorites_list.append(item_id)
    
    # Save updated user data
    save_user_data(session['user_id'], user_data)
    
    return True

# Update top favorites
def update_top_favorites(type, medal, item_id):
    if 'user_id' not in session:
        return False
    
    user_data = get_user_by_id(session['user_id'])
    if not user_data:
        return False
    
    # Determine which list to update
    if type in ['manga', 'anime', 'manga_characters', 'anime_characters']:
        user_data['profile']['top_favorites'][type][medal] = item_id
    else:
        return False
    
    # Save updated user data
    save_user_data(session['user_id'], user_data)
    
    return True

# Get popular users
def get_popular_users(limit=10):
    users = []
    
    # Get all users
    for filename in os.listdir(USER_DATA_PATH):
        if filename.endswith('.json'):
            with open(os.path.join(USER_DATA_PATH, filename), 'r') as f:
                user_data = json.load(f)
                
                # Skip private profiles
                if not user_data.get('profile', {}).get('public', True):
                    continue
                
                # Calculate popularity (simple metric: friends + favorites)
                popularity = len(user_data.get('social', {}).get('friends', []))
                popularity += len(user_data.get('profile', {}).get('favorites', {}).get('manga', []))
                popularity += len(user_data.get('profile', {}).get('favorites', {}).get('anime', []))
                
                users.append({
                    'username': user_data['username'],
                    'display_name': user_data.get('display_name', user_data['username']),
                    'profile_picture': user_data.get('profile', {}).get('profile_picture', ''),
                    'popularity': popularity
                })
    
    # Sort by popularity and limit
    users.sort(key=lambda x: x['popularity'], reverse=True)
    return users[:limit]

# Import from external service
def import_from_service(service, file_data):
    if 'user_id' not in session:
        return False
    
    user_data = get_user_by_id(session['user_id'])
    if not user_data:
        return False
    
    try:
        # Parse imported data
        if service == 'mal':
            # Parse MyAnimeList XML export
            # This is a simplified mock implementation
            pass
        elif service == 'anilist':
            # Parse AniList JSON export
            # This is a simplified mock implementation
            pass
        elif service == 'kitsu':
            # Parse Kitsu JSON export
            # This is a simplified mock implementation
            pass
        else:
            return False
        
        # Save updated user data
        save_user_data(session['user_id'], user_data)
        return True
    
    except Exception as e:
        print(f"Import error: {e}")
        return False

# Export to external service
def export_to_service(service):
    if 'user_id' not in session:
        return None
    
    user_data = get_user_by_id(session['user_id'])
    if not user_data:
        return None
    
    try:
        # Generate export data
        if service == 'mal':
            # Generate MyAnimeList XML export
            # This is a simplified mock implementation
            return {"format": "xml", "data": "XML data would go here"}
        elif service == 'anilist':
            # Generate AniList JSON export
            # This is a simplified mock implementation
            return {"format": "json", "data": user_data['profile']['lists']}
        elif service == 'kitsu':
            # Generate Kitsu JSON export
            # This is a simplified mock implementation
            return {"format": "json", "data": user_data['profile']['lists']}
        else:
            return None
    
    except Exception as e:
        print(f"Export error: {e}")
        return None
import os
import json
import re
import requests
import uuid
import datetime
from flask import session

# Data paths
USER_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'users')

# Ensure directories exist
os.makedirs(USER_DATA_PATH, exist_ok=True)

# Get user by ID
def get_user_by_id(user_id):
    user_file = os.path.join(USER_DATA_PATH, f'{user_id}.json')
    if os.path.exists(user_file):
        with open(user_file, 'r') as f:
            return json.load(f)
    return None

# Get current user
def get_current_user():
    if 'user_id' in session:
        return get_user_by_id(session['user_id'])
    return None

# Update user profile
def update_user_profile(form_data, profile_picture=None, banner=None):
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
    with open(os.path.join(USER_DATA_PATH, f'{session["user_id"]}.json'), 'w') as f:
        json.dump(user_data, f, indent=4)
    
    return True

# Update user list
def update_user_list(type, item_id, status):
    if 'user_id' not in session:
        return False
    
    user_data = get_user_by_id(session['user_id'])
    if not user_data:
        return False
    
    valid_statuses = {
        'manga': ['reading', 'completed', 'planning'],
        'anime': ['watching', 'completed', 'planning']
    }
    
    # Validate type and status
    if type not in valid_statuses or status not in valid_statuses[type]:
        return False
    
    # Remove from all lists
    for list_status in valid_statuses[type]:
        if item_id in user_data['profile']['lists'][type][list_status]:
            user_data['profile']['lists'][type][list_status].remove(item_id)
    
    # Add to specified list
    user_data['profile']['lists'][type][status].append(item_id)
    
    # Save updated user data
    with open(os.path.join(USER_DATA_PATH, f'{session["user_id"]}.json'), 'w') as f:
        json.dump(user_data, f, indent=4)
    
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
    with open(os.path.join(USER_DATA_PATH, f'{session["user_id"]}.json'), 'w') as f:
        json.dump(user_data, f, indent=4)
    
    return True

# Update top favorites
def update_top_favorites(type, medal, item_id):
    if 'user_id' not in session:
        return False
    
    user_data = get_user_by_id(session['user_id'])
    if not user_data:
        return False
    
    valid_medals = ['gold', 'silver', 'bronze']
    valid_types = ['manga', 'anime', 'manga_characters', 'anime_characters']
    
    # Validate medal and type
    if medal not in valid_medals or type not in valid_types:
        return False
    
    # Update medal
    user_data['profile']['top_favorites'][type][medal] = item_id
    
    # Save updated user data
    with open(os.path.join(USER_DATA_PATH, f'{session["user_id"]}.json'), 'w') as f:
        json.dump(user_data, f, indent=4)
    
    return True
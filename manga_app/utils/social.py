import os
import json
import uuid
import datetime
from flask import session

# Data paths
USER_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'users')
POSTS_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'posts')

# Ensure directories exist
os.makedirs(USER_DATA_PATH, exist_ok=True)
os.makedirs(POSTS_DATA_PATH, exist_ok=True)

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

# Create new post
def create_new_post(content, poll_options=None):
    if 'user_id' not in session or not content:
        return False
    
    user_data = get_user_by_id(session['user_id'])
    if not user_data:
        return False
    
    # Validate content length
    if len(content) > 5000:
        return False
    
    # Create post ID
    post_id = str(uuid.uuid4())
    
    # Create post data
    post_data = {
        'id': post_id,
        'user_id': session['user_id'],
        'username': user_data['username'],
        'display_name': user_data.get('display_name', user_data['username']),
        'profile_picture': user_data.get('profile', {}).get('profile_picture', ''),
        'content': content,
        'created_at': datetime.datetime.now().isoformat(),
        'likes': [],
        'comments': []
    }
    
    # Add poll if provided
    if poll_options and isinstance(poll_options, list) and len(poll_options) > 1:
        post_data['poll'] = {
            'options': [{'text': option, 'votes': []} for option in poll_options],
            'expires_at': (datetime.datetime.now() + datetime.timedelta(days=7)).isoformat()
        }
    
    # Save post data
    os.makedirs(POSTS_DATA_PATH, exist_ok=True)
    with open(os.path.join(POSTS_DATA_PATH, f'{post_id}.json'), 'w') as f:
        json.dump(post_data, f, indent=4)
    
    return True

# Get recent posts
def get_recent_posts(limit=20):
    posts = []
    
    # Get all post files
    post_files = [f for f in os.listdir(POSTS_DATA_PATH) if f.endswith('.json')]
    
    # Sort by modification time (most recent first)
    post_files.sort(key=lambda x: os.path.getmtime(os.path.join(POSTS_DATA_PATH, x)), reverse=True)
    
    # Get posts
    for filename in post_files[:limit]:
        with open(os.path.join(POSTS_DATA_PATH, filename), 'r') as f:
            post_data = json.load(f)
            posts.append(post_data)
    
    return posts

# Like post
def like_post(post_id):
    if 'user_id' not in session:
        return False
    
    post_file = os.path.join(POSTS_DATA_PATH, f'{post_id}.json')
    if not os.path.exists(post_file):
        return False
    
    with open(post_file, 'r') as f:
        post_data = json.load(f)
    
    # Toggle like
    if session['user_id'] in post_data['likes']:
        post_data['likes'].remove(session['user_id'])
    else:
        post_data['likes'].append(session['user_id'])
    
    # Save updated post data
    with open(post_file, 'w') as f:
        json.dump(post_data, f, indent=4)
    
    return True

# Add comment to post
def add_comment(post_id, content):
    if 'user_id' not in session or not content:
        return False
    
    post_file = os.path.join(POSTS_DATA_PATH, f'{post_id}.json')
    if not os.path.exists(post_file):
        return False
    
    user_data = get_user_by_id(session['user_id'])
    if not user_data:
        return False
    
    with open(post_file, 'r') as f:
        post_data = json.load(f)
    
    # Create comment
    comment = {
        'id': str(uuid.uuid4()),
        'user_id': session['user_id'],
        'username': user_data['username'],
        'display_name': user_data.get('display_name', user_data['username']),
        'profile_picture': user_data.get('profile', {}).get('profile_picture', ''),
        'content': content,
        'created_at': datetime.datetime.now().isoformat(),
        'likes': []
    }
    
    # Add comment to post
    post_data['comments'].append(comment)
    
    # Save updated post data
    with open(post_file, 'w') as f:
        json.dump(post_data, f, indent=4)
    
    return True

# Vote in poll
def vote_in_poll(post_id, option_index):
    if 'user_id' not in session:
        return False
    
    post_file = os.path.join(POSTS_DATA_PATH, f'{post_id}.json')
    if not os.path.exists(post_file):
        return False
    
    with open(post_file, 'r') as f:
        post_data = json.load(f)
    
    # Check if post has a poll
    if 'poll' not in post_data:
        return False
    
    # Check if poll is expired
    if datetime.datetime.fromisoformat(post_data['poll']['expires_at']) < datetime.datetime.now():
        return False
    
    # Check if option index is valid
    if option_index < 0 or option_index >= len(post_data['poll']['options']):
        return False
    
    # Remove user from all options
    for option in post_data['poll']['options']:
        if session['user_id'] in option['votes']:
            option['votes'].remove(session['user_id'])
    
    # Add user to selected option
    post_data['poll']['options'][option_index]['votes'].append(session['user_id'])
    
    # Save updated post data
    with open(post_file, 'w') as f:
        json.dump(post_data, f, indent=4)
    
    return True

# Add friend
def add_friend(username):
    if 'user_id' not in session:
        return False
    
    # Get current user
    current_user = get_user_by_id(session['user_id'])
    if not current_user:
        return False
    
    # Get target user
    target_user = None
    target_user_id = None
    
    for filename in os.listdir(USER_DATA_PATH):
        if filename.endswith('.json'):
            with open(os.path.join(USER_DATA_PATH, filename), 'r') as f:
                user_data = json.load(f)
                if user_data.get('username') == username:
                    target_user = user_data
                    target_user_id = user_data['user_id']
                    break
    
    if not target_user:
        return False
    
    # Don't add self as friend
    if target_user_id == session['user_id']:
        return False
    
    # Check if already friends
    if target_user_id in current_user.get('social', {}).get('friends', []):
        return False
    
    # Check if friend request already sent
    if target_user_id in current_user.get('social', {}).get('friend_requests', {}).get('sent', []):
        return False
    
    # Check if friend request already received
    if target_user_id in current_user.get('social', {}).get('friend_requests', {}).get('received', []):
        # Accept friend request
        current_user['social']['friend_requests']['received'].remove(target_user_id)
        current_user['social']['friends'].append(target_user_id)
        
        target_user['social']['friend_requests']['sent'].remove(session['user_id'])
        target_user['social']['friends'].append(session['user_id'])
        
        # Save updated user data
        with open(os.path.join(USER_DATA_PATH, f'{session["user_id"]}.json'), 'w') as f:
            json.dump(current_user, f, indent=4)
        
        with open(os.path.join(USER_DATA_PATH, f'{target_user_id}.json'), 'w') as f:
            json.dump(target_user, f, indent=4)
        
        return True
    
    # Send friend request
    current_user['social']['friend_requests']['sent'].append(target_user_id)
    target_user['social']['friend_requests']['received'].append(session['user_id'])
    
    # Add notification to target user
    notification = {
        'id': str(uuid.uuid4()),
        'type': 'friend_request',
        'from_user_id': session['user_id'],
        'from_username': current_user['username'],
        'created_at': datetime.datetime.now().isoformat(),
        'read': False
    }
    
    target_user['social']['notifications'].append(notification)
    
    # Save updated user data
    with open(os.path.join(USER_DATA_PATH, f'{session["user_id"]}.json'), 'w') as f:
        json.dump(current_user, f, indent=4)
    
    with open(os.path.join(USER_DATA_PATH, f'{target_user_id}.json'), 'w') as f:
        json.dump(target_user, f, indent=4)
    
    return True

# Get notifications
def get_notifications():
    if 'user_id' not in session:
        return []
    
    # Get current user
    current_user = get_user_by_id(session['user_id'])
    if not current_user:
        return []
    
    return current_user.get('social', {}).get('notifications', [])

# Mark notification as read
def mark_notification_read(notification_id):
    if 'user_id' not in session:
        return False
    
    # Get current user
    current_user = get_user_by_id(session['user_id'])
    if not current_user:
        return False
    
    # Find and mark notification as read
    for notification in current_user.get('social', {}).get('notifications', []):
        if notification.get('id') == notification_id:
            notification['read'] = True
            break
    
    # Save updated user data
    with open(os.path.join(USER_DATA_PATH, f'{session["user_id"]}.json'), 'w') as f:
        json.dump(current_user, f, indent=4)
    
    return True
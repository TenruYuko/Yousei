from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
import os
import json
import secrets
import re
import hashlib
import uuid
import datetime
import time
import threading
import requests
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Ensure all necessary directories exist
def ensure_directories():
    directories = [
        os.path.join('data', 'manga'),
        os.path.join('data', 'anime'),
        os.path.join('data', 'users'),
        os.path.join('data', 'covers'),
        os.path.join('data', 'posts'),
        os.path.join('static', 'uploads'),
        os.path.join('static', 'uploads', 'profiles'),
        os.path.join('static', 'uploads', 'banners')
    ]
    
    for directory in directories:
        os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), directory), exist_ok=True)

ensure_directories()

# Import utility modules
from utils.auth import *
from utils.manga import *
from utils.anime import *
from utils.user import *
from utils.social import *
from utils.api import *

# Start background scanning thread
from utils.scanner import start_scanner_thread
scanner_thread = threading.Thread(target=start_scanner_thread)
scanner_thread.daemon = True
scanner_thread.start()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/library')
def library():
    sort = request.args.get('sort', 'alpha')
    search = request.args.get('search', '')
    
    manga_list = get_manga_list(sort=sort, search=search)
    
    return render_template('library.html', 
                          manga_list=manga_list, 
                          sort=sort, 
                          search=search)

@app.route('/manga/<manga_id>')
def manga_detail(manga_id):
    manga = get_manga_details(manga_id)
    if not manga:
        flash('Manga not found', 'error')
        return redirect(url_for('library'))
    
    return render_template('manga_detail.html', manga=manga)

@app.route('/anime')
def anime_library():
    sort = request.args.get('sort', 'alpha')
    search = request.args.get('search', '')
    
    anime_list = get_anime_list(sort=sort, search=search)
    
    return render_template('anime_library.html', 
                          anime_list=anime_list, 
                          sort=sort, 
                          search=search)

@app.route('/anime/<anime_id>')
def anime_detail(anime_id):
    anime = get_anime_details(anime_id)
    if not anime:
        flash('Anime not found', 'error')
        return redirect(url_for('anime_library'))
    
    return render_template('anime_detail.html', anime=anime)

@app.route('/community')
def community():
    popular_users = get_popular_users()
    recent_posts = get_recent_posts()
    
    return render_template('community.html', 
                          popular_users=popular_users,
                          recent_posts=recent_posts)

@app.route('/user/<username>')
def user_profile(username):
    user = get_user_by_username(username)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('community'))
    
    return render_template('user_profile.html', user=user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Registration logic
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if register_user(username, email, password):
            flash('Registration successful! Please check your email to verify your account.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Registration failed. Username or email may already be in use.', 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if authenticate_user(email, password):
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login failed. Please check your credentials.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # Update user settings
        update_user_settings(request.form)
        flash('Settings updated successfully', 'success')
        return redirect(url_for('settings'))
    
    user = get_current_user()
    return render_template('settings.html', user=user)

@app.route('/create_post', methods=['POST'])
@login_required
def create_post():
    content = request.form.get('content')
    if create_new_post(content):
        flash('Post created successfully', 'success')
    else:
        flash('Failed to create post', 'error')
    
    return redirect(url_for('community'))

@app.route('/favorite/<type>/<id>', methods=['POST'])
@login_required
def favorite(type, id):
    if toggle_favorite(type, id):
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'})

@app.route('/import', methods=['GET', 'POST'])
@login_required
def import_list():
    if request.method == 'POST':
        source = request.form.get('source')
        file = request.files.get('import_file')
        
        if file and source:
            if import_from_service(source, file):
                flash('Import successful', 'success')
                return redirect(url_for('library'))
            else:
                flash('Import failed', 'error')
    
    return render_template('import.html')

@app.route('/export/<service>')
@login_required
def export_list(service):
    export_data = export_to_service(service)
    if export_data:
        return jsonify(export_data)
    return jsonify({'error': 'Export failed'})

@app.route('/api/search_characters')
@login_required
def search_characters():
    query = request.args.get('query', '')
    type = request.args.get('type', 'manga')
    
    results = search_character_by_regex(query, type)
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)
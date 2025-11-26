import json
import os
import uuid
import requests
import threading
import time
import logging
from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__, static_folder='.', static_url_path='')

RULES_FILE = '/config/rules.json'
RULES = []

def load_rules():
    global RULES
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, 'r') as f:
            RULES = json.load(f)
    logging.info(f"Loaded {len(RULES)} rules.")

def save_rules():
    with open(RULES_FILE, 'w') as f:
        json.dump(RULES, f, indent=2)
    logging.info(f"Saved {len(RULES)} rules.")

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/rules', methods=['GET', 'POST'])
def rules():
    global RULES
    if request.method == 'POST':
        rule = request.get_json()
        rule['id'] = str(uuid.uuid4())
        RULES.append(rule)
        save_rules()
        logging.info(f"Added rule: {rule}")
        return jsonify({"status": "success"})
    return jsonify({"rules": RULES})

@app.route('/api/rules/preview', methods=['POST'])
def preview_rule():
    rule = request.get_json()
    affected_items = []
    if rule['mediaType'] == 'episode':
        affected_items = handle_sonarr_rule(rule, dry_run=True)
    elif rule['mediaType'] == 'movie':
        affected_items = handle_radarr_rule(rule, dry_run=True)
    return jsonify({"affected_items": affected_items})

@app.route('/api/rules/<rule_id>', methods=['DELETE'])
def delete_rule(rule_id):
    global RULES
    RULES = [rule for rule in RULES if rule.get('id') != rule_id]
    save_rules()
    logging.info(f"Deleted rule with id: {rule_id}")
    return jsonify({"status": "success"})

@app.route('/api/sonarr/data', methods=['GET'])
def sonarr_data():
    quality_profiles = sonarr_api_request('qualityprofile')
    tags = sonarr_api_request('tag')
    return jsonify({
        'quality_profiles': quality_profiles,
        'tags': tags
    })

@app.route('/api/radarr/data', methods=['GET'])
def radarr_data():
    quality_profiles = radarr_api_request('qualityprofile')
    tags = radarr_api_request('tag')
    return jsonify({
        'quality_profiles': quality_profiles,
        'tags': tags
    })

@app.route('/api/sonarr/library', methods=['GET'])
def sonarr_library():
    library = sonarr_api_request('series')
    return jsonify(library)

@app.route('/api/radarr/library', methods=['GET'])
def radarr_library():
    library = radarr_api_request('movie')
    return jsonify(library)

@app.route('/api/sonarr/wanted', methods=['GET'])
def sonarr_wanted():
    wanted = sonarr_api_request('wanted/missing')
    return jsonify(wanted)

@app.route('/api/radarr/wanted', methods=['GET'])
def radarr_wanted():
    wanted = radarr_api_request('wanted/missing')
    return jsonify(wanted)

@app.route('/api/sonarr/search', methods=['POST'])
def sonarr_search():
    data = request.get_json()
    series_id = data.get('seriesId')
    sonarr_api_request('command', method='POST', json={'name': 'SeriesSearch', 'seriesId': series_id})
    return jsonify({"status": "success"})

@app.route('/api/radarr/search', methods=['POST'])
def radarr_search():
    data = request.get_json()
    movie_id = data.get('movieId')
    radarr_api_request('command', method='POST', json={'name': 'MoviesSearch', 'movieIds': [movie_id]})
    return jsonify({"status": "success"})

def api_request(url, api_key, endpoint, method='GET', json=None):
    if not url or not api_key:
        return None
    try:
        if method == 'GET':
            response = requests.get(f"{url}/api/v3/{endpoint}", headers={'X-Api-Key': api_key})
        elif method == 'POST':
            response = requests.post(f"{url}/api/v3/{endpoint}", headers={'X-Api-Key': api_key}, json=json)
        elif method == 'PUT':
            response = requests.put(f"{url}/api/v3/{endpoint}", headers={'X-Api-Key': api_key}, json=json)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error communicating with API: {e}")
        return None

def sonarr_api_request(endpoint, method='GET', json=None):
    return api_request(os.environ.get('SONARR_URL'), os.environ.get('SONARR_API_KEY'), endpoint, method, json)

def delete_sonarr_episode(item_id):
    url = os.environ.get('SONARR_URL')
    api_key = os.environ.get('SONARR_API_KEY')
    if not url or not api_key:
        return
    try:
        requests.delete(f"{url}/api/v3/queue/{item_id}", headers={'X-Api-Key': api_key}, params={'removeFromClient': 'true', 'blocklist': 'true'})
    except requests.exceptions.RequestException as e:
        logging.error(f"Error deleting Sonarr episode: {e}")

def run_automations():
    while True:
        logging.info("Running automations...")
        for rule in RULES:
            if rule['mediaType'] == 'episode':
                handle_sonarr_rule(rule)
            elif rule['mediaType'] == 'movie':
                handle_radarr_rule(rule)
        time.sleep(60)

def handle_radarr_rule(rule, dry_run=False):
    items = []
    if rule['eventType'] in ['grabbed', 'downloaded', 'imported', 'failed']:
        items = (radarr_api_request('queue') or {}).get('records', [])
    elif rule['eventType'] == 'missing':
        items = (radarr_api_request('wanted/missing') or {}).get('records', [])
    elif rule['eventType'] == 'unmonitored':
        items = radarr_api_request('movie?monitored=false') or []

    tags = radarr_api_request('tag')
    tag_map = {tag['label']: tag['id'] for tag in tags} if tags else {}
    quality_profiles = radarr_api_request('qualityprofile')
    quality_profile_map = {profile['name']: profile['id'] for profile in quality_profiles} if quality_profiles else {}
    affected_items = []

    for item in items:
        if check_rule(rule, item, tag_map):
            if dry_run:
                affected_items.append(item)
            else:
                action = rule.get('action')
                action_value = rule.get('actionValue')
                if action == 'delete':
                    logging.info(f"Deleting Radarr movie: {item['title']}")
                    delete_radarr_movie(item['id'])
                elif action == 'notify':
                    logging.info(f"Radarr notification: {item['title']}")
                elif action == 'add_tag':
                    logging.info(f"Adding tag '{action_value}' to Radarr movie: {item['title']}")
                    item_id = item['id'] if rule['eventType'] == 'unmonitored' else item['movieId']
                    add_radarr_tag(item_id, tag_map[action_value])
                elif action == 'remove_tag':
                    logging.info(f"Removing tag '{action_value}' from Radarr movie: {item['title']}")
                    item_id = item['id'] if rule['eventType'] == 'unmonitored' else item['movieId']
                    remove_radarr_tag(item_id, tag_map[action_value])
                elif action == 'change_quality_profile':
                    logging.info(f"Changing quality profile to '{action_value}' for Radarr movie: {item['title']}")
                    item_id = item['id'] if rule['eventType'] == 'unmonitored' else item['movieId']
                    change_radarr_quality_profile(item_id, quality_profile_map[action_value])
                elif action == 'monitor':
                    logging.info(f"Monitoring Radarr movie: {item['title']}")
                    item_id = item['id'] if rule['eventType'] == 'unmonitored' else item['movieId']
                    monitor_radarr_movie(item_id)
                elif action == 'unmonitor':
                    logging.info(f"Unmonitoring Radarr movie: {item['title']}")
                    item_id = item['id'] if rule['eventType'] == 'unmonitored' else item['movieId']
                    unmonitor_radarr_movie(item_id)

    return affected_items


def radarr_api_request(endpoint, method='GET', json=None):
    return api_request(os.environ.get('RADARR_URL'), os.environ.get('RADARR_API_KEY'), endpoint, method, json)

def delete_radarr_movie(item_id):
    url = os.environ.get('RADARR_URL')
    api_key = os.environ.get('RADARR_API_KEY')
    if not url or not api_key:
        return
    try:
        requests.delete(f"{url}/api/v3/queue/{item_id}", headers={'X-Api-Key': api_key}, params={'removeFromClient': 'true', 'blocklist': 'true'})
    except requests.exceptions.RequestException as e:
        logging.error(f"Error deleting Radarr movie: {e}")

def handle_sonarr_rule(rule, dry_run=False):
    items = []
    if dry_run and rule['eventType'] == 'imported':
        items = sonarr_api_request('series') or []
    elif rule['eventType'] in ['grabbed', 'downloaded', 'imported', 'failed']:
        items = (sonarr_api_request('queue') or {}).get('records', [])
    elif rule['eventType'] == 'missing':
        items = (sonarr_api_request('wanted/missing') or {}).get('records', [])
    elif rule['eventType'] == 'unmonitored':
        items = sonarr_api_request('series?monitored=false') or []

    tags = sonarr_api_request('tag')
    tag_map = {tag['label']: tag['id'] for tag in tags} if tags else {}
    quality_profiles = sonarr_api_request('qualityprofile')
    quality_profile_map = {profile['name']: profile['id'] for profile in quality_profiles} if quality_profiles else {}
    affected_items = []

    for item in items:
        if check_rule(rule, item, tag_map):
            if dry_run:
                affected_items.append(item)
            else:
                action = rule.get('action')
                action_value = rule.get('actionValue')
                if action == 'delete':
                    logging.info(f"Deleting Sonarr episode: {item['title']}")
                    delete_sonarr_episode(item['id'])
                elif action == 'notify':
                    logging.info(f"Sonarr notification: {item['title']}")
                elif action == 'add_tag':
                    logging.info(f"Adding tag '{action_value}' to Sonarr series: {item['title']}")
                    item_id = item['id'] if rule['eventType'] == 'unmonitored' else item['seriesId']
                    add_sonarr_tag(item_id, tag_map[action_value])
                elif action == 'remove_tag':
                    logging.info(f"Removing tag '{action_value}' from Sonarr series: {item['title']}")
                    item_id = item['id'] if rule['eventType'] == 'unmonitored' else item['seriesId']
                    remove_sonarr_tag(item_id, tag_map[action_value])
                elif action == 'change_quality_profile':
                    logging.info(f"Changing quality profile to '{action_value}' for Sonarr series: {item['title']}")
                    item_id = item['id'] if rule['eventType'] == 'unmonitored' else item['seriesId']
                    change_sonarr_quality_profile(item_id, quality_profile_map[action_value])
                elif action == 'monitor':
                    logging.info(f"Monitoring Sonarr series: {item['title']}")
                    item_id = item['id'] if rule['eventType'] == 'unmonitored' else item['seriesId']
                    monitor_sonarr_series(item_id)
                elif action == 'unmonitor':
                    logging.info(f"Unmonitoring Sonarr series: {item['title']}")
                    item_id = item['id'] if rule['eventType'] == 'unmonitored' else item['seriesId']
                    unmonitor_sonarr_series(item_id)

    return affected_items

def add_sonarr_tag(series_id, tag_id):
    series = sonarr_api_request(f'series/{series_id}')
    if tag_id not in series.get('tags', []):
        series['tags'].append(tag_id)
        sonarr_api_request(f'series/{series_id}', method='PUT', json=series)

def remove_sonarr_tag(series_id, tag_id):
    series = sonarr_api_request(f'series/{series_id}')
    if tag_id in series.get('tags', []):
        series['tags'].remove(tag_id)
        sonarr_api_request(f'series/{series_id}', method='PUT', json=series)

def change_sonarr_quality_profile(series_id, quality_profile_id):
    series = sonarr_api_request(f'series/{series_id}')
    series['qualityProfileId'] = quality_profile_id
    sonarr_api_request(f'series/{series_id}', method='PUT', json=series)

def monitor_sonarr_series(series_id):
    series = sonarr_api_request(f'series/{series_id}')
    series['monitored'] = True
    sonarr_api_request(f'series/{series_id}', method='PUT', json=series)

def unmonitor_sonarr_series(series_id):
    series = sonarr_api_request(f'series/{series_id}')
    series['monitored'] = False
    sonarr_api_request(f'series/{series_id}', method='PUT', json=series)

def add_radarr_tag(movie_id, tag_id):
    movie = radarr_api_request(f'movie/{movie_id}')
    if tag_id not in movie.get('tags', []):
        movie['tags'].append(tag_id)
        radarr_api_request(f'movie/{movie_id}', method='PUT', json=movie)

def remove_radarr_tag(movie_id, tag_id):
    movie = radarr_api_request(f'movie/{movie_id}')
    if tag_id in movie.get('tags', []):
        movie['tags'].remove(tag_id)
        radarr_api_request(f'movie/{movie_id}', method='PUT', json=movie)

def change_radarr_quality_profile(movie_id, quality_profile_id):
    movie = radarr_api_request(f'movie/{movie_id}')
    movie['qualityProfileId'] = quality_profile_id
    radarr_api_request(f'movie/{movie_id}', method='PUT', json=movie)

def monitor_radarr_movie(movie_id):
    movie = radarr_api_request(f'movie/{movie_id}')
    movie['monitored'] = True
    radarr_api_request(f'movie/{movie_id}', method='PUT', json=movie)

def unmonitor_radarr_movie(movie_id):
    movie = radarr_api_request(f'movie/{movie_id}')
    movie['monitored'] = False
    radarr_api_request(f'movie/{movie_id}', method='PUT', json=movie)

def check_rule(rule, item, tag_map):
    event_type = rule.get('eventType')
    status = item.get('status')
    tracked_download_status = item.get('trackedDownloadStatus')
    monitored = item.get('monitored')

    if event_type == 'downloaded' and status == 'completed':
        if rule.get('status') == 'waiting_for_import' and tracked_download_status in ['warning', 'error']:
            pass
        elif rule.get('status') == 'completed' and tracked_download_status == 'ok':
            pass
        else:
            return False
    elif event_type == 'grabbed' and status == 'pending':
        pass
    elif event_type == 'imported' and status == 'completed' and tracked_download_status == 'ok':
        pass
    elif event_type == 'failed' and status == 'failed':
        pass
    elif event_type == 'missing' and monitored:
        pass
    elif event_type == 'unmonitored' and not monitored:
        pass
    else:
        return False

    if rule.get('qualityProfile') and rule.get('qualityProfile') != item.get('quality', {}).get('quality', {}).get('name'):
        return False
    if rule.get('tag'):
        tag_id = tag_map.get(rule.get('tag'))
        if not tag_id or tag_id not in item.get('tags', []):
            return False

    return True

if __name__ == '__main__':
    load_rules()
    automation_thread = threading.Thread(target=run_automations)
    automation_thread.daemon = True
    automation_thread.start()
    app.run(host='0.0.0.0', port=8000)

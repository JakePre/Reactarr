import json
import os
import uuid
import requests
import threading
import time
import logging
from flask import Flask, jsonify, request, send_from_directory

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

def sonarr_api_request(endpoint):
    url = os.environ.get('SONARR_URL')
    api_key = os.environ.get('SONARR_API_KEY')
    if not url or not api_key:
        return None
    try:
        response = requests.get(f"{url}/api/v3/{endpoint}", headers={'X-Api-Key': api_key})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error communicating with Sonarr: {e}")
        return None

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
    queue = radarr_api_request('queue')
    if not queue:
        return []

    tags = radarr_api_request('tag')
    tag_map = {tag['label']: tag['id'] for tag in tags} if tags else {}
    affected_items = []

    for item in queue.get('records', []):
        if check_rule(rule, item, tag_map):
            if dry_run:
                affected_items.append(item)
            else:
                if rule.get('action') == 'delete':
                    logging.info(f"Deleting Radarr movie: {item['title']}")
                    delete_radarr_movie(item['id'])
                elif rule.get('action') == 'notify':
                    logging.info(f"Radarr notification: {item['title']}")
    return affected_items


def radarr_api_request(endpoint):
    url = os.environ.get('RADARR_URL')
    api_key = os.environ.get('RADARR_API_KEY')
    if not url or not api_key:
        return None
    try:
        response = requests.get(f"{url}/api/v3/{endpoint}", headers={'X-Api-Key': api_key})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error communicating with Radarr: {e}")
        return None

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
    queue = sonarr_api_request('queue')
    if not queue:
        return []

    tags = sonarr_api_request('tag')
    tag_map = {tag['label']: tag['id'] for tag in tags} if tags else {}
    affected_items = []

    for item in queue.get('records', []):
        if check_rule(rule, item, tag_map):
            if dry_run:
                affected_items.append(item)
            else:
                if rule.get('action') == 'delete':
                    logging.info(f"Deleting Sonarr episode: {item['title']}")
                    delete_sonarr_episode(item['id'])
                elif rule.get('action') == 'notify':
                    logging.info(f"Sonarr notification: {item['title']}")
    return affected_items

def check_rule(rule, item, tag_map):
    event_type_match = False
    if rule.get('eventType') == 'downloaded' and item.get('status') == 'completed':
        if rule.get('status') == 'waiting_for_import' and item.get('trackedDownloadStatus') in ['warning', 'error']:
            event_type_match = True
        if rule.get('status') == 'completed' and item.get('trackedDownloadStatus') == 'ok':
            event_type_match = True
    elif rule.get('eventType') == 'grabbed' and item.get('status') == 'pending':
        event_type_match = True
    elif rule.get('eventType') == 'imported' and item.get('status') == 'completed' and item.get('trackedDownloadStatus') == 'ok':
        event_type_match = True
    elif rule.get('eventType') == 'failed' and item.get('status') == 'failed':
        event_type_match = True

    if not event_type_match:
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

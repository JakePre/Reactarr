import json
import os
import uuid
import requests
import threading
import time
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder='.', static_url_path='')

RULES_FILE = '/config/rules.json'
RULES = []

def load_rules():
    global RULES
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, 'r') as f:
            RULES = json.load(f)

def save_rules():
    with open(RULES_FILE, 'w') as f:
        json.dump(RULES, f, indent=2)

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
        return jsonify({"status": "success"})
    return jsonify({"rules": RULES})

@app.route('/api/rules/<rule_id>', methods=['DELETE'])
def delete_rule(rule_id):
    global RULES
    RULES = [rule for rule in RULES if rule.get('id') != rule_id]
    save_rules()
    return jsonify({"status": "success"})

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
        print(f"Error communicating with Sonarr: {e}")
        return None

def delete_sonarr_episode(item_id):
    url = os.environ.get('SONARR_URL')
    api_key = os.environ.get('SONARR_API_KEY')
    if not url or not api_key:
        return
    try:
        requests.delete(f"{url}/api/v3/queue/{item_id}", headers={'X-Api-Key': api_key}, params={'removeFromClient': 'true', 'blocklist': 'true'})
    except requests.exceptions.RequestException as e:
        print(f"Error deleting Sonarr episode: {e}")

def run_automations():
    while True:
        for rule in RULES:
            if rule['mediaType'] == 'episode':
                handle_sonarr_rule(rule)
            elif rule['mediaType'] == 'movie':
                handle_radarr_rule(rule)
        time.sleep(60)

def handle_radarr_rule(rule):
    if rule.get('eventType') == 'downloaded':
        queue = radarr_api_request('queue')
        if not queue:
            return

        for item in queue.get('records', []):
            if item.get('status') == 'completed':
                if rule.get('status') == 'waiting_for_import' and item.get('trackedDownloadStatus') in ['warning', 'error']:
                    if rule.get('action') == 'delete':
                        print(f"Deleting Radarr movie: {item['title']}")
                        delete_radarr_movie(item['id'])
                    elif rule.get('action') == 'notify':
                        print(f"Radarr movie waiting for import: {item['title']}")
                elif rule.get('status') == 'completed' and item.get('trackedDownloadStatus') == 'ok':
                     if rule.get('action') == 'notify':
                        print(f"Radarr movie imported: {item['title']}")

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
        print(f"Error communicating with Radarr: {e}")
        return None

def delete_radarr_movie(item_id):
    url = os.environ.get('RADARR_URL')
    api_key = os.environ.get('RADARR_API_KEY')
    if not url or not api_key:
        return
    try:
        requests.delete(f"{url}/api/v3/queue/{item_id}", headers={'X-Api-Key': api_key}, params={'removeFromClient': 'true', 'blocklist': 'true'})
    except requests.exceptions.RequestException as e:
        print(f"Error deleting Radarr movie: {e}")

def handle_sonarr_rule(rule):
    if rule.get('eventType') == 'downloaded':
        queue = sonarr_api_request('queue')
        if not queue:
            return

        for item in queue.get('records', []):
            if item.get('status') == 'completed':
                if rule.get('status') == 'waiting_for_import' and item.get('trackedDownloadStatus') in ['warning', 'error']:
                    if rule.get('action') == 'delete':
                        print(f"Deleting Sonarr episode: {item['title']}")
                        delete_sonarr_episode(item['id'])
                    elif rule.get('action') == 'notify':
                        print(f"Sonarr episode waiting for import: {item['title']}")
                elif rule.get('status') == 'completed' and item.get('trackedDownloadStatus') == 'ok':
                    if rule.get('action') == 'notify':
                        print(f"Sonarr episode imported: {item['title']}")

if __name__ == '__main__':
    load_rules()
    automation_thread = threading.Thread(target=run_automations)
    automation_thread.daemon = True
    automation_thread.start()
    app.run(host='0.0.0.0', port=8000)

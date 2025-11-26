import os
import requests
from dotenv import load_dotenv
import json

load_dotenv(dotenv_path='z:/reactarr/app/.env')

SONARR_URL = os.getenv('SONARR_URL')
SONARR_API_KEY = os.getenv('SONARR_API_KEY')

def api_request(endpoint):
    url = f"{SONARR_URL}/api/v3/{endpoint}"
    headers = {'X-Api-Key': SONARR_API_KEY}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def debug():
    print("Fetching series...")
    series = api_request('series')
    if not series:
        print("No series found.")
        return

    first_series = series[0]
    series_id = first_series['id']
    print(f"Inspecting Series: {first_series['title']} (ID: {series_id})")

    print("\nFetching episodes...")
    episodes = api_request(f'episode?seriesId={series_id}')
    if episodes:
        print("First Episode Keys:", episodes[0].keys())
        if 'episodeFile' in episodes[0]:
            print("Episode has 'episodeFile' key.")
        else:
            print("Episode MISSING 'episodeFile' key.")
            if 'episodeFileId' in episodes[0]:
                print(f"Episode has 'episodeFileId': {episodes[0]['episodeFileId']}")
    
    print("\nFetching episode files...")
    episode_files = api_request(f'episodefile?seriesId={series_id}')
    if episode_files:
        print("First Episode File Keys:", episode_files[0].keys())
        if 'mediaInfo' in episode_files[0]:
            print("Episode File has 'mediaInfo'.")
        else:
            print("Episode File MISSING 'mediaInfo'.")

if __name__ == "__main__":
    debug()

import requests
import os
import argparse
import json

token = os.getenv('PROXY_TOKEN')
proxy_base_url = os.getenv('PROXY_BASE_URL', 'http://localhost:8000')


def list_events(calendar_id):
    if token is None:
        print("PROXY_TOKEN environment variable is not set. ")
        return

    headers = {
        'X-Guardette-Host': 'www.googleapis.com',
        'X-Guardette-Gcp-Impersonate-Sub': calendar_id,
        'Authorization': token,
    }

    response = requests.get(
        f'{proxy_base_url}/calendar/v3/calendars/{calendar_id}/events',
        headers=headers)
    response.raise_for_status()
    events = response.json()
    print(json.dumps(events, indent=4))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='List gcal events for a given calendar id.')
    parser.add_argument('calendar_id', type=str, help='The calendar id.')
    args = parser.parse_args()

    list_events(args.calendar_id)

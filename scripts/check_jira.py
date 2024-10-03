import requests
import os
import argparse
import json

token = os.getenv('PROXY_TOKEN')
proxy_base_url = os.getenv('PROXY_BASE_URL', 'http://localhost:8000')
jira_host = os.getenv('JIRA_HOST')

if token is None:
    print("PROXY_TOKEN environment variable is not set.")
    exit(1)

if jira_host is None:
    print("JIRA_HOST environment variable is not set.")
    exit(1)


def do_request(url, *args, **kwargs):
    print(f"Requesting {url}")
    response = requests.get(url, *args, **kwargs)
    if response.status_code != 200:
        print(f"Error with status code: {response.status_code}, "
              f"Message: {response.text}")
        return
    return response.json()


def jira_apis():
    headers = {
        'X-Guardette-Host': jira_host,
        'Authorization': token,
        'Accept': 'application/json',
    }

    do_request(f'{proxy_base_url}/rest/api/3/users/search', headers=headers)
    response = do_request(f'{proxy_base_url}/rest/api/3/search'
                          '?fields=*all&expand=renderedFields,transitions,changelog',
               headers=headers)

    with open('.guardette/jira_issues_response.json', 'w') as f:
        json.dump(response, f, indent=4)

    # List Jira boards using REST 1.0 API
    boards_response = do_request(f'{proxy_base_url}/rest/agile/1.0/board', headers=headers)

    with open('.guardette/jira_boards_response.json', 'w') as f:
        json.dump(boards_response, f, indent=4)

    board_id = boards_response['values'][0]['id']
    # Get issues for the first board using REST 1.0 API
    issues_response = do_request(f'{proxy_base_url}/rest/agile/1.0/board/{board_id}/issue'
                                 '?expand=renderedFields,transitions,changelog', headers=headers)

    with open('.guardette/jira_board_issues_response.json', 'w') as f:
        json.dump(issues_response, f, indent=4)

    print(f"Retrieved issues for board ID: {board_id}")
    print(f"Total issues: {issues_response.get('total', 'N/A')}")
    print(f"Issues retrieved: {len(issues_response.get('issues', []))}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='List the first 5 users in Jira.')
    args = parser.parse_args()

    jira_apis()

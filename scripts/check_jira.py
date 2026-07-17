import argparse
import json
import os
import sys
from pathlib import Path

import requests


def do_request(url, *args, timeout=30, **kwargs):
    print(f"Requesting {url}")
    response = requests.get(url, *args, timeout=timeout, **kwargs)
    if response.status_code != 200:
        message = f"Error with status code: {response.status_code}, Message: {response.text}"
        print(message)
        raise requests.HTTPError(message, response=response)
    return response.json()


def jira_apis(token, jira_host, proxy_base_url):
    headers = {
        "X-Guardette-Host": jira_host,
        "Authorization": token,
        "Accept": "application/json",
    }
    output_dir = Path(".guardette")
    output_dir.mkdir(exist_ok=True)

    do_request(f"{proxy_base_url}/rest/api/3/users/search", headers=headers)
    response = do_request(
        f"{proxy_base_url}/rest/api/3/search?fields=*all&expand=renderedFields,transitions,changelog", headers=headers
    )

    (output_dir / "jira_issues_response.json").write_text(json.dumps(response, indent=4))

    # List Jira boards using REST 1.0 API
    boards_response = do_request(f"{proxy_base_url}/rest/agile/1.0/board", headers=headers)

    (output_dir / "jira_boards_response.json").write_text(json.dumps(boards_response, indent=4))

    board_id = boards_response["values"][0]["id"]
    # Get issues for the first board using REST 1.0 API
    issues_response = do_request(
        f"{proxy_base_url}/rest/agile/1.0/board/{board_id}/issue?expand=renderedFields,transitions,changelog",
        headers=headers,
    )

    (output_dir / "jira_board_issues_response.json").write_text(json.dumps(issues_response, indent=4))

    print(f"Retrieved issues for board ID: {board_id}")
    print(f"Total issues: {issues_response.get('total', 'N/A')}")
    print(f"Issues retrieved: {len(issues_response.get('issues', []))}")


def main():
    token = os.getenv("PROXY_TOKEN")
    proxy_base_url = os.getenv("PROXY_BASE_URL", "http://localhost:8000")
    jira_host = os.getenv("JIRA_HOST")

    if token is None:
        print("PROXY_TOKEN environment variable is not set.")
        sys.exit(1)

    if jira_host is None:
        print("JIRA_HOST environment variable is not set.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="List the first 5 users in Jira.")
    parser.parse_args()
    jira_apis(token, jira_host, proxy_base_url)


if __name__ == "__main__":
    main()

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote, urlencode, urlparse

import requests


def _validated_proxy_base_url(base_url):
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        raise ValueError("PROXY_BASE_URL must be an HTTP(S) URL with a host.")
    if parsed.username or parsed.password or parsed.params or parsed.query or parsed.fragment:
        raise ValueError("PROXY_BASE_URL must not include credentials, params, query, or fragment.")
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}", parsed.hostname.lower()


def _proxy_url(base_url, *path_segments, query=None):
    safe_base_url, proxy_host = _validated_proxy_base_url(base_url)
    safe_path = "/".join(quote(segment, safe="") for segment in path_segments)
    safe_url = f"{safe_base_url}/{safe_path}"
    if query:
        safe_url = f"{safe_url}?{query}"
    return safe_url, proxy_host


def _validate_request_url(url, allowed_host):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        raise ValueError("Request URL must be an HTTP(S) URL with a host.")
    if parsed.hostname.lower() != allowed_host:
        raise ValueError("Request URL host does not match the configured proxy host.")


def do_request(url, *args, allowed_host, timeout=30, **kwargs):
    _validate_request_url(url, allowed_host)
    print(f"Requesting {url}")
    response = requests.get(url, *args, timeout=timeout, allow_redirects=False, **kwargs)
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

    users_url, proxy_host = _proxy_url(proxy_base_url, "rest", "api", "3", "users", "search")
    do_request(users_url, headers=headers, allowed_host=proxy_host)
    bounded_jql = "updated >= -30d ORDER BY updated ASC"
    issues_query = urlencode(
        {
            "jql": bounded_jql,
            "fields": "*all",
            "expand": "renderedFields,transitions,changelog",
        }
    )
    issues_url, proxy_host = _proxy_url(proxy_base_url, "rest", "api", "3", "search", "jql", query=issues_query)
    response = do_request(issues_url, headers=headers, allowed_host=proxy_host)

    (output_dir / "jira_issues_response.json").write_text(json.dumps(response, indent=4))

    # List Jira boards using REST 1.0 API
    boards_url, proxy_host = _proxy_url(proxy_base_url, "rest", "agile", "1.0", "board")
    boards_response = do_request(boards_url, headers=headers, allowed_host=proxy_host)

    (output_dir / "jira_boards_response.json").write_text(json.dumps(boards_response, indent=4))

    board_id = boards_response["values"][0]["id"]
    # Get issues for the first board using REST 1.0 API
    board_issues_url, proxy_host = _proxy_url(
        proxy_base_url,
        "rest",
        "agile",
        "1.0",
        "board",
        str(board_id),
        "issue",
        query="expand=renderedFields%2Ctransitions%2Cchangelog",
    )
    issues_response = do_request(
        board_issues_url,
        headers=headers,
        allowed_host=proxy_host,
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

import argparse
import json
import os
import sys
from urllib.parse import quote, urlparse

import requests

token = os.getenv("PROXY_TOKEN")
proxy_base_url = os.getenv("PROXY_BASE_URL", "http://localhost:8000")
gitlab_host = os.getenv("GITLAB_HOST", "gitlab.com")

if token is None:
    print("PROXY_TOKEN environment variable is not set.")
    sys.exit(1)


def _validated_proxy_base_url(base_url):
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        raise ValueError("PROXY_BASE_URL must be an HTTP(S) URL with a host.")
    if parsed.username or parsed.password or parsed.params or parsed.query or parsed.fragment:
        raise ValueError("PROXY_BASE_URL must not include credentials, params, query, or fragment.")
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"


def _proxy_url(base_url, *path_segments):
    safe_base_url = _validated_proxy_base_url(base_url)
    safe_path = "/".join(quote(segment, safe="%") for segment in path_segments)
    return f"{safe_base_url}/{safe_path}"


def list_merge_requests(project_id):
    headers = {
        "X-Guardette-Host": gitlab_host,
        "Authorization": token,
        "Accept": "application/json",
    }

    try:
        url = _proxy_url(proxy_base_url, "api", "v4", "projects", project_id, "merge_requests")
    except ValueError as error:
        print(f"Invalid proxy configuration: {error}")
        return

    response = requests.get(url, headers=headers, timeout=30, allow_redirects=False)

    if response.status_code != 200:
        print(f"Error with status code: {response.status_code}, Message: {response.text}")
        return

    data = response.json()

    for i, mr in enumerate(data[:5]):
        print(f"Merge Request #{i + 1}:")
        print(json.dumps(mr, indent=4))
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List the first 5 merge requests for a given GitLab project.")
    parser.add_argument("project_id", type=str, help="The project ID (numeric or URL-encoded path).")
    args = parser.parse_args()

    list_merge_requests(args.project_id)

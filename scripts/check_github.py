import argparse
import json
import os
from urllib.parse import quote, urlparse

import requests

token = os.getenv("PROXY_TOKEN")
proxy_base_url = os.getenv("PROXY_BASE_URL", "http://localhost:8000")


def _validated_proxy_base_url(base_url):
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        raise ValueError("PROXY_BASE_URL must be an HTTP(S) URL with a host.")
    if parsed.username or parsed.password or parsed.params or parsed.query or parsed.fragment:
        raise ValueError("PROXY_BASE_URL must not include credentials, params, query, or fragment.")
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"


def _proxy_url(base_url, *path_segments):
    safe_base_url = _validated_proxy_base_url(base_url)
    safe_path = "/".join(quote(segment, safe="") for segment in path_segments)
    return f"{safe_base_url}/{safe_path}"


def list_pull_requests(owner, repo):
    if token is None:
        print("PROXY_TOKEN environment variable is not set. ")
        return

    headers = {
        "X-Guardette-Host": "api.github.com",
        "Authorization": token,
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        url = _proxy_url(proxy_base_url, "repos", owner, repo, "pulls")
    except ValueError as error:
        print(f"Invalid proxy configuration: {error}")
        return

    response = requests.get(url, headers=headers, timeout=30, allow_redirects=False)

    if response.status_code != 200:
        print(f"Error with status code: {response.status_code}, Message: {response.text}")
        return

    data = response.json()

    for i, pull_request in enumerate(data[:5]):
        print(f"Pull Request #{i + 1}:")
        print(json.dumps(pull_request, indent=4))
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List the first 5 pull requests for a given GitHub repository.")
    parser.add_argument("owner", type=str, help="The owner of the repository.")
    parser.add_argument("repo", type=str, help="The repository name.")
    args = parser.parse_args()

    list_pull_requests(args.owner, args.repo)

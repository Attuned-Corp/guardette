import argparse
import json
import os

import requests

token = os.getenv("PROXY_TOKEN")
proxy_base_url = os.getenv("PROXY_BASE_URL", "http://localhost:8000")
gitlab_host = os.getenv("GITLAB_HOST", "gitlab.com")

if token is None:
    print("PROXY_TOKEN environment variable is not set.")
    exit(1)


def list_merge_requests(project_id):
    headers = {
        "X-Guardette-Host": gitlab_host,
        "Authorization": token,
        "Accept": "application/json",
    }

    url = f"{proxy_base_url}/api/v4/projects/{project_id}/merge_requests"

    response = requests.get(url, headers=headers)

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

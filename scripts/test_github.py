import requests
import os
import argparse
import json

token = os.getenv('PROXY_TOKEN')
proxy_base_url = os.getenv('PROXY_BASE_URL', 'http://localhost:8000')


def list_pull_requests(owner, repo):
    if token is None:
        print("PROXY_TOKEN environment variable is not set. ")
        return

    headers = {
        'X-Guardette-Host': 'api.github.com',
        'Authorization': token,
        'Accept': 'application/vnd.github.v3+json',
    }

    url = f'{proxy_base_url}/repos/{owner}/{repo}/pulls'

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Error with status code: {response.status_code}, "
              f"Message: {response.text}")
        return

    data = response.json()

    for i, pull_request in enumerate(data[:5]):
        print(f'Pull Request #{i+1}:')
        print(json.dumps(pull_request, indent=4))
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='List the first 5 pull requests '
                                     'for a given GitHub repository.')
    parser.add_argument('owner', type=str, help='The owner of the repository.')
    parser.add_argument('repo', type=str, help='The repository name.')
    args = parser.parse_args()

    list_pull_requests(args.owner, args.repo)

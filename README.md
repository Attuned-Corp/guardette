# Guardette
A redacting proxy built on FastAPI/Starlette.

## Quick Start
```
cp scripts/policygen.config.example.json policygen.config.json
python scripts/policygen/policygen.py
SECRET_MANAGER=default CLIENT_SECRET=secret python -m uvicorn main:app --reload
```

```
curl -H "Authorization: secret" -H "X-Guardette-Host: hacker-news.firebaseio.com" "http://localhost:8000/v0/item/8863.json?print=pretty"
```

## Environment Variables
You can optionally use a `.env` file.

| Env Variable | Description |
| --- | --- |
| `SECRET_MANAGER` | `aws_secret_manager` or `default` |
| `CLIENT_SECRET` | Used by Guardette clients as a bearer token to access the proxy. Recommend you generate a cryptographically secure random string with ie. `openssl rand -hex 32` |
| `PSEUDONYMIZE_SALT` | Used to pseudonymize PII such as emails |
| `PSEUDONYMIZE_EMAIL_DOMAINS_ALLOWLIST` | Comma separated list of domains whose emails we will NOT pseudonymize |

## Terraform

There are modules provided under `terraform/` that can be used to setup the Guardette proxy as a Lambda Function.

## Development Setup
```
brew install pre-commit
pre-commit install

python -m venv .venv
source .venv/bin/activate
```

### Install Dependencies
```
pip install -e ".[dev]"
```

### Building the Wheel
```
python -m build
```

### Running Tests
```
python -m pytest
```

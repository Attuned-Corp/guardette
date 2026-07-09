# Guardette

Guardette is a **redacting proxy layer** that sits between the REST APIs of data
sources/vendors (e.g., Jira, GitHub, GitLab, Google Workspace Calendar) and clients
that require access to only a subset of that data. It enforces **granular,
policy-driven access control** by redacting, filtering, or removing fields from
requests and responses based on rules defined in a YAML policy file. It can run as
a standalone FastAPI webservice or be deployed as an AWS Lambda function.

## Tech stack in use

- **Language**: Python >=3.13, managed with **Poetry** (`pyproject.toml`, `poetry.lock`)
- **Web framework**: FastAPI / Starlette, served via Uvicorn (or Mangum when running on AWS Lambda)
- **HTTP client**: httpx / aiohttp for proxying requests upstream
- **Policy engine**: YAML policy files (`.guardette/policy.yml`) parsed with `pyyaml` and matched with `jsonpath-ng`
- **Auth backends**: pluggable handlers in `src/guardette/default_auth/` (`basic_auth`, `bearer_token`, `gcp_service_account`), with secrets resolved via env vars or AWS Secrets Manager (`aiobotocore`)
- **Deployment**: Docker (`Dockerfile`) for standalone use, `Dockerfile.awslambda` + `terraform/aws/` for AWS Lambda deployment
- **Testing**: pytest (`tests/`), fixtures in `tests/conftest.py`
- **Linting/formatting**: Ruff (`ruff check`, `ruff format`), configured in `pyproject.toml`
- **CI**: GitHub Actions (`.github/workflows/ci.yaml`) running lint, format check, and pytest
- **Pre-commit**: `.pre-commit-config.yaml` runs `ruff check --fix` and `ruff format` locally before commit

## Project and code guidelines

- Use Poetry for all dependency management (`poetry install`, `poetry add`); do not hand-edit `poetry.lock`.
- Use a local virtual environment for development (`.venv` in the repo root is the preferred local setup) and run commands through it (`.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/ruff`) rather than system Python where practical.
- All GitHub Actions must pin third-party actions to full commit SHA values. Use `pinact` (configured via `.pinact.yml`) to update workflow files; do not leave floating tags such as `@v4` or `@main` in workflow YAML.
- Run `poetry run ruff check .` and `poetry run ruff format --check .` before committing; CI will fail otherwise.
- Line length is 120 characters (see `[tool.ruff]` in `pyproject.toml`).
- Prefer double quotes for strings (`ruff format` quote-style = double).
- Add or update pytest tests under `tests/` for any behavioral change; tests must pass locally (`poetry run pytest`) and in CI.
- Never commit real secrets, credentials, tenant IDs, or customer-specific policy files. Use `.env.example` and sanitized example policies/configs as templates.
- New auth handlers go in `src/guardette/default_auth/`; new redaction/filtering actions go in `src/guardette/default_actions/`. Both are registered and looked up by `kind`/handler name from the policy file.
- Environment variables follow the `AUTH_{HANDLER}_{SUBKIND}_{KEY}` naming convention for auth credentials (see README "Authentication Configuration" section).
- Keep changes narrowly scoped — this project favors small, focused, reviewable PRs over broad refactors (see `docs/draft-prd.md` for the upstream contribution strategy).

## Project structure

- `src/guardette/` : Core application package
  - `proxy.py` : Main proxy request/response handling
  - `policy.py` : Policy file loading and matching
  - `auth.py`, `default_auth/` : Authentication handler registry and built-in handlers (basic auth, bearer token, GCP service account)
  - `actions.py`, `default_actions/` : Redaction/filtering action registry and built-in actions (redact, remove, nullify, pseudonymize_email, filter_regex, redact_secrets, redact_regex)
  - `secrets.py` : Secret resolution (env vars or AWS Secrets Manager backend)
  - `config.py`, `constants.py`, `datastructures.py`, `exceptions.py`, `logging.py`, `matching.py`, `utils.py`, `version.py` : Supporting modules
- `main.py` : FastAPI app entrypoint for standalone/Docker deployment
- `lambda_handler.py` : AWS Lambda entrypoint (via Mangum)
- `scripts/policygen/` : Policy YAML generator
  - `policygen.py` : Reads a `policygen.config.json` and per-source templates to produce `.guardette/policy.yml`
  - `sources/<name>/template.yml` : Per-source (Jira, GitHub, GitLab, Google Workspace Calendar, Hacker News) policy templates
- `scripts/check_*.py` : Manual smoke-test scripts for individual integrations (GitHub, GitLab, Jira, Google Calendar)
- `tests/` : Pytest suite (`test_proxy.py`, `test_actions.py`, `test_secrets.py`, `test_policy.yml` fixture, `conftest.py`)
- `terraform/aws/` : Terraform IaC for AWS Lambda + API Gateway deployment
- `docs/` : Project documentation, including `draft-prd.md` (upstream contribution PRD/plan) and `REDACTION.md`
- `.github/workflows/` : CI workflow definitions

## Resources

- Local development
  - `poetry install` — install all dependencies
  - `poetry run uvicorn main:app --reload` — run the app locally
  - `poetry run pytest` — run the test suite
  - `poetry run ruff check .` / `poetry run ruff format .` — lint / format
  - `poetry run python scripts/policygen/policygen.py --config=policygen.config.json` — generate a `.guardette/policy.yml`
- Docker
  - `docker build -t guardette .` then `docker run ...` (see README "Setup" section for full example with volume mounts and env vars)
  - `docker compose up` — see `docker-compose.yml` for a complete local example
- AWS Lambda deployment
  - `docker build -f Dockerfile.awslambda -t guardette-lambda .`
  - See `terraform/aws/README.md` for full deployment instructions
- Documentation
  - `README.md` — setup, environment variables, authentication configuration, policy format
  - `docs/REDACTION.md` — redaction action details
  - `docs/draft-prd.md` — PRD for upstream contribution baseline (dependency hygiene, linting, type checking, CI/Actions hardening, redaction proxy scope), including a full comparison against a reference internal fork in Appendix A

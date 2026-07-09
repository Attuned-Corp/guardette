# PRD: Guardette Upstream Contribution Baseline

## 1. Purpose

We intend to use Guardette as a supported redaction proxy between Span and our Jira instance.

To avoid maintaining a long-lived internal fork, we will contribute generic improvements back to the upstream `Attuned-Corp/guardette` repository. These contributions will focus first on establishing a minimum engineering and security baseline required for operating the service in our environment, before adding Jira/Span-specific proxy capabilities.

The intent is not to take ownership of Guardette or impose our internal platform model. The intent is to make the upstream project safe, maintainable, testable, and suitable for supported production use.

### 1.1 Reference implementation

This baseline is not speculative: a sibling internal fork, `NewDayCards/guardette` (at `internal checkout`), diverged from the same upstream merge-base (`f04012b`) and has already implemented most of the engineering, security, and Jira-integration scope described in this document. That fork went further than upstream contribution requires — it also replatformed the runtime from AWS Lambda to a container-first Azure deployment model, which is an internal deployment decision, not a generic upstream concern.

This document uses that fork as **evidence and a source of reusable patterns** for the generic, upstream-appropriate parts of the work (dependency hygiene, linting/type-checking, Actions hardening, CI scaffolding, redaction proxy capability), while explicitly excluding the Azure/container-first architecture and other environment-specific decisions from the upstream contribution scope. A full breakdown of every difference between baseline and the reference fork is captured in **Appendix A**.

## 2. Problem Statement

Guardette is the preferred option because Span/Attuned support it. However, before we can run it in our environment, the project needs foundational improvements across dependency management, CI, linting, type checking, GitHub Actions hardening, and application scaffolding.

Without these changes, we would either need to:

1. Carry a divergent internal fork.
2. Accept a lower engineering and security baseline than we normally permit.
3. Build a separate YARP-based proxy, increasing integration and support risk.

The preferred path is to contribute the required generic improvements upstream in small, reviewable pull requests.

## 3. Goals

The goals are:

1. Establish a clean, reproducible Python development baseline.
2. Fix known dependency and Dependabot issues.
3. Add or improve linting, formatting, and type-checking controls.
4. Harden GitHub Actions workflows, including pinning third-party actions to commit SHAs.
5. Add basic CI scaffolding for tests, linting, type checking, and dependency validation.
6. Improve project structure only where needed to support testability and maintainability.
7. Add generic redaction proxy capabilities required for Span-to-Jira use.
8. Keep all customer-specific configuration, credentials, infrastructure, and deployment workflows outside the upstream repository.

## 4. Non-Goals

This work will not:

1. Add our internal Jira URLs, Span tenant details, credentials, project keys, or environment names to the upstream repository.
2. Add our production deployment workflows to the upstream repository unless explicitly requested by Attuned.
3. Convert Guardette into an organisation-specific product.
4. Rewrite the application unnecessarily.
5. Replace the existing packaging or dependency model unless agreed with Attuned.
6. Introduce strict type-checking or broad refactoring in a single change.
7. Create a permanent internal fork as the default operating model.

## 5. Users and Stakeholders

Primary users:

1. Our security engineering team operating the redaction proxy.
2. Span/Attuned support teams responsible for Guardette supportability.
3. Guardette maintainers reviewing upstream contributions.

Secondary users:

1. Platform engineering teams responsible for runtime and deployment environments.
2. Security assurance teams reviewing use of the proxy.
3. Developers or operators who may need to run Guardette locally for testing.

## 6. Target Operating Model

The target flow is:

```text
Span → Guardette redaction proxy → Jira
```

The contribution model is:

```text
generic Guardette improvements → upstream repository
customer-specific configuration → private deployment repository
```

The upstream Guardette repository should contain reusable product improvements, examples, documentation, and tests.

Our private deployment repository should contain environment-specific configuration, infrastructure, secrets references, deployment workflows, and operational runbooks.

## 7. Scope of Contributions

### 7.1 Dependency Hygiene

Add or update dependency management so that Python dependencies are current, reviewed, and maintainable.

Expected outputs:

1. Resolved Dependabot alerts where safe.
2. Updated dependency versions.
3. Clear dependency update process.
4. Lockfile update if the project already uses a lockfile.
5. No unnecessary packaging migration.

Acceptance criteria:

1. Existing tests pass.
2. Dependency updates are minimal and justifiable.
3. No behavioural changes are introduced.
4. Dependabot configuration is valid and scoped.

**Reference fork evidence:** the reference fork moved from Poetry (`poetry.lock`) to uv (`uv.lock`), added `.github/dependabot.yml` covering `uv`, `docker`, and `github-actions` ecosystems, and added `scripts/fetch_action_release.py` with an `action-release-watch.yaml` workflow to flag stale Action pins over time. Whether to propose a Poetry→uv migration upstream (vs. keeping Poetry and only fixing Dependabot config) is an open question — see §13.

### 7.2 Linting and Formatting

Introduce a consistent Python linting and formatting baseline.

Expected outputs:

1. Linting tool configuration, preferably using the project’s existing conventions.
2. Formatting command documented.
3. CI check for linting.
4. Minimal code changes required to pass.

Acceptance criteria:

1. Lint checks run in CI.
2. Local developer command is documented.
3. Formatting changes are mechanical and isolated.
4. No unrelated refactoring is included.

**Reference fork evidence:** Ruff config lives in `pyproject.toml` in both repos; the reference fork additionally adds `[tool.ruff.lint.per-file-ignores]` scoped to non-product tooling directories (`.agents/skills/**`) rather than loosening rules project-wide — a pattern worth reusing if similar tooling directories are introduced upstream.

### 7.3 Type Checking

Introduce a basic type-checking baseline.

Expected outputs:

1. Type-checking configuration.
2. CI check for type checking.
3. Initial annotations or ignores where required.
4. Documented command for local execution.

Acceptance criteria:

1. Type checking runs in CI.
2. Baseline is achievable without major rewrites.
3. Strict mode is not enabled unless the codebase is ready.
4. Any exclusions are explicit and documented.

**Reference fork evidence:** the reference fork runs `uv run ty check .` in CI with Ty's default configuration — no `tool.ty`, `mypy.ini`, or equivalent strict config file was introduced. This confirms a permissive, default-config baseline is achievable without upfront annotation work, supporting the "start permissive, ratchet later" approach in §12.

### 7.4 GitHub Actions Hardening

Harden GitHub Actions usage to reduce CI/CD supply-chain risk.

Expected outputs:

1. Third-party GitHub Actions pinned to full commit SHAs.
2. Comments preserving the original version tag where useful.
3. Minimal workflow permissions.
4. No unrelated CI restructuring in the same PR.

Acceptance criteria:

1. All third-party actions are pinned to full commit SHA.
2. Workflows still execute successfully.
3. Workflow permissions are no broader than required.
4. The PR is limited to CI hardening.

**Reference fork evidence:** the reference fork pins all third-party Actions to commit SHAs, sets `persist-credentials: false` on checkout, adds explicit `permissions:` blocks per workflow, and adds two dedicated security workflows — `zizmor.yaml` (running `zizmorcore/zizmor-action` and `raven-actions/actionlint`) and `codeql.yml` (Python CodeQL analysis, currently reporting 0 findings per `docs/security/codeql-findings.md`). These are strong candidates for direct upstream contribution since they require no environment-specific secrets.

### 7.5 CI and Test Scaffolding

Add a baseline CI structure for tests, linting, type checking, and basic validation.

Expected outputs:

1. CI jobs for tests, linting, and type checking.
2. Basic smoke tests if no meaningful tests currently exist.
3. Documented local commands matching CI.
4. Optional dependency or security check if agreed with Attuned.

Acceptance criteria:

1. CI is reproducible.
2. CI fails on lint, type-check, or test failures.
3. CI jobs are separated clearly.
4. CI does not require internal secrets or private infrastructure.

**Reference fork evidence:** the reference fork splits CI into separate workflows for shared runtime tests, container image build/SBOM/signing, CodeQL, and workflow linting, rather than one monolithic job. It also added local security scanning (`scripts/security-scan.sh`, `trivy.yaml`, Bandit config, OSV-Scanner) as a pre-CI developer step. Note that container image build/SBOM/signing and the Azure/Cloudflare deploy workflows are environment-specific and out of scope for upstream — only the generic test/lint/type-check/security-scan split is applicable here.

### 7.6 Application Scaffolding

Improve project structure only where needed to support maintainability and testing.

Expected outputs may include:

1. Clear application entry point.
2. Configuration loading structure.
3. Test fixtures.
4. Example configuration.
5. Developer documentation.
6. Docker or local runtime support if agreed.

Acceptance criteria:

1. Behaviour is preserved unless a specific behavioural change is agreed.
2. File moves are separated from logic changes where practical.
3. Configuration is generic and environment-neutral.
4. Local run instructions are clear.

**Reference fork evidence:** the reference fork moved runtime code under `src/` and introduced a platform-neutral core (`src/guardette/*`) with thin, swappable adapters selected via an `APP_TARGET` environment variable, plus a `PlatformSecretsManager` abstraction so secret resolution (Key Vault, App Configuration, env vars) is decoupled from application logic. **This full platform-adapter/`APP_TARGET` restructuring reflects the reference fork's specific Azure/Cloudflare multi-target deployment needs and is judged out of scope for upstream** — upstream Guardette need only support one deployment target well. However, the underlying principle (secret resolution and config loading isolated from business logic, via a small abstraction) is a reusable pattern worth proposing in a lighter form, without committing upstream to multi-platform adapters.

### 7.7 Generic Redaction Proxy Capability

Add the reusable capability needed to operate Guardette as a redaction proxy for Jira-compatible APIs.

Expected outputs:

1. Configurable upstream target URL.
2. Configurable request redaction rules.
3. Configurable response redaction rules.
4. Header allowlist/blocklist support.
5. Query parameter redaction.
6. JSON body redaction.
7. Basic audit logging that avoids leaking sensitive values.
8. Sanitised example configuration.

Acceptance criteria:

1. Redaction rules are configuration-driven.
2. Jira-specific behaviour is generic enough to be reusable.
3. Tests cover headers, query parameters, JSON request bodies, and JSON response bodies.
4. No customer-specific URLs, field names, credentials, or tenant identifiers are committed.
5. Documentation explains how to adapt the configuration for Jira-like APIs.

**Reference fork evidence:** the reference fork implements exactly this capability and more:
- **Redaction**: `scripts/policygen/policygen.py` and `config/policy.*.yml` cover client-alias redaction, non-corporate email detection, card-number-like/JWT-like/base64 token patterns, UK postcode/address-like patterns, and broaden redaction across summaries, descriptions, comments, worklogs, changelog items, display names, and email fields. A sanitised example lives at `docs/guardette/policy.jira.example.yml`.
- **Inbound auth rotation**: dual rotatable secrets (`GUARDETTE_SECRET_1`/`GUARDETTE_SECRET_2`) with constant-time comparison, replacing a single static `CLIENT_SECRET` — directly reusable and low-risk to propose upstream.
- **Outbound Jira auth**: a corrected Basic Auth credential model (`username`+`token`, matching Atlassian API tokens, vs. the current `username`+`password`) plus a new OAuth 2.0 client-credentials flow (`src/guardette/default_auth/oauth_client_credentials.py`) with **per-route auth override** (e.g., `/rest/dev-status/1.0/issue/detail` must stay on Basic Auth against the tenant domain because it isn't exposed through Atlassian's OAuth gateway). This per-route override capability is itself a generic, reusable policy-engine feature, independent of any customer's specific Jira tenant.
- **Tests**: `tests/test_jira_span_pack.py`, `tests/test_jira_live_redaction.py`, and `tests/test_policygen.py` demonstrate coverage patterns, including opt-in live tests against real Jira that avoid persisting issue content.

The Basic Auth credential fix (§7.7, `username`+`token`) is a strict correctness bug fix independent of the OAuth feature and should be prioritised as its own small PR.

## 8. Proposed PR Sequence

The work should be delivered as a sequence of small PRs.

### PR 1: Dependency and Dependabot Baseline

Purpose: Resolve immediate dependency hygiene issues.

Scope:

1. Update Python dependencies.
2. Fix Dependabot configuration.
3. Preserve existing packaging approach.

Out of scope:

1. Toolchain migration.
2. Refactoring.
3. Feature work.

### PR 2: Linting and Formatting Baseline

Purpose: Establish consistent code quality checks.

Scope:

1. Add linting configuration.
2. Add formatting configuration if appropriate.
3. Make minimal mechanical changes to pass.

Out of scope:

1. Large-scale refactoring.
2. Behaviour changes.

### PR 3: Type Checking Baseline

Purpose: Establish basic type-safety checks.

Scope:

1. Add type-checking configuration.
2. Add CI command.
3. Make minimal annotations or exclusions.

Out of scope:

1. Strict typing across the entire codebase.
2. Broad rewrites.

### PR 4: GitHub Actions SHA Pinning

Purpose: Reduce GitHub Actions supply-chain risk.

Scope:

1. Pin third-party Actions to full commit SHAs.
2. Preserve tag comments where useful.
3. Tighten permissions if low-risk.

Out of scope:

1. Redesigning the CI pipeline.
2. Adding deployment workflows.

### PR 5: CI and Test Scaffolding

Purpose: Make the project consistently testable.

Scope:

1. Add CI jobs for tests, linting, and type checking.
2. Add smoke tests if needed.
3. Document local commands.

Out of scope:

1. Full test suite rewrite.
2. Internal deployment integration.

### PR 6: Application Configuration Scaffolding

Purpose: Prepare the app for safe proxy configuration.

Scope:

1. Add generic configuration structure.
2. Add example config.
3. Add validation around required settings.

Out of scope:

1. Customer-specific config.
2. Secrets management integration specific to our environment.

### PR 7: Generic Redaction Proxy Support

Purpose: Add the reusable redaction proxy capability required for Span-to-Jira.

Scope:

1. Configurable routing to target API.
2. Request and response redaction.
3. Header/query/body rules.
4. Tests and documentation.

Out of scope:

1. Internal Jira configuration.
2. Span tenant configuration.
3. Production deployment workflows.

### PR 8: Jira Basic Auth Credential Fix

Purpose: Correct the Basic Auth credential model for Jira API-token authentication.

Scope:

1. Change `secret_keys` from `["username", "password"]` to `["username", "token"]` to match Atlassian API-token auth.
2. Update documentation and example configuration accordingly.
3. Add/adjust tests covering the corrected credential model.

Out of scope:

1. OAuth client-credentials support (see PR 9).
2. Internal Jira tenant configuration.

### PR 9 (optional/later): Jira OAuth Client-Credentials Support

Purpose: Support OAuth 2.0 client-credentials as an alternative outbound auth method for Jira, with per-route auth override.

Scope:

1. Generic OAuth client-credentials auth module.
2. Per-route auth override in the policy engine (some endpoints may not be reachable via a given auth method).
3. Sanitised example configuration and documentation.
4. Tests covering token acquisition, request rewriting, and per-route override behaviour.

Out of scope:

1. Internal Jira Cloud ID, client ID/secret, or tenant-specific routing.
2. Broader multi-platform secret-store integration (Key Vault/App Configuration) — that remains in the private deployment repository.

This PR is lower priority than PR 8 and should only be proposed if Attuned confirms interest in OAuth support upstream (see §13).

## 9. Repository Boundary

### Upstream Guardette Repository

May include:

1. Generic source code improvements.
2. Generic redaction logic.
3. Generic Jira-compatible examples.
4. Tests.
5. Documentation.
6. CI checks.
7. Development tooling configuration.

Must not include:

1. Internal Jira URLs.
2. Span tenant IDs or private integration details.
3. Secrets or secret references tied to our environment.
4. Production deployment workflows.
5. Internal infrastructure code.
6. Internal project keys or issue schemas.
7. Non-sanitised redaction rules.

### Private Deployment Repository

Should include:

1. Environment-specific configuration.
2. Production and non-production deployment workflows.
3. Infrastructure-as-code.
4. Secret references.
5. Internal operational runbooks.
6. Internal Jira and Span configuration.
7. Environment-specific redaction policy.

## 10. Security Requirements

The contributed baseline should support the following security properties:

1. No secrets committed to the repository.
2. Third-party GitHub Actions pinned to full commit SHA.
3. Minimum required GitHub Actions permissions.
4. Redaction before data reaches Jira where configured.
5. No sensitive values emitted in logs.
6. Tests for redaction logic.
7. Configuration-driven handling of sensitive fields.
8. No customer-specific identifiers in upstream examples.
9. Clear separation between product code and deployment configuration.

## 11. Engineering Requirements

The project should support:

1. Reproducible local development.
2. Repeatable CI checks.
3. Clear test command.
4. Clear lint command.
5. Clear type-check command.
6. Documented configuration model.
7. Small, reviewable PRs.
8. Minimal behavioural change per PR.
9. Compatibility with the existing project direction unless otherwise agreed.

## 12. Risks

### Risk: Maintainers reject broad tooling changes

Mitigation: Agree tooling preferences before implementation and keep PRs narrow.

### Risk: PRs become too large to review

Mitigation: Split dependency, linting, typing, CI, scaffolding, and feature work into separate PRs.

### Risk: Internal assumptions leak upstream

Mitigation: Use sanitised examples and keep environment-specific configuration in a private repo.

### Risk: We create a de facto fork anyway

Mitigation: Prioritise upstream mergeability and avoid internal-only source changes.

### Risk: Type checking becomes invasive

Mitigation: Start with a permissive baseline and ratchet later.

### Risk: CI hardening breaks maintainer workflows

Mitigation: Keep workflow changes minimal and test each PR independently.

## 13. Open Questions

1. Does Attuned have preferred tooling for linting, formatting, and type checking? (The reference fork uses Ruff + Ty via uv — worth proposing as a concrete starting point rather than an open-ended question.)
2. Does the project have an intended packaging strategy? Specifically: is a Poetry→uv migration acceptable upstream, or should Dependabot/dependency fixes be made within the existing Poetry setup?
3. Should GitHub Actions SHA pinning, zizmor, actionlint, and CodeQL be accepted upstream, or should they be limited to our fork? These require no secrets or environment-specific config, so they seem low-risk to propose.
4. What level of Jira-specific example configuration is acceptable upstream, and is Attuned interested in an OAuth client-credentials auth option (with per-route override) in addition to Basic Auth?
5. Does Attuned want Docker, Compose, or Kubernetes examples? (Confirmed out of scope: the reference fork's Azure App Service/Container Apps/Bicep and Cloudflare Workers deployment paths are internal decisions and will not be proposed upstream.)
6. Who will review and approve upstream PRs?
7. What support boundary will exist between upstream Guardette and our private deployment overlay?
8. Should AWS Secrets Manager support remain in the upstream codebase as an optional secret-source, or is a simple env-var-only model preferred, leaving all cloud-specific secret resolution (Key Vault, Secrets Manager, etc.) to the private deployment repository?

## 14. Success Criteria

This work is successful when:

1. Guardette can be built, linted, type-checked, and tested in CI.
2. Known dependency hygiene issues are addressed or explicitly tracked.
3. GitHub Actions workflows are pinned and minimally permissioned.
4. Generic redaction proxy behaviour is tested and documented.
5. Our environment-specific configuration remains outside the upstream repo.
6. Attuned accepts the contribution model and merges the foundational PRs.
7. We can deploy Guardette internally without maintaining a material long-lived fork.

## 15. Recommended Initial Message to Attuned

We are planning to use Guardette as the supported redaction proxy between Span and our Jira instance. We want to avoid carrying a long-lived fork, so our preference is to contribute generic improvements upstream.

Before we can run it in our environment, we need to bring a few engineering controls up to our baseline. The main areas are Python dependency hygiene, linting, type checking, CI reliability, pinned GitHub Actions, and basic application/test scaffolding.

To keep review manageable, we propose contributing these as small, focused PRs rather than one large change:

1. Dependency and Dependabot baseline
2. Linting and formatting baseline
3. Type-checking baseline
4. GitHub Actions SHA pinning
5. CI and test scaffolding
6. Generic configuration scaffolding
7. Redaction proxy improvements needed for the Span/Jira integration

We will keep our environment-specific deployment configuration, credentials, Jira URLs, Span configuration, and internal workflows out of the upstream repository.

Please confirm whether this sequencing works for you, and whether you have tooling preferences for linting, type checking, packaging, or CI before we start opening PRs.

## Appendix A: Full Fork Divergence Analysis

The following is the complete comparison between this baseline repository and the reference fork (`NewDayCards/guardette`), supporting the claims and PR scoping made above.


### Purpose
This document captures the delta between:

- **BASELINE** — this repository (`NewDayTechnology/guardette`), currently rebased and in sync with upstream `Attuned-Corp/guardette` (`origin/main` == `upstream/main` at commit `2d43a05`).
- **ENHANCED** — a sibling fork at `internal checkout` (`NewDayCards/guardette`, `main` at commit `016bd6d`), which diverged from the same upstream merge-base (`f04012b`, "Span Autofix VULN-308: Upgrade aiohttp to 3.14.0") and has since applied ~28 merged commits of security, tooling, architecture, and feature work.

The goal is to record what changed, why, and what would be required to port the ENHANCED work into this baseline, so the two lines can be reconciled or the enhancements re-applied deliberately.

### Summary
The ENHANCED fork is not a small patch set — it is a **full replatforming** layered with a **security hardening pass** and a **new Jira OAuth integration**. At a glance:

| Dimension | Baseline | Enhanced |
|---|---|---|
| Package manager | Poetry (`poetry.lock`) | uv (`uv.lock`), Poetry removed |
| Deploy target | AWS Lambda (Mangum) via Terraform | Azure App Service for Containers (container-first), Cloudflare sandbox |
| Runtime layout | `main.py` / `lambda_handler.py` at repo root | `src/guardette/*` platform-neutral core + thin adapters via `APP_TARGET` |
| IaC | `terraform/aws/*` | `azure/*.bicep` |
| Inbound auth | Single `CLIENT_SECRET` | Rotatable `GUARDETTE_SECRET_1` / `GUARDETTE_SECRET_2` |
| Outbound Jira auth | `basic_auth:jira` only | OAuth 2.0 client-credentials default, per-route `basic_auth` override |
| Secrets store | AWS Secrets Manager (`aiobotocore`) | Azure Key Vault + App Configuration (`DefaultAzureCredential`) |
| CI/security scanning | Ruff + pytest only | + CodeQL, zizmor, actionlint, Dependabot (uv/docker/actions), Bandit, OSV-Scanner, Trivy |
| Docs | `draft-prd.md`, `REDACTION.md` | Reorganized into `adr/`, `prd/`, `specs/`, `security/`, `guardette/`, `cloudflare/`, `import/` |

---

### 1. Tooling & CI Fixes

#### 1.1 Packaging / dependency management
- Baseline: `pyproject.toml` is a Poetry-managed distributable package (`[tool.poetry]`, `poetry-core` build backend), with `poetry.lock` and a `.pre-commit-config.yaml` invoking `poetry run ruff …`.
- Enhanced: `pyproject.toml` becomes a repo/runtime tool environment (`name = "guardette-repo-tools"`, `[tool.uv] package = false`), Poetry sections and `poetry.lock` removed (commit `d8cf168` "Remove Poetry lockfile"), `uv.lock` added, `.pre-commit-config.yaml` removed, workflows/README standardized on `uv sync --frozen --dev`, `uv run pytest`, `uv run ruff …`.

#### 1.2 Ruff / ty (type checker)
- Both keep Ruff config in `pyproject.toml`.
- Enhanced adds `[tool.ruff.lint.per-file-ignores]` for `.agents/skills/**` and runs `uv run ty check .` in CI. Neither repo carries a dedicated `tool.ty`/mypy config; Ty runs with defaults.

#### 1.3 GitHub Actions / actionlint / zizmor
- Baseline: single `.github/workflows/ci.yaml` using floating tags (`actions/checkout@v6`, `actions/setup-python@v6`), Poetry install, Ruff + pytest.
- Enhanced: split into multiple workflows — `ci.yaml`, `ci-container-image.yml`, `codeql.yml`, `deploy-azure.yml`, `deploy-sandbox.yml`, `zizmor.yaml`, `action-release-watch.yaml`. Third-party actions pinned to commit SHAs, `persist-credentials: false` on checkout, explicit `permissions:` blocks, path filters to limit unnecessary runs. `zizmor.yaml` runs `zizmorcore/zizmor-action` and `raven-actions/actionlint` against workflow files. `action-release-watch.yaml` + `scripts/fetch_action_release.py` track stale/outdated action pins over time.

#### 1.4 CodeQL & Dependabot
- Baseline: neither present.
- Enhanced: `codeql.yml` runs Python CodeQL analysis (deps installed via uv); latest local scan recorded in `docs/security/codeql-findings.md` shows 0 findings. `.github/dependabot.yml` added covering `uv`, `docker`, and `github-actions` ecosystems.

---

### 2. Security Fixes

#### 2.1 Inbound secret rotation
- Baseline: single `CLIENT_SECRET` gate.
- Enhanced: `src/guardette/proxy.py` accepts either `GUARDETTE_SECRET_1` or `GUARDETTE_SECRET_2` (constant-time `compare_digest`), enabling zero-downtime secret rotation.

#### 2.2 Removal of AWS-specific secret path
- Baseline: `src/guardette/secrets.py` supports `SECRET_MANAGER=aws_secret_manager` via `aiobotocore` + AWS Secrets Manager with TTL caching.
- Enhanced: AWS Secrets Manager path and `aiobotocore`/`types-aiobotocore[secretsmanager]` removed entirely; replaced by a `PlatformSecretsManager`/`APP_TARGET` abstraction that expects the platform (Azure Key Vault, App Configuration) to resolve secrets into env vars before the app runs.

#### 2.3 Redaction hardening
Enhanced substantially expands PII/secret redaction in `scripts/policygen/policygen.py` and `config/policy.{production,non-production}.yml` / `config/policy.jira.example.yml`:
- Client alias detection (e.g., named customer/brand references)
- Non-corporate email address detection
- Card-number-like, JWT-like, and long base64/base64url token patterns
- UK postcode and address-like patterns
- Short numeric identifiers / sort-code-like values
- Broadened targets: summaries, descriptions, comments, worklogs, changelog items, display names, email fields

#### 2.4 Jira credential model correction
- Baseline: `src/guardette/default_auth/basic_auth.py` used `secret_keys=["username", "password"]`.
- Enhanced: corrected to `secret_keys=["username", "token"]`, aligning with Atlassian API-token authentication (documented in `docs/guardette/jira-basic-auth.md`).

#### 2.5 Container/runtime hardening
From commit `50c0016` ("add local security scanning"):
- `Dockerfile` pinned to a Chainguard Python base image by digest, runs as non-root (`USER 65532`), adds `HEALTHCHECK` against `/api/heartbeat`.
- Local scanning added: `scripts/security-scan.sh`, `trivy.yaml`, Bandit configuration in `pyproject.toml`, plus OSV-Scanner usage.

#### 2.6 Workflow hardening
OIDC-based Azure login in CI/deploy workflows, digest-pinned image deployment in `deploy-azure.yml`, repo-wide action SHA pinning, zizmor/actionlint checks as noted in §1.3.

---

### 3. Architecture Rearchitecture (Container-First)

Reference: `docs/adr/architecture.md` (Accepted), `docs/prd/deployment-prd.md`, `docs/specs/app-service-custom-containers.md`.

#### Decision
> "Guardette adopts a container-first runtime model": Azure App Service for Containers is the production target; the Azure Functions path (and, in this fork's lineage, the AWS Lambda path) is deprecated/removed; FastAPI application logic is shared and platform-neutral; platform-specific behavior is isolated to thin adapters selected via `APP_TARGET`; secrets are consumed as env vars only (platform stores resolve them upstream); CI/CD deploys immutable image digests with SBOM + vulnerability scan + signing.

#### Structural changes
- Baseline: `main.py`, `lambda_handler.py`, `Dockerfile`, `Dockerfile.awslambda` at repo root; `terraform/aws/*` for AWS Lambda + API Gateway.
- Enhanced: runtime moved under `src/` — `src/main.py`, `src/guardette/platform.py`, `src/guardette/azure.py`, `src/guardette/cloudflare.py`, plus shared core modules. New top-level dirs: `config/`, `azure/`, `cloudflare/`, `bruno/`, and an expanded `docs/`.

#### New runtime behaviors
- `/api/heartbeat` and `/api/_guardette/refresh` endpoints
- Warmup path handling and platform adapter selection via `APP_TARGET`
- Optional default-source-host behavior when a policy has a single source
- Richer request/upstream duration logging
- `DISABLE_INCOMING_TRAFFIC` kill switch

#### Noted inconsistency to resolve
Docs/workflows describe **Azure App Service (custom containers)** as the accepted production target, but the committed `azure/guardette-dev01.bicep` currently provisions **Azure Container Apps** — an earlier/dev-path example that has not yet been reconciled with the ADR. This should be tracked as a follow-up item before treating the Bicep as production-ready.

---

### 4. New Feature: OAuth Authentication to Jira

Docs: `docs/guardette/jira-auth-by-endpoint.md`, `jira-basic-auth.md`, `span-jira-integration.md`, `client-info-policy.md`, `policy.jira.example.yml`.
Code: `src/guardette/default_auth/oauth_client_credentials.py`, `src/guardette/policy.py` (per-rule `auth` override), `scripts/policygen/policygen.py`.

#### Behavior
1. **Client → Guardette**: inbound request authenticated via rotatable `GUARDETTE_SECRET_1`/`GUARDETTE_SECRET_2` (see §2.1).
2. **Guardette → Jira (default)**: OAuth 2.0 client-credentials flow using `JIRA_CLIENT_ID`, `JIRA_CLIENT_SECRET`, `JIRA_CLOUD_ID`; requests are rewritten onto `api.atlassian.com/ex/jira/{cloudId}/...`.
3. **Per-endpoint override**: `/rest/dev-status/1.0/issue/detail` remains on the tenant domain and uses Basic Auth (`AUTH_BASIC_AUTH_JIRA_USERNAME` / `AUTH_BASIC_AUTH_JIRA_TOKEN`), since this endpoint is not exposed through the Atlassian OAuth gateway.

#### Net-new vs. baseline
Baseline only supported source-level `basic_auth:jira` for all Jira routes. Enhanced adds: OAuth 2LO (2-legged OAuth) flow, per-endpoint auth selection in the policy generator, committed example/prod/non-prod Jira policies, and tests validating gateway rewrite vs. tenant-domain direct calls (`tests/test_jira_span_pack.py`, `tests/test_jira_live_redaction.py`).

---

### 5. Azure Key Vault Compatibility

Baseline has no Key Vault references. Enhanced adds:
- `src/guardette/az_app_config.py` — optional Azure App Configuration bootstrap using `DefaultAzureCredential`, resolving Key-Vault-backed references for keys prefixed `GUARDETTE_*`, `AUTH_*`, `CLIENT_SECRET`, `PSEUDONYMIZE_*`.
- `config/clusters/ndc-d1/apps/guardette.yml` — App Service configuration referencing Key Vault secrets for `APPLICATIONINSIGHTS_CONNECTION_STRING`, `GUARDETTE_SECRET_1`, `UPSTREAM_API_KEY`.
- `azure/guardette-dev01.bicep` — provisions the Key Vault itself, injects secrets into the runtime, and assigns the "Key Vault Secrets User" role to the app's managed identity.

---

### 6. Bicep / Infrastructure-as-Code

- Baseline: `terraform/aws/*` (`main.tf`, `lambda.tf`, `api_gateway.tf`, `outputs.tf`, `variables.tf`) — provisions AWS Lambda container function, API Gateway HTTP API, IAM role/policy.
- Enhanced: `azure/main.bicep` (subscription-scope resource group) and `azure/guardette-dev01.bicep` (Log Analytics workspace, Azure Container Registry, Key Vault, Container Apps managed environment, Container App with system-assigned identity, secret refs, ACR pull + Key Vault RBAC).
- **Gap**: no Bicep for App Service for Containers exists yet in-repo even though that is the ADR-accepted production target; the App Service path today is expressed only via `config/clusters/ndc-d1/apps/guardette.yml` and `.github/workflows/deploy-azure.yml`. This is a candidate follow-up work item (see §10).

---

### 7. Other Tooling Additions

- **Bruno** (`bruno/guardette/*`, `bruno/jira-postman-sample/*`): executable API collections for Guardette/Jira smoke tests and redaction verification.
- **Cloudflare** (`cloudflare/README.md`, `wrangler.toml`, `src/index.js`): explicitly a sandbox/experimentation runtime, not the production path.
- **Agent tooling** (`.agents/skills/*`): repo-specific Copilot/agent workflow scaffolding, not core runtime functionality.
- **Scripts**: `scripts/fetch_action_release.py`, `scripts/generate_jira_sample_collection.py`, `scripts/jira_pii_discovery.py`, `scripts/security-scan.sh`.
- **Docs reorganization**: baseline had `draft-prd.md` and `REDACTION.md`; enhanced reorganizes into `docs/{README.md, adr/, prd/, specs/, security/, guardette/, cloudflare/, import/}`.

---

### 8. Testing

- Baseline: `tests/test_actions.py`, `tests/test_proxy.py`, `tests/test_secrets.py`.
- Enhanced additions: `tests/test_platform_adapter.py`, `tests/test_policygen.py`, `tests/test_jira_span_pack.py`, `tests/test_jira_live_redaction.py`, `tests/test_fetch_action_release.py`, `tests/fixtures/live_jira_pii_issue_keys.json`.
- Removed: `tests/test_secrets.py` (consistent with AWS Secrets Manager removal).
- New coverage areas: platform adapter selection via `APP_TARGET`, Jira policy-generation correctness, secret rollover, `/api/_guardette/refresh` behavior, `DISABLE_INCOMING_TRAFFIC` behavior, per-rule Jira basic-auth override, OAuth route rewrite to the Atlassian gateway, expanded Jira redaction behavior, and opt-in live tests against real Jira that avoid persisting issue content.

---

### 9. Dependency Management

- Baseline: Poetry-managed package with `poetry.lock`; Lambda extra (`mangum>=0.17.0`); AWS deps (`aiobotocore`, `types-aiobotocore[secretsmanager]`).
- Enhanced: uv-managed with `uv.lock`; no Poetry, no Lambda extra, no Mangum. Removed direct deps: `aiobotocore`, `types-aiobotocore[secretsmanager]`, `sniffio`, explicit `yarl`, pinned `aiohttp==3.14.0`. Added: `jinja2`, `requests`, `workers-runtime-sdk` (Cloudflare), dev-only `bandit`, `workers-py`. Version bumps: `fastapi >=0.103.2 → >=0.138.0`, `httpx >=0.25.0 → >=0.28.1`, `starlette` constraint normalized/updated.

---

### 10. Recommended Follow-ups / Open Questions

1. Decide whether to reconcile this baseline with the ENHANCED fork wholesale (adopt container-first architecture) or selectively cherry-pick security/tooling fixes (CodeQL, zizmor, actionlint, Dependabot, secret rotation, redaction hardening) independent of the Azure/Lambda platform decision.
2. Resolve the Bicep/ADR mismatch: either add an App Service for Containers Bicep module to match the accepted architecture, or update the ADR/docs to reflect Container Apps as the actual target.
3. If porting the Jira OAuth work, confirm which endpoints (e.g., `/rest/dev-status/1.0/issue/detail`) are known to be unsupported by the Atlassian OAuth gateway and require the Basic Auth override, and keep this list current as Atlassian's API surface evolves.
4. Confirm whether the Cloudflare sandbox and Bruno collections should be carried over as-is, adapted, or dropped, since they are explicitly out of scope for production per the ADR.
5. Evaluate whether AWS Secrets Manager support should be retained as an additional platform adapter (multi-cloud) or fully retired in favor of Azure Key Vault/App Configuration, consistent with the current single-cloud direction of the ENHANCED fork.

---

### Appendix: Source Commits (Enhanced fork, since merge-base `f04012b`)
```
016bd6d style: clean up remaining lint/type findings in src
50c0016 chore: add local security scanning (bandit, osv-scanner, trivy)
8ea7970 salvage: port valuable assets from PR #16 (platform engineering WebApp.SiteContainer attempt)
1ae80ef Merge chore/repo-agent-tooling into main
63d8863 Merge feat/azure-bicep-iac into main
8b2d4dd Merge feat/cloudflare-sandbox-worker into main
3fa7133 Merge feat/bruno-jira-collections into main
2fbd94c Merge ci/container-workflows into main
5f6504d Merge feat/container-first-migration into main
951136b fix: address PR #18 review comments
ffaa55e Merge branch 'main' into feat/container-first-migration
cf712bf docs: add container-first architecture ADR, PRD, and reorganised docs (#17)
960a281 chore: add shared agent skill tooling and repo attributes
77b3b7c feat: add Bruno collections and Jira sample generator tooling
759cd5a feat: add Azure Bicep IaC for App Service for Containers
28064c9 feat: add Cloudflare Containers sandbox worker
e92e255 feat: add fetch_action_release script for action-release-watch workflow
be3cd63 feat: add container-first CI/CD workflows
c65a3f5 chore: remove legacy FunctionApp.Python313 CI
6b981eb feat!: remove FunctionApp.Python313 (Azure Functions deployment path)
b02c574 test: port and add tests for the container-first runtime
1f81cc5 build: switch root packaging to container-first layout
4fed018 feat: add platform adapter layer and FastAPI entrypoint
588d2b2 feat: add shared guardette package modules (platform-neutral core)
2da224e SPECT-4229: cd flow with default repo target (#15)
21eccea SPECT-4229: Guardette as FunctionApp.Python313 (#11)
d8cf168 Remove Poetry lockfile (#9)
e6aec2d Azure Function App rearchitecture (#1)
```

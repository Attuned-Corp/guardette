# Guardette Observability Options

**Status:** Proposed
**Scope:** Application-only
**Related documents:**

- `.client/guardette/01-prd-observability.md`
- `.client/guardette/02-note-cloudflare-logs.md`

## Decision summary

Start with a small, explicitly enabled request/response observability slice:

- structured JSON events to `stdout`;
- one request-boundary middleware in the FastAPI application;
- request and response metadata plus a strict safe-header allowlist;
- no request or response bodies;
- no authentication or credential-bearing headers;
- a few low-cardinality operational metrics;
- no tracing or direct OTLP exporter in the first implementation.

Keep the implementation behind a discrete `guardette.observability` module with no-op behavior when disabled. Cloudflare log collection, Grafana routing, and deployment-specific exporters remain outside this repository.

## Context

The full observability PRD describes an adapter-based architecture with independent feature flags, correlation identifiers, structured stdout, metrics, tracing, and sensitive-data tests. The Cloudflare logging note correctly identifies structured container logs and operational metrics as the highest-value starting point for the current proxy flow.

The current application is simpler than the full PRD assumes:

- FastAPI creates the application in `main.py`.
- Guardette registers the proxy route and currently logs request lifecycle events inside `proxy.py`.
- `logging.py` serializes arbitrary `logging` extras, so a caller can accidentally emit fields that were not reviewed for sensitivity.
- Existing request logging includes raw URLs, client/proxy host values, exception strings, and the complete policy model.
- No OpenTelemetry or metrics dependency is currently required by the application.

The first change should improve request visibility without turning every policy, action, authentication, and secret boundary into an instrumentation concern.

## Goals

1. Make request and response behavior diagnosable from safe structured events.
2. Make logging opt-in and disabled by default.
3. Capture useful headers without allowing authentication material into telemetry.
4. Record a small set of stable, low-cardinality metrics.
5. Keep the FastAPI integration and application changes small.
6. Leave a clean extension point for OpenTelemetry later.

## Non-goals

The first implementation will not:

- capture request or response bodies;
- capture raw query strings;
- capture arbitrary request or response headers;
- record authorization, cookies, API keys, tokens, secrets, or credential values;
- add distributed tracing;
- send telemetry directly to Grafana Cloud, Tempo, Loki, or Cloudflare APIs;
- instrument every policy action, secret lookup, or authentication handler;
- add Cloudflare deployment workflows or configuration to this repository;
- expose a new metrics endpoint unless a later implementation explicitly selects that option.

## Options

### Option A: Structured stdout only

The application emits explicit JSON request/response events through the standard Python logging framework. Cloudflare Containers, local Docker, or another runtime collects `stdout` and `stderr`.

**Advantages**

- Smallest dependency and code footprint.
- Works locally and in Cloudflare Containers.
- Keeps exporter failures out of request processing.
- Matches the existing Cloudflare logging note.

**Trade-offs**

- Metrics are initially observations in structured events rather than native time-series instruments.
- Queries, aggregation, retention, and alerting are deployment concerns.
- A later exporter must preserve the event schema and metric dimensions.

**Cloudflare caveat:** Numeric fields in JSON logs do not automatically become native Cloudflare metrics. If container stdout is surfaced in the relevant Cloudflare log view, the fields can be searched and aggregated as logs; native metric dashboards and alerts require a separate metrics path. The deployment repository must verify how the deployed Container/Worker combination exposes container logs before relying on Cloudflare Observability for them.

### Option B: Direct OTLP from the application

The application creates OpenTelemetry providers and exports logs, metrics, or traces directly to a configured OTLP endpoint.

**Advantages**

- Native telemetry signals and standard backend integration.
- Direct routing to Grafana Cloud or another OTLP-compatible service.
- Supports traces and metrics without changing event semantics later.

**Trade-offs**

- Adds SDK/exporter dependencies and lifecycle configuration.
- Requires bounded asynchronous export and explicit failure behavior.
- Introduces endpoint, credential, batching, retry, and shutdown concerns into the application.
- Is unnecessary for the first request/response slice.

**Recommendation:** Keep as a follow-on adapter after the event model and metric dimensions have stabilised.

### Option C: Collector or Grafana Alloy

The application emits safe stdout or OTLP, and a collector handles batching, enrichment, routing, and export.

**Advantages**

- Centralises credentials, retries, routing, and backend changes.
- Avoids vendor-specific exporter logic in the application.
- Suits production environments with several services.

**Trade-offs**

- Requires deployment infrastructure and operational ownership.
- Does not reduce the need for safe application-side redaction.
- Belongs primarily in the deployment repository.

**Recommendation:** Evaluate when multiple services or external telemetry backends justify a collector. Do not make it a prerequisite for the first application change.

## Recommended first slice

### Module boundary

Add a small `src/guardette/observability/` package containing only the first-slice concerns:

- configuration and feature-flag parsing;
- safe request/response field extraction;
- request lifecycle event construction;
- a small metrics recorder interface;
- stdout adapters and no-op implementations;
- FastAPI/ASGI middleware registration.

The middleware should be installed once during application setup. Core policy, action, authentication, secret, and transformation code should not gain feature-flag checks in this slice.

### Feature flags

Use explicit environment configuration with safe defaults:

```text
OBS_ENABLED=false
OBS_REQUEST_LOGGING_ENABLED=false
OBS_METRICS_ENABLED=false
```

`OBS_ENABLED` is the master switch. A signal is active only when both the master switch and its signal flag are enabled. No observability handler, middleware emission, or metric recording should be active when the master switch is false.

Do not make the safe-header list configurable through an environment variable. A code-reviewed allowlist is safer than allowing production configuration to expand telemetry fields.

### Request/response event

Emit one completed event for each observed request, with error and rejection events only when needed. Use explicit fields rather than serializing arbitrary logging extras.

Allowed event fields:

```json
{
  "event": "guardette.request.completed",
  "request_id": "opaque-id",
  "method": "GET",
  "route": "/{path:path}",
  "status_code": 200,
  "status_class": "2xx",
  "duration_ms": 12.4,
  "headers": {
    "request": {
      "accept": "application/json",
      "content-type": "application/json",
      "user-agent": "client"
    },
    "response": {
      "content-type": "application/json"
    }
  },
  "error_class": null,
  "service": "guardette",
  "environment": "production",
  "version": "git-sha"
}
```

The exact route should be the normalized FastAPI route template where available, not the raw path. Never record the query string. `request_id` must be opaque and may be generated by the application when no trusted incoming identifier is available.

The response should include the opaque request identifier when the application already controls the response. This allows a safe log lookup without exposing request content.

### Safe header policy

Use an explicit allowlist of low-risk header names. The initial list should be deliberately small, for example:

- `accept`;
- `content-type`;
- `user-agent`;
- `cf-ray`;
- `x-guardette-request-id`.

The allowlist applies separately to request and response headers. Header names should be normalized, and values should be bounded before logging.

Never log these headers or any equivalent aliases:

- `authorization`;
- `proxy-authorization`;
- `cookie`;
- `set-cookie`;
- `x-api-key`;
- `x-auth-token`;
- `x-access-token`;
- `www-authenticate`;
- headers containing `token`, `secret`, `password`, `credential`, or `session`.

The denylist is a defense-in-depth check only. A header must pass the explicit allowlist before it can be emitted.

### Simple metrics

Record only low-cardinality metrics. Exact paths, request IDs, upstream hostnames, header values, and policy identifiers must not be metric labels.

Initial metric set:

| Metric | Type | Labels |
| --- | --- | --- |
| `guardette_requests_total` | counter | `method`, `status_class` |
| `guardette_request_duration_seconds` | histogram | `method`, `status_class` |
| `guardette_upstream_requests_total` | counter | `outcome`, `status_class` |
| `guardette_auth_failures_total` | counter | `failure_class` |

`status_class` should use values such as `2xx`, `4xx`, and `5xx`. `outcome`, `failure_class`, and method values must come from small fixed sets.

For the first slice, the metrics recorder may emit stable numeric metric events through the stdout adapter rather than introducing a full metrics SDK. This supports log-based investigation where stdout is collected, but it is not a native metric time series. A later adapter can map the same names and dimensions to OpenTelemetry or another backend without changing request handling.

### Failure behavior

Observability must not change the proxy response because a formatter, stdout write, or future exporter fails. The implementation should use no-op adapters when disabled and keep telemetry construction separate from request/response body handling.

Do not include raw exception messages by default. Emit a bounded error class and status/outcome; exception details can contain upstream payloads or secrets.

## Implementation impact

The expected application changes are limited to:

1. Add the observability package and its configuration.
2. Register middleware during FastAPI setup.
3. Replace unsafe request lifecycle fields with explicit sanitized fields.
4. Make logging setup conditional on the feature flags.
5. Add the four simple metric observations.
6. Add focused tests for feature flags, event shape, safe headers, no-body capture, and metric labels.

Do not change policy matching, transformation actions, authentication handlers, secret management, or deployment manifests in the first slice.

## Test requirements

Tests should prove:

- logging is absent when `OBS_ENABLED=false`;
- request and response events are valid JSON when enabled;
- request and response bodies never appear in captured telemetry;
- query strings never appear;
- authorization, cookie, token, API-key, and secret marker values never appear;
- only allowlisted headers are emitted;
- metric labels are limited to the documented fixed dimensions;
- request IDs correlate request and response events;
- telemetry failures do not fail the request;
- existing application responses remain unchanged when observability is disabled.

## Follow-on path

After this slice is stable:

1. Add richer policy, transformation, upstream, and secret metrics only where operational value is demonstrated.
2. Add optional OpenTelemetry metrics export.
3. Add optional tracing with low success sampling and complete error sampling.
4. Add collector/Grafana Alloy or direct OTLP deployment configuration in the appropriate deployment repository.

Tempo remains a trace backend and Loki remains a log backend; neither is required for the first stdout-based application slice.

## Decision

Choose **Option A** for the first implementation, with the explicit feature flags and safe-header policy above. Keep the module boundary and event/metric names stable so a later OpenTelemetry adapter can be added without expanding the FastAPI request changes.

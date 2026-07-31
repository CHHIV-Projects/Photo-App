# Milestone 009A — Runtime-Neutral Frontend Artifact Foundation

Prompt filename:

docs/server_deployment/deployment_milestones/009A_deployment_runtime_neutral_frontend_artifact_foundation_prompt.md

Required closeout filename:

docs/server_deployment/deployment_milestones/009A_deployment_runtime_neutral_frontend_artifact_foundation_closeout.md

Create exactly one closeout document using that filename.
Do not create a separate coder report or operations report.

## 1. Role and Milestone Relationship

Act as the coding agent for the Photo Organizer deployment branch.

Use High reasoning for the narrow frontend runtime-configuration and proxy
boundary.

Authoritative repository:

    /home/chuck/projects/photo-organizer-dev

Branch:

    feature/deployment-linux-runtime

Read and obey:

- docs/context/coding_agent_rules_v6.md
- docs/server_deployment/deployment_milestones/009_deployment_isolated_test_environment_foundation_prompt.md
- docs/server_deployment/deployment_milestones/008_deployment_restart_and_recovery_controls_validation_closeout.md
- docs/server_deployment/Photo_Organizer_Development_Operator_Controls.md

Milestone 009 remains paused while this prerequisite is implemented and
validated.

Perform Git preflight before editing:

    git branch --show-current
    git status --short
    git log --oneline --decorate -5

Stop and classify unexpected workspace changes before proceeding.

Do not commit, push, tag, merge, rebase, reset, clean, or rewrite history.

## 2. Problem Statement

The current production frontend build embeds:

    NEXT_PUBLIC_API_BASE_URL

during:

    next build

Browser requests then use that compiled environment-specific destination.

A frontend image built for Test with a Test-specific backend URL cannot honestly
be promoted unchanged to Production unless Production uses the same
browser-visible backend address and port.

That violates the intended promotion contract:

- Test validates an exact immutable frontend image;
- Production later reuses that same validated frontend image ID;
- environment-specific backend routing changes only through runtime
  configuration;
- Production must not rebuild an approved frontend candidate from source.

## 3. Milestone Goal

Make the frontend image runtime-neutral by routing browser API and managed media
requests through the frontend's own origin.

Required flow:

    Browser
        |
        | same-origin /api/* and /media/*
        v
    Next.js frontend server
        |
        | BACKEND_INTERNAL_BASE_URL at container runtime
        v
    Backend service on the environment's private Docker network

The browser must not know or embed the backend container hostname, host port, or
environment-specific backend address.

The same built frontend image must operate against at least two distinct
backend destinations solely by changing runtime container configuration.

## 4. Approved Architecture

The approved mechanism is a narrow same-origin proxy implemented inside the
existing Next.js frontend.

Implement:

- browser API requests using relative same-origin `/api/*` URLs;

- browser managed-media requests using relative same-origin `/media/*` URLs;

- a shared server-only proxy implementation;

- a catch-all Next.js Route Handler for `/api/*`;

- a catch-all Next.js Route Handler for `/media/*`;

- runtime-only backend destination configuration through:
  
      BACKEND_INTERNAL_BASE_URL

Development Compose must supply:

    BACKEND_INTERNAL_BASE_URL=http://backend:8001

Test and future Production may supply their own private internal backend
destinations while reusing the exact same frontend image.

Do not use:

- NEXT_PUBLIC_API_BASE_URL;
- a Test-specific browser URL;
- a Production-specific browser URL;
- a client-selected proxy destination;
- an external reverse proxy;
- a new package or dependency;
- an environment-specific frontend rebuild.

Do not implement this with Next.js rewrites unless direct evidence establishes
that the destination remains request-time configurable in the final built
artifact. The approved default is explicit Route Handlers.

## 5. Required Reconnaissance

Before editing, inspect narrowly:

- frontend/Dockerfile
- frontend/src/lib/api.ts
- frontend/src/lib and component code that resolves media URLs
- frontend/next.config.mjs
- frontend/.env.local.example
- frontend/.env.production.example
- docker/compose.development.yml
- docker/.env.development.example
- current frontend package scripts and Next.js version
- existing frontend route handlers, if any
- backend API and media route shapes only as needed
- use of absolute external media URLs, if any
- use of API helpers during server-side rendering, static generation, or only in
  browser/client execution

Confirm:

1. no existing `/api/*` or `/media/*` frontend route conflicts;
2. all managed backend media URLs that require proxying are safely identifiable;
3. intentionally external absolute URLs can remain external;
4. browser API calls can use same-origin relative paths;
5. server-side frontend code will not break when browser URL construction
   changes;
6. no authentication, websocket, or streaming behavior requires a broader
   architecture change.

Stop and report if those assumptions are false.

## 6. Proxy Security and Runtime Configuration Contract

`BACKEND_INTERNAL_BASE_URL` must:

- be read only by server-side Next.js code;
- be evaluated from container runtime environment;
- never use the `NEXT_PUBLIC_` prefix;
- never be returned to the browser;
- never be selectable or overridden by a request parameter, header, cookie,
  pathname, or request body;
- accept only a valid fixed `http` or `https` origin;
- reject credentials/user information in the URL;
- reject unexpected query strings and fragments;
- reject malformed or unsupported destinations;
- fail clearly and safely when missing or invalid;
- not silently fall back to an unintended host.

The proxy must append only the approved incoming `/api/*` or `/media/*`
pathname and query string to the validated backend origin.

It must prevent path construction from changing the configured backend origin.

The shared proxy implementation must remain server-only and must not enter the
browser/client module graph.

## 7. Request and Response Behavior

Support the HTTP methods required by the current API and media behavior,
including as applicable:

- GET
- HEAD
- POST
- PUT
- PATCH
- DELETE
- OPTIONS

Preserve narrowly and correctly:

- URL path;
- query string;
- request body;
- content type;
- authorization and application headers where applicable;
- cookies where applicable;
- response status;
- response body;
- streaming response behavior;
- HEAD behavior;
- media content type;
- byte-range requests;
- Range;
- Accept-Ranges;
- Content-Range;
- relevant caching headers;
- multiple Set-Cookie values if the current runtime uses them.

Do not forward hop-by-hop headers such as:

- Connection
- Keep-Alive
- Proxy-Authenticate
- Proxy-Authorization
- TE
- Trailer
- Transfer-Encoding
- Upgrade

Do not forward the browser-supplied Host header as the backend Host unless
required and proven safe.

Do not expose private backend service identity through error text, response
headers, or redirect locations.

If an upstream redirect references the configured private backend origin,
rewrite it safely to an equivalent same-origin browser path or fail closed.
Intentionally external redirects may remain external when current behavior
requires them.

Unsupported operations and upstream failures must retain appropriate HTTP
status behavior rather than returning a false success response.

## 8. Browser URL Behavior

Update frontend browser-facing URL resolution so:

- API requests use same-origin `/api/...`;
- managed relative media paths use same-origin `/media/...`;
- Test, Development, and Production browser bundles contain no
  environment-specific backend host or port;
- intentionally external absolute URLs remain unchanged;
- no Test URL is compiled into the frontend image;
- no Production URL is compiled into the frontend image.

Do not broadly rewrite arbitrary external URLs.

Do not alter backend route definitions.

## 9. Docker and Environment Changes

Update the frontend Dockerfile so:

- NEXT_PUBLIC_API_BASE_URL is no longer a build argument;
- no environment-specific backend destination is used during `next build`;
- the image continues to use the existing production-like:
  - next build;
  - next start;
- no source bind mount is introduced;
- no secret is added to image history, labels, or layers.

Update Development Compose so the frontend container receives:

    BACKEND_INTERNAL_BASE_URL=http://backend:8001

at runtime.

Update tracked environment templates to document:

    BACKEND_INTERNAL_BASE_URL

Use safe examples only.

Do not put a real protected value into Git.

Do not modify the actual protected Development environment file unless the
existing Compose pattern explicitly requires a Product Owner-managed runtime
entry. If a protected-file edit is required, stop and provide the exact
nonsecret variable name and expected value for the Product Owner to add
manually.

Preserve current Development:

- Compose project;
- ports;
- backend;
- PostgreSQL;
- Redis;
- volumes;
- storage;
- GPU behavior;
- loopback-only publication.

## 10. Required Files

Authorized implementation files:

- frontend/src/lib/api.ts
- frontend/src/lib/backendProxy.ts
- frontend/src/app/api/[...path]/route.ts
- frontend/src/app/media/[...path]/route.ts
- frontend/Dockerfile
- frontend/.env.local.example
- frontend/.env.production.example
- docker/compose.development.yml
- docker/.env.development.example
- docs/server_deployment/deployment_milestones/009A_deployment_runtime_neutral_frontend_artifact_foundation_prompt.md

The route filename may use an optional catch-all form only if reconnaissance
shows the root `/api` or `/media` route must also be supported.

Later, when requested, create only:

- docs/server_deployment/deployment_milestones/009A_deployment_runtime_neutral_frontend_artifact_foundation_closeout.md

No package.json or lockfile change is authorized.

No backend file is authorized.

If any file outside this list becomes necessary, stop and request approval.

## 11. Out of Scope

Do not implement:

- Milestone 009 Test containers, networks, volumes, configuration, or release
  state;
- Production;
- Test-to-Production promotion;
- candidate preparation or deployment;
- image registry use;
- CI/CD;
- GitHub Actions;
- reverse-proxy infrastructure;
- nginx, Traefik, Caddy, or another proxy platform;
- backend changes;
- authentication redesign;
- websocket architecture;
- public or LAN exposure;
- TLS;
- dependency additions;
- schema or database changes;
- storage changes;
- Development data changes;
- Windows operator changes;
- Docker daemon changes;
- systemd, fstab, NAS, UFW, or router changes.

No `photo-organizer-test` Docker resource may be created during this milestone.

## 12. Stop Conditions

Stop and report before proceeding if:

- the proxy destination enters the browser bundle;
- a client can influence the destination origin;
- the same image cannot use distinct backend destinations through runtime
  configuration alone;
- media streaming or range behavior cannot be preserved narrowly;
- API requests require websocket support or another unsupported transport;
- existing Next.js routes conflict with `/api/*` or `/media/*`;
- browser and server-side API use cannot be separated safely;
- Development requires a broad behavior change;
- implementation requires a dependency;
- implementation requires a backend change;
- authentication or cookie behavior requires redesign;
- an internal backend address would leak through redirects or errors;
- external absolute media URLs cannot be distinguished safely;
- a file outside the authorized list is required;
- validation would affect Portainer, Development data, or unrelated Docker
  workloads.

Report evidence and the smallest safe recommendation. Do not improvise around a
stop condition.

## 13. Required Static Validation

Run the smallest relevant validation:

- frontend lint;
- frontend TypeScript validation if separately available;
- production frontend build;
- route-handler compile validation;
- server-only module boundary validation;
- no package or lockfile change;
- protected-value scan;
- Dockerfile secret/build-argument review;
- Compose config rendering with safe configuration;
- Development service/port/volume/network comparison;
- no Test resource reference;
- no Production resource reference;
- whitespace validation;
- Git diff review.

Inspect the generated browser/static assets and confirm they contain none of:

- Test hostnames;
- Production hostnames;
- `127.0.0.1:18002`;
- environment-specific backend ports;
- the runtime value supplied through BACKEND_INTERNAL_BASE_URL;
- NEXT_PUBLIC_API_BASE_URL.

The literal server-side variable name may exist in server-only build artifacts,
but must not appear in browser-delivered JavaScript as a usable destination or
configuration mechanism.

Do not claim live Docker validation that was not performed.

## 14. Product Owner Docker Validation Plan

Because Docker requires interactive sudo, provide exact commands and pause for
Product Owner execution where necessary.

Use temporary validation resources that:

- do not use the `photo-organizer-test` project or names;
- do not attach persistent volumes;
- do not modify Development containers;
- do not modify Portainer;
- bind only to unused Windows/server loopback validation ports;
- have unique 009A validation labels or names;
- are removed only by exact name after validation;
- never use prune or broad cleanup commands.

### Gate 1 — Build once

Build the frontend image exactly once from the implemented workspace.

Use a temporary validation-specific tag, never `latest`.

Record:

- image reference;
- image ID;
- build result.

Do not rebuild between the two endpoint tests.

### Gate 2 — First runtime backend destination

Run the exact built image ID with:

    BACKEND_INTERNAL_BASE_URL=<temporary backend endpoint A>

Verify:

- frontend starts;
- `/api/*` reaches endpoint A;
- `/media/*` reaches endpoint A;
- query strings are preserved;
- request bodies are preserved;
- content type and status are preserved;
- HEAD works;
- media streaming works;
- byte-range requests work;
- invalid methods and upstream failures retain appropriate status;
- no private backend identity leaks.

Stop only the exact temporary validation containers.

### Gate 3 — Second runtime backend destination

Run the same exact frontend image ID without rebuilding, with:

    BACKEND_INTERNAL_BASE_URL=<temporary backend endpoint B>

Verify the same behavior and prove requests now reach endpoint B.

Record that the frontend image ID is identical in Gate 2 and Gate 3.

Stop only the exact temporary validation containers.

### Gate 4 — Browser artifact proof

Confirm browser-delivered assets contain no endpoint A or endpoint B address,
hostname, or port.

Confirm the browser communicates only with its own frontend origin.

### Gate 5 — Development regression

Validate Development without altering its database, Redis, volumes, Vault, or
existing backend.

Preferred safe method:

- run the exact validation frontend image temporarily on a separate loopback
  port;
- connect it only to the existing Development Docker network when necessary;
- supply `BACKEND_INTERNAL_BASE_URL=http://backend:8001`;
- do not replace or recreate the existing Development frontend during the
  initial proof.

Verify:

- frontend loads;
- normal API requests work;
- existing Assets display;
- thumbnails and managed media load through `/media/*`;
- backend health remains available;
- Development backend, PostgreSQL, Redis, ports, volumes, and storage remain
  unchanged;
- Portainer remains unchanged.

If attaching a temporary validation container to the Development network would
create ambiguity or risk, stop and propose a narrower Product Owner-controlled
regression method.

After the isolated proof passes, report whether the committed Development
Compose change requires a later controlled Development frontend rebuild or
restart. Do not perform that replacement without Product Owner approval.

## 15. Acceptance Criteria

Milestone 009A is ready for Product Owner approval when:

- browser API requests use same-origin paths;
- browser managed-media requests use same-origin paths;
- backend destination is server-only runtime configuration;
- client requests cannot select the backend origin;
- NEXT_PUBLIC_API_BASE_URL is removed from the build contract;
- no Test or Production endpoint is compiled into browser assets;
- the frontend image builds successfully;
- one exact frontend image ID operates against two distinct backend endpoints
  without rebuilding;
- API behavior is preserved;
- media streaming and byte ranges are preserved;
- private backend identity does not leak;
- Development regression passes;
- no backend, database, Redis, storage, schema, dependency, Portainer, Test, or
  Production change occurs;
- no Test Docker resource exists;
- all static and Product Owner validation evidence is recorded.

Do not claim acceptance until the Product Owner completes the required live
Docker validation.

## 16. Required Final Report

Report:

1. reconnaissance findings;
2. final proxy architecture;
3. server-only runtime configuration validation;
4. API and media behavior;
5. exact files changed;
6. static tests performed;
7. generated browser-asset inspection;
8. Docker validation still required;
9. Product Owner validation commands and expected evidence;
10. Development regression plan;
11. risks, limitations, and stop conditions encountered;
12. confirmation that no Test resource was created;
13. confirmation that Development data and Portainer were untouched.

Provide:

    git status --short
    git diff --name-only
    git diff --stat
    git -c core.whitespace=cr-at-eol diff --check
    git ls-files --others --exclude-standard

Do not commit or push.

Pause for Product Owner review.

# Milestone 009A — Runtime-Neutral Frontend Artifact Foundation Closeout

## 1. Outcome

Milestone 009A completed successfully.

The frontend now uses same-origin browser paths for API and managed-media
requests and resolves the private backend origin only in server-side Next.js
code from `BACKEND_INTERNAL_BASE_URL` at request time. One exact frontend image
operated against two isolated backend destinations solely through different
runtime configuration, without rebuilding.

Product Owner validation passed all five gates, including native Windows
browser validation against the existing Development backend and controlled
fixture data.

Milestone outcome: **PASS**.

Milestone 009 may resume after the Milestone 009A implementation and closeout
are reviewed and committed. No Test or Production deployment is approved by
this closeout.

## 2. Repository State and Commit Identification

### Authoritative repository

- Path: `/home/chuck/projects/photo-organizer-dev`
- Branch: `feature/deployment-linux-runtime`
- Current HEAD: `4ab9b53` — `Add Milestone 009A runtime-neutral frontend prompt`
- Remote branch at review: `origin/feature/deployment-linux-runtime` at
  `4ab9b53`

### Commit status

The locked Milestone 009A prompt is committed in `4ab9b53`.

The implementation and this closeout are intentionally uncommitted at closeout
creation. Therefore, there is no final Milestone 009A implementation commit to
identify yet. The Product Owner must review and create the implementation
commit in a later authorized step.

No commit, push, tag, merge, rebase, reset, clean, or history rewrite was
performed during implementation validation or closeout creation.

## 3. Problem Resolved

The previous frontend production build accepted
`NEXT_PUBLIC_API_BASE_URL` as a Docker build argument and compiled a
browser-visible backend destination into the artifact. That prevented an exact
Test-validated frontend image from being promoted unchanged to a different
runtime backend destination.

Milestone 009A replaced that contract with this flow:

```text
Browser
  |
  | same-origin /api/* and /media/*
  v
Next.js frontend server
  |
  | server-only BACKEND_INTERNAL_BASE_URL
  v
Backend on the environment's private Docker network
```

The browser does not select or receive the configured backend origin.

## 4. Exact Implementation Files

### Modified files

- `docker/.env.development.example`
- `docker/compose.development.yml`
- `frontend/.env.local.example`
- `frontend/.env.production.example`
- `frontend/Dockerfile`
- `frontend/src/lib/api.ts`

### Added files

- `frontend/src/lib/backendProxy.ts`
- `frontend/src/app/api/[...path]/route.ts`
- `frontend/src/app/media/[...path]/route.ts`

### Closeout file

- `docs/server_deployment/deployment_milestones/009A_deployment_runtime_neutral_frontend_artifact_foundation_closeout.md`

No package file, lockfile, backend file, database/schema file, storage file,
operator file, Test file, Production deployment file, or other implementation
file changed.

The temporary Product Owner harness at
`docs/server_deployment/working/009A_product_owner_validation.sh` remains
excluded through `.git/info/exclude`, untracked, and outside the milestone
deliverables.

## 5. Browser URL Architecture

`frontend/src/lib/api.ts` now uses an empty API base so browser requests remain
same-origin:

```text
/api/*
/media/*
```

Managed relative paths are normalized to root-relative paths. Explicit
`http://` and `https://` URLs remain external and unchanged. Protocol-relative
URLs beginning with `//` fail closed instead of inheriting the browser scheme
and creating an ambiguous external destination.

No browser helper reads a backend environment variable. The legacy
`NEXT_PUBLIC_API_BASE_URL` build and browser contract was removed.

## 6. Server-Only Runtime Configuration

The shared proxy reads:

```text
BACKEND_INTERNAL_BASE_URL
```

only when a Route Handler receives a request. It is not evaluated during module
import or `next build`.

The configured value must be one fixed `http` or `https` origin. Validation
rejects:

- a missing value;
- malformed URLs;
- unsupported schemes;
- usernames or passwords;
- paths other than `/`;
- query strings;
- fragments;
- an origin that resolves to `null`.

The proxy constructs an upstream URL by applying only the approved incoming
`/api/*` or `/media/*` pathname and query string to the validated origin. It
then verifies that the resulting origin is unchanged. Request parameters,
headers, cookies, paths, queries, and bodies cannot select a different backend
origin.

Missing or invalid configuration returns a generic, non-leaking HTTP `500`
response. An unreachable upstream returns a generic HTTP `502` response. There
is no fallback backend.

## 7. Route Handler and Runtime Behavior

The two catch-all Route Handlers:

- use the Next.js Node.js runtime;
- force dynamic request handling;
- import the shared proxy only into server-side Route Handler modules;
- support `GET`, `HEAD`, `POST`, `PUT`, `PATCH`, `DELETE`, and `OPTIONS`;
- preserve the incoming approved path and query string;
- preserve request bodies as bytes;
- return the upstream response body as a stream where applicable;
- preserve upstream status and status text;
- preserve media content type, caching headers, and range headers;
- suppress bodies for `HEAD`, `204`, `205`, and `304` responses;
- preserve multiple `Set-Cookie` values in the validated Node runtime.

The proxy sets upstream `Accept-Encoding: identity` to prevent transparent
decompression from changing the byte stream while stale content encoding or
length metadata remains attached.

## 8. Header and Private-Identity Security

In both request and response directions, the proxy removes standard
hop-by-hop headers and headers nominated by `Connection`.

The browser-supplied `Host` header is not forwarded. The runtime HTTP client
derives the upstream Host from the server-configured backend URL. Product Owner
evidence confirmed that the browser-provided value did not reach either mock
backend and that the actual upstream Host was nonempty and recorded only in
private server-side mock-log evidence.

Responses remove upstream `Server`, `Via`, and `X-Powered-By` identity headers.
Other response-header and cookie values are rejected if they expose the
configured private backend origin, host, or hostname.

Redirect handling is manual:

- a redirect to the configured backend origin is rewritten to an approved
  same-origin `/api/*` or `/media/*` browser path;
- credentials, a different origin, an unsupported scheme, an unapproved path,
  or a malformed destination fails closed with a generic HTTP `502` response;
- private backend identity is not returned in generated errors or redirect
  locations.

The proxy does not buffer and rewrite arbitrary upstream application bodies.
Current managed-media and API contracts use relative URLs, while deliberately
external absolute `http` or `https` URLs remain external.

## 9. Docker and Environment Contract

The frontend Dockerfile no longer declares or exports
`NEXT_PUBLIC_API_BASE_URL` during the builder stage. The existing production
shape remains:

- `npm ci`;
- frontend lint;
- `next build`;
- `next start`;
- no runtime source bind mount;
- no new package or dependency.

Development Compose supplies this literal server-only runtime value to the
frontend container:

```text
BACKEND_INTERNAL_BASE_URL=http://backend:8001
```

The tracked Development and frontend environment examples document only safe
server-side examples. The protected Development environment file was not
modified.

Development retains:

- Compose project `photo-organizer-dev`;
- frontend publication at `127.0.0.1:13000`;
- backend publication at `127.0.0.1:18001`;
- unpublished PostgreSQL and Redis;
- existing networks and named volumes;
- `STORAGE_MODE=local` and existing application storage;
- existing GPU behavior.

## 10. Static Validation

Static review and Product Owner Docker build evidence established:

- frontend lint passed;
- Next.js production build and its integrated TypeScript validation passed;
- both Route Handlers compiled in the production artifact;
- the shared proxy is imported only by the server-side Route Handlers;
- no `NEXT_PUBLIC_API_BASE_URL` reference remains in frontend or Docker
  implementation files;
- no package or lockfile changed;
- protected environment files remain ignored;
- Development Compose rendered with the original four services, ports,
  networks, named volumes, storage, and GPU overlay behavior;
- no Test or Production resource reference entered implementation files;
- whitespace validation passed.

The retained Gate 1 build log reports the lint/build layer as cache-resolved for
the identical frontend context. The final image was nevertheless assembled
once under the unique validation tag, and no rebuild occurred between runtime
destinations.

## 11. Product Owner Validation Identity

Product Owner validation completed on 2026-08-01 with:

```text
run_id:
009a-20260801T004633Z-367721

retained image:
photo-organizer-009a-validation:009a-20260801T004633Z-367721

exact image ID:
sha256:9e203bf9452fde7aa7900133ef69835427552e826965cd8030a3f0acd1c5dcbd

evidence directory:
/tmp/photo-organizer-009a-20260801T004633Z-367721-evidence
```

The image is intentionally retained pending evidence review. It is validation
evidence built from the reviewed uncommitted workspace; it is not yet a clean,
committed Milestone 009 Test candidate and must not be treated as a Production
or promotion artifact.

## 12. Gate 1 — Static Docker Build Validation

Result: **PASS**.

- The frontend image was built exactly once under a unique 009A tag, never
  `latest`.
- The exact image ID was recorded.
- Lint, production build, integrated TypeScript validation, and Route Handler
  compilation passed through the Docker build.
- `frontend/package.json` and `frontend/package-lock.json` hashes were
  identical before and after the build.
- No package or lockfile change occurred.
- The final image configuration contained no runtime backend destination.

## 13. Gate 2 — Runtime Destination A

Result: **PASS**.

The exact Gate 1 image ran with runtime destination A. Evidence confirmed:

- expected destination marker A;
- preserved method, `/api/*` path, query string, JSON bytes, authorization,
  cookie, content type, response status, and two `Set-Cookie` headers;
- browser-supplied Host was not forwarded;
- the connection-nominated test header was removed;
- private server, proxy, powered-by, hop-header, Host, and mock identity values
  did not leak through browser-facing headers or bodies;
- full media bytes and `HEAD` behavior passed;
- `Accept-Ranges`, content length, content type, cache control, and ETag were
  preserved;
- `Range: bytes=5-9` returned HTTP `206`,
  `Content-Range: bytes 5-9/26`, and bytes `FGHIJ`;
- upstream HTTP `409` and `503` statuses were preserved;
- an internal private-origin redirect became
  `/api/probe?redirected=1`;
- an unsafe external redirect failed closed with generic HTTP `502`;
- `PROPFIND` returned framework HTTP `400` without reaching the mock backend.

The exact temporary containers and network were removed by name.

## 14. Gate 3 — Runtime Destination B

Result: **PASS**.

The exact same frontend image ID ran with runtime destination B. No rebuild was
performed. The same API, header, cookie, Host, media, `HEAD`, byte-range,
status, redirect, unsupported-method, and private-identity checks passed with
destination marker B.

The exact temporary containers and network were removed by name.

## 15. Gate 4 — Browser Artifact Proof

Result: **PASS**.

Nine browser-delivered assets were captured and inspected. Twenty forbidden
values were checked, including:

- runtime endpoint A and B names and origins;
- Test and Production resource-name patterns;
- Development and proposed Test backend ports;
- `backend:8001` and port `8001`;
- `NEXT_PUBLIC_API_BASE_URL`;
- `BACKEND_INTERNAL_BASE_URL`.

Forbidden matches: **0**.

The literal server-side variable name and its runtime value were absent from
browser-delivered assets.

## 16. Gate 5 — Development Regression

Result: **PASS**.

The Development browser-edge network was selected by exact Compose project and
network labels rather than by a presumed name. The same Gate 1 image ran as a
temporary frontend on server loopback port `13093`, attached only to that
verified network, with:

```text
BACKEND_INTERNAL_BASE_URL=http://backend:8001
```

The existing Development frontend was not replaced or recreated.

Automated evidence confirmed:

- frontend root and `/api/photos` loaded through the temporary frontend;
- exactly three controlled fixture Assets were returned;
- both JPEG originals, the TIFF original, and its managed JPEG preview were
  readable through the same-origin proxy;
- media SHA-256 values matched before validation, through the proxy, and after
  cleanup;
- managed-media range behavior returned HTTP `206` with the correct bytes;
- backend health was identical before and after and reported database, Redis,
  and local storage healthy;
- Development container, network, and volume snapshots were identical before
  and after;
- Portainer configuration was identical before and after;
- shared-host container, Compose-project, network, and volume diffs were empty;
- PostgreSQL and Redis remained unpublished.

Native Windows validation through the temporary SSH tunnel confirmed:

- the frontend loaded;
- all three controlled fixture Assets displayed;
- display/thumbnail media loaded;
- the TIFF managed JPEG preview loaded;
- no API, database, Redis, storage, Vault, preview, or missing-file error
  appeared.

The temporary Development-validation frontend was removed by exact name.

## 17. Test, Production, and Resource Boundaries

Preflight evidence recorded:

```text
Test containers: 0
Test networks: 0
Test volumes: 0
```

No `photo-organizer-test` container, network, volume, configuration, release
state, or other Test resource was created. No Production container, network,
volume, configuration, deployment, or promotion resource was created.

No persistent volume was attached to a temporary validation resource. No
broad cleanup, prune, wildcard removal, Development recreation, Portainer
change, Docker daemon change, socket-permission change, or Docker-group change
occurred. Docker commands in the Product Owner harness used visible interactive
sudo.

Post-cleanup shared-host evidence contains no temporary 009A container or
network. Only the specifically retained validation image and excluded harness
remain pending Product Owner review.

## 18. Known Limitations and Deferred Work

- The proxy supports HTTP request/response and streaming behavior required by
  the current application. WebSocket proxying is not implemented.
- Route Handler coverage is for `/api/*` and `/media/*`; bare `/api` and
  `/media` roots were not required by current routes or validation.
- The proxy preserves deliberately external absolute `http` and `https` URLs
  rather than broadly rewriting them.
- Arbitrary upstream application bodies are not buffered or rewritten. Current
  API and managed-media contracts use relative internal paths.
- The retained validation image was built from an uncommitted workspace and is
  evidence only. Milestone 009 must prepare any Test candidate from an exact
  clean, pushed commit under its own approval gates.
- The existing Development frontend was not rebuilt or recreated during this
  milestone. Applying the new Compose/runtime contract to that existing
  service requires a later controlled frontend build/recreation after the
  implementation is committed and approved.
- Test configuration, isolated Test services and data, candidate deployment,
  Production, registry use, CI/CD, and promotion remain deferred.
- The retained `/tmp` evidence directory is host-local and temporary by
  filesystem convention; preserve or archive it separately if longer-term
  evidence retention is required.

## 19. Acceptance Conclusion

Every Milestone 009A acceptance criterion passed:

- browser API and managed-media requests are same-origin;
- backend destination configuration is server-only and request-time;
- clients cannot select the backend origin;
- the legacy public build argument is removed;
- browser assets contain no environment-specific backend identity;
- the frontend production image builds successfully;
- one exact image ID operated against destinations A and B without rebuilding;
- API, cookie, streaming, `HEAD`, range, status, redirect, and error behavior
  passed;
- private backend identity did not leak in validated browser-facing results;
- Development regression and native Windows validation passed;
- Development data and topology and Portainer remained unchanged;
- no dependency, backend, database, Redis, storage, schema, Test, or Production
  change occurred;
- all static and Product Owner evidence was recorded.

Milestone 009A is approved for its narrow runtime-neutral frontend artifact
foundation scope.

## 20. Recommendation for Resuming Milestone 009

Resume Milestone 009 after Product Owner review and commit of this
implementation and closeout.

Milestone 009 should:

1. prepare a Test candidate only from an exact clean, pushed commit;
2. build and record immutable commit-specific frontend and backend image IDs;
3. reuse the runtime-neutral frontend image without compiling a Test backend
   destination into browser assets;
4. supply the isolated Test backend origin only through server runtime
   configuration;
5. create separate Test Compose identity, ports, networks, PostgreSQL, Redis,
   application storage, Vault, logs, and release state under the locked
   Milestone 009 gates;
6. preserve all Development, Portainer, shared-host, loopback-only, sudo, and
   non-destructive boundaries.

The retained Milestone 009A validation image should not substitute for the
Milestone 009 clean-commit candidate process.

## 21. Closeout Boundary

This closeout creates only:

`docs/server_deployment/deployment_milestones/009A_deployment_runtime_neutral_frontend_artifact_foundation_closeout.md`

No implementation file was changed during closeout creation. No Docker command
was rerun. The retained validation image and temporary Product Owner harness
were not removed. No commit or push was performed.

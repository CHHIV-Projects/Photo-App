const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade"
]);

const PRIVATE_RESPONSE_HEADERS = new Set(["server", "via", "x-powered-by"]);

type ProxyRoutePrefix = "/api" | "/media";

class ProxyConfigurationError extends Error {}

function errorResponse(request: Request, status: number, detail: string): Response {
  const headers = new Headers({
    "Cache-Control": "no-store",
    "Content-Type": "application/json"
  });
  const body = request.method === "HEAD" ? null : JSON.stringify({ detail });
  return new Response(body, { status, headers });
}

function backendOriginFromRuntime(): URL {
  const configuredValue = process.env.BACKEND_INTERNAL_BASE_URL?.trim();
  if (!configuredValue) {
    throw new ProxyConfigurationError("The backend proxy is not configured.");
  }

  let configuredUrl: URL;
  try {
    configuredUrl = new URL(configuredValue);
  } catch {
    throw new ProxyConfigurationError("The backend proxy configuration is invalid.");
  }

  if (configuredUrl.protocol !== "http:" && configuredUrl.protocol !== "https:") {
    throw new ProxyConfigurationError("The backend proxy configuration is invalid.");
  }
  if (
    configuredUrl.username ||
    configuredUrl.password ||
    configuredUrl.pathname !== "/" ||
    configuredUrl.search ||
    configuredUrl.hash ||
    configuredUrl.origin === "null"
  ) {
    throw new ProxyConfigurationError("The backend proxy configuration is invalid.");
  }

  return new URL(configuredUrl.origin);
}

function connectionScopedHeaderNames(headers: Headers): Set<string> {
  const names = new Set<string>();
  const connectionValue = headers.get("connection");
  if (!connectionValue) {
    return names;
  }

  for (const token of connectionValue.split(",")) {
    const normalized = token.trim().toLowerCase();
    if (normalized) {
      names.add(normalized);
    }
  }
  return names;
}

function requestHeadersForUpstream(source: Headers): Headers {
  const destination = new Headers();
  const connectionScoped = connectionScopedHeaderNames(source);

  source.forEach((value, name) => {
    const normalized = name.toLowerCase();
    if (
      normalized === "host" ||
      HOP_BY_HOP_HEADERS.has(normalized) ||
      connectionScoped.has(normalized)
    ) {
      return;
    }
    destination.append(name, value);
  });

  // Avoid transparent decompression changing the bytes while retaining an
  // upstream Content-Encoding or Content-Length header.
  destination.set("Accept-Encoding", "identity");
  return destination;
}

type HeadersWithSetCookie = Headers & {
  getSetCookie?: () => string[];
};

function exposesPrivateBackendIdentity(value: string, backendOrigin: URL): boolean {
  const normalizedValue = value.toLowerCase();
  const privateCandidates = [
    backendOrigin.origin.toLowerCase(),
    backendOrigin.host.toLowerCase(),
    backendOrigin.hostname.toLowerCase()
  ];
  return privateCandidates.some((candidate) => normalizedValue.includes(candidate));
}

function responseHeadersForBrowser(
  source: Headers,
  backendOrigin: URL
): Headers | null {
  const destination = new Headers();
  const connectionScoped = connectionScopedHeaderNames(source);
  let privateIdentityFound = false;

  source.forEach((value, name) => {
    const normalized = name.toLowerCase();
    if (
      normalized === "set-cookie" ||
      HOP_BY_HOP_HEADERS.has(normalized) ||
      connectionScoped.has(normalized) ||
      PRIVATE_RESPONSE_HEADERS.has(normalized)
    ) {
      return;
    }
    if (normalized !== "location" && exposesPrivateBackendIdentity(value, backendOrigin)) {
      privateIdentityFound = true;
      return;
    }
    destination.append(name, value);
  });

  const headersWithSetCookie = source as HeadersWithSetCookie;
  const getSetCookieValues = headersWithSetCookie.getSetCookie?.();
  const fallbackSetCookieValue = source.get("set-cookie");
  const setCookieValues = getSetCookieValues ?? (fallbackSetCookieValue ? [fallbackSetCookieValue] : []);
  if (
    privateIdentityFound ||
    setCookieValues.some((value) => exposesPrivateBackendIdentity(value, backendOrigin))
  ) {
    return null;
  }
  for (const value of setCookieValues) {
    destination.append("Set-Cookie", value);
  }

  return destination;
}

function isApprovedProxyPath(pathname: string, prefix?: ProxyRoutePrefix): boolean {
  if (prefix) {
    return pathname === prefix || pathname.startsWith(`${prefix}/`);
  }
  return (
    pathname === "/api" ||
    pathname.startsWith("/api/") ||
    pathname === "/media" ||
    pathname.startsWith("/media/")
  );
}

function upstreamUrlForRequest(request: Request, backendOrigin: URL, prefix: ProxyRoutePrefix): URL {
  const incomingUrl = new URL(request.url);
  if (!isApprovedProxyPath(incomingUrl.pathname, prefix)) {
    throw new ProxyConfigurationError("The requested proxy path is invalid.");
  }

  const upstreamUrl = new URL(backendOrigin.origin);
  upstreamUrl.pathname = incomingUrl.pathname;
  upstreamUrl.search = incomingUrl.search;
  if (upstreamUrl.origin !== backendOrigin.origin) {
    throw new ProxyConfigurationError("The requested proxy path is invalid.");
  }
  return upstreamUrl;
}

function rewriteRedirectLocation(
  responseHeaders: Headers,
  upstreamRequestUrl: URL,
  backendOrigin: URL
): boolean {
  const location = responseHeaders.get("location");
  if (!location) {
    return true;
  }

  let redirectUrl: URL;
  try {
    redirectUrl = new URL(location, upstreamRequestUrl);
  } catch {
    return false;
  }

  if (redirectUrl.protocol !== "http:" && redirectUrl.protocol !== "https:") {
    return false;
  }
  if (redirectUrl.username || redirectUrl.password || redirectUrl.origin !== backendOrigin.origin) {
    return false;
  }
  if (!isApprovedProxyPath(redirectUrl.pathname)) {
    return false;
  }

  responseHeaders.set(
    "Location",
    `${redirectUrl.pathname}${redirectUrl.search}${redirectUrl.hash}`
  );
  return true;
}

function responseMayHaveBody(request: Request, status: number): boolean {
  return request.method !== "HEAD" && status !== 204 && status !== 205 && status !== 304;
}

export async function proxyToBackend(
  request: Request,
  prefix: ProxyRoutePrefix
): Promise<Response> {
  let backendOrigin: URL;
  let upstreamUrl: URL;
  try {
    backendOrigin = backendOriginFromRuntime();
    upstreamUrl = upstreamUrlForRequest(request, backendOrigin, prefix);
  } catch (error) {
    const detail =
      error instanceof ProxyConfigurationError
        ? error.message
        : "The backend proxy request is invalid.";
    return errorResponse(request, 500, detail);
  }

  const method = request.method.toUpperCase();
  let requestBody: ArrayBuffer | undefined;
  try {
    requestBody = method === "GET" || method === "HEAD"
      ? undefined
      : await request.arrayBuffer();
  } catch {
    return errorResponse(request, 400, "The proxy request body could not be read.");
  }

  let upstreamResponse: Response;
  try {
    upstreamResponse = await fetch(upstreamUrl, {
      method,
      headers: requestHeadersForUpstream(request.headers),
      body: requestBody,
      cache: "no-store",
      redirect: "manual",
      signal: request.signal
    });
  } catch {
    return errorResponse(request, 502, "The backend service is unavailable.");
  }

  const responseHeaders = responseHeadersForBrowser(upstreamResponse.headers, backendOrigin);
  if (!responseHeaders) {
    return errorResponse(request, 502, "The backend returned an unsafe response header.");
  }
  if (
    upstreamResponse.status >= 300 &&
    upstreamResponse.status < 400 &&
    !rewriteRedirectLocation(responseHeaders, upstreamUrl, backendOrigin)
  ) {
    return errorResponse(request, 502, "The backend returned an unsafe redirect.");
  }

  const responseBody = responseMayHaveBody(request, upstreamResponse.status)
    ? upstreamResponse.body
    : null;
  return new Response(responseBody, {
    status: upstreamResponse.status,
    statusText: upstreamResponse.statusText,
    headers: responseHeaders
  });
}

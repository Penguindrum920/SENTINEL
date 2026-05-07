function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '');
}

function stripSuffix(value: string, suffix: string): string {
  return value.toLowerCase().endsWith(suffix)
    ? value.slice(0, value.length - suffix.length)
    : value;
}

function normalizeBase(value: string): string {
  let normalized = trimTrailingSlash(value.trim());
  normalized = stripSuffix(normalized, '/api');
  normalized = stripSuffix(normalized, '/ws');
  return trimTrailingSlash(normalized);
}

function toHttpOrigin(value: string): string {
  return normalizeBase(value)
    .replace(/^ws:\/\//i, 'http://')
    .replace(/^wss:\/\//i, 'https://');
}

function toWsOrigin(value: string): string {
  return normalizeBase(value)
    .replace(/^http:\/\//i, 'ws://')
    .replace(/^https:\/\//i, 'wss://');
}

export function getApiBaseUrl(): string {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (apiUrl) {
    return normalizeBase(apiUrl);
  }

  const wsUrl = process.env.NEXT_PUBLIC_WS_URL?.trim();
  if (wsUrl) {
    return toHttpOrigin(wsUrl);
  }

  if (typeof window !== 'undefined') {
    const isLocalhost = ['localhost', '127.0.0.1'].includes(window.location.hostname);
    if (!isLocalhost) {
      return window.location.origin;
    }
  }

  return 'http://localhost:8000';
}

export function getWsBaseUrl(): string {
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL?.trim();
  if (wsUrl) {
    return toWsOrigin(wsUrl);
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (apiUrl) {
    return toWsOrigin(apiUrl);
  }

  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const isLocalhost = ['localhost', '127.0.0.1'].includes(window.location.hostname);
    if (!isLocalhost) {
      return `${protocol}//${window.location.host}`;
    }
  }

  return 'ws://localhost:8000';
}

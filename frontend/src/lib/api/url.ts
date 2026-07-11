const DEFAULT_API_BASE_URL = '';

function trimTrailingSlash(value: string): string {
  return value.endsWith('/') ? value.slice(0, -1) : value;
}

export function publicApiBaseUrl(envValue = process.env.NEXT_PUBLIC_API_URL): string {
  const raw = trimTrailingSlash(envValue ?? DEFAULT_API_BASE_URL);
  if (!raw) return '';

  const parsed = new URL(raw);
  if (parsed.pathname !== '/' && parsed.pathname !== '') {
    throw new Error('NEXT_PUBLIC_API_URL must be an origin only, for example https://agentco.example.com');
  }
  return `${parsed.protocol}//${parsed.host}`;
}

export function apiUrl(path: string, params = ''): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${publicApiBaseUrl()}${normalizedPath}${params}`;
}

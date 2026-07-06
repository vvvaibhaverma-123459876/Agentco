const API_KEY = process.env.NEXT_PUBLIC_AGENTCO_API_KEY;

export function agentcoAuthHeaders(existing?: HeadersInit): Headers {
  const headers = new Headers(existing);
  if (API_KEY) {
    headers.set('x-api-key', API_KEY);
    headers.set('x-agentco-api-key', API_KEY);
  }
  return headers;
}

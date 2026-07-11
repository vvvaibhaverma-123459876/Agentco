import { NextRequest } from 'next/server';

export const runtime = 'nodejs';

const HOP_BY_HOP_HEADERS = new Set([
  'connection',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
  'host',
]);

function backendOrigin(): string {
  const value = process.env.AGENTCO_API_URL ?? process.env.INTERNAL_AGENTCO_API_URL ?? 'http://localhost:3001';
  const parsed = new URL(value);
  if (parsed.pathname !== '/' && parsed.pathname !== '') {
    throw new Error('AGENTCO_API_URL must be an origin only, for example http://backend:3001');
  }
  return `${parsed.protocol}//${parsed.host}`;
}

function assertSameOriginMutation(request: NextRequest): Response | null {
  if (['GET', 'HEAD', 'OPTIONS'].includes(request.method)) return null;
  const origin = request.headers.get('origin');
  if (!origin) return new Response(JSON.stringify({ error: 'origin required' }), { status: 403 });
  if (origin !== request.nextUrl.origin) {
    return new Response(JSON.stringify({ error: 'csrf rejected' }), { status: 403 });
  }
  return null;
}

async function proxy(request: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
  const csrf = assertSameOriginMutation(request);
  if (csrf) return csrf;

  const params = await context.params;
  const path = `/${params.path?.join('/') ?? ''}`;
  const upstream = new URL(`${backendOrigin()}/api${path}`);
  upstream.search = request.nextUrl.search;

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase())) headers.set(key, value);
  });

  const serviceKey = process.env.AGENTCO_API_KEY;
  if (serviceKey) {
    headers.set('x-api-key', serviceKey);
    headers.set('x-agentco-api-key', serviceKey);
  }

  const response = await fetch(upstream, {
    method: request.method,
    headers,
    body: ['GET', 'HEAD'].includes(request.method) ? undefined : await request.arrayBuffer(),
    redirect: 'manual',
  });

  const responseHeaders = new Headers(response.headers);
  responseHeaders.delete('content-encoding');
  responseHeaders.delete('content-length');
  return new Response(response.body, { status: response.status, headers: responseHeaders });
}

export const GET = proxy;
export const HEAD = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;

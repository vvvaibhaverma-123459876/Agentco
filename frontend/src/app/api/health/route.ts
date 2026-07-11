export const runtime = 'nodejs';

export async function GET() {
  return Response.json({ status: 'ok', service: 'agentco-frontend', timestamp: new Date().toISOString() });
}

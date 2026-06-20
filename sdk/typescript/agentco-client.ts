export class AgentcoClient {
  constructor(private readonly baseUrl: string, private readonly apiKey: string) {}

  private async post(path: string, payload: unknown, idempotencyKey?: string): Promise<unknown> {
    const res = await fetch(`${this.baseUrl.replace(/\/$/, '')}${path}`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-agentco-api-key': this.apiKey,
        ...(idempotencyKey ? { 'idempotency-key': idempotencyKey } : {}),
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`Agentco API error ${res.status}`);
    return res.json();
  }

  createInstitution(name: string, idempotencyKey?: string): Promise<unknown> {
    return this.post('/institutions', { name }, idempotencyKey);
  }

  registerClaim(claim: string, probability: number, idempotencyKey?: string): Promise<unknown> {
    return this.post('/claims/register', { claim, probability }, idempotencyKey);
  }
}

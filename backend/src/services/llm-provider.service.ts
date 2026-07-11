export type LlmJsonRequest = {
  system: string;
  user: string;
  operation: string;
  model?: string;
  temperature?: number;
  maxTokens?: number;
  responseFormat?: 'json_object' | 'text';
  signal?: AbortSignal;
};

export type LlmJsonResult = {
  json: Record<string, unknown>;
  usage: {
    promptTokens: number | null;
    completionTokens: number | null;
    totalTokens: number | null;
  };
  model: string;
  attempts: number;
};

export class LlmProviderError extends Error {
  constructor(
    message: string,
    public readonly code:
      | 'missing_config'
      | 'timeout'
      | 'deadline_exceeded'
      | 'retryable_http'
      | 'non_retryable_http'
      | 'malformed_response'
      | 'cancelled',
    public readonly retryable: boolean,
  ) {
    super(message);
  }
}

function numberEnv(name: string, fallback: number): number {
  const parsed = Number(process.env[name]);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function clampMaxTokens(value: number | undefined): number {
  const max = numberEnv('LLM_MAX_OUTPUT_TOKENS', 2048);
  const requested = value ?? max;
  return Math.max(1, Math.min(requested, max));
}

function retryableStatus(status: number): boolean {
  return status === 408 || status === 409 || status === 425 || status === 429 || status >= 500;
}

function parseRetryAfterMs(header: string | null): number | null {
  if (!header) return null;
  const seconds = Number(header);
  if (Number.isFinite(seconds) && seconds >= 0) return seconds * 1000;
  const date = Date.parse(header);
  if (Number.isFinite(date)) return Math.max(0, date - Date.now());
  return null;
}

export class LlmProviderService {
  async callJson(request: LlmJsonRequest): Promise<LlmJsonResult> {
    const apiKey = process.env.LLM_API_KEY || process.env.OPENAI_API_KEY;
    if (!apiKey) {
      throw new LlmProviderError('LLM_API_KEY or OPENAI_API_KEY is required', 'missing_config', false);
    }

    const baseUrl = (process.env.LLM_BASE_URL || 'https://api.openai.com/v1').replace(/\/$/, '');
    const model = request.model || process.env.LLM_MODEL_DEFAULT || 'gpt-4o-mini';
    const maxRetries = numberEnv('LLM_MAX_RETRIES', 2);
    const perAttemptMs = Math.max(1, numberEnv('LLM_REQUEST_TIMEOUT_MS', 30000));
    const deadlineMs = Math.max(perAttemptMs, numberEnv('LLM_TOTAL_DEADLINE_MS', perAttemptMs * (maxRetries + 1)));
    const retryBaseMs = numberEnv('LLM_RETRY_BASE_MS', 100);
    const started = Date.now();
    let attempts = 0;
    let lastError: unknown;

    while (attempts <= maxRetries) {
      attempts += 1;
      const remainingMs = deadlineMs - (Date.now() - started);
      if (remainingMs <= 0) {
        throw new LlmProviderError(`${request.operation} exceeded total LLM deadline`, 'deadline_exceeded', true);
      }

      const timeoutMs = Math.min(perAttemptMs, remainingMs);
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), timeoutMs);
      const abortOnParent = () => controller.abort();
      request.signal?.addEventListener('abort', abortOnParent, { once: true });

      try {
        if (request.signal?.aborted) {
          throw new LlmProviderError(`${request.operation} cancelled`, 'cancelled', false);
        }

        const response = await fetch(`${baseUrl}/chat/completions`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${apiKey}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            model,
            temperature: request.temperature ?? 0,
            max_tokens: clampMaxTokens(request.maxTokens),
            response_format: request.responseFormat === 'text' ? undefined : { type: 'json_object' },
            messages: [
              { role: 'system', content: request.system },
              { role: 'user', content: request.user },
            ],
          }),
          signal: controller.signal,
        });

        if (!response.ok) {
          const retryable = retryableStatus(response.status);
          const code = retryable ? 'retryable_http' : 'non_retryable_http';
          const err = new LlmProviderError(
            `${request.operation} failed with provider HTTP ${response.status}`,
            code,
            retryable,
          );
          if (!retryable || attempts > maxRetries) throw err;
          lastError = err;
          const hinted = parseRetryAfterMs(response.headers.get('retry-after'));
          await sleep(Math.min(hinted ?? retryBaseMs * 2 ** (attempts - 1), Math.max(0, deadlineMs - (Date.now() - started))));
          continue;
        }

        const body = await response.json() as {
          model?: string;
          choices?: Array<{ message?: { content?: string } }>;
          usage?: { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number };
        };
        const content = body.choices?.[0]?.message?.content;
        if (!content) {
          throw new LlmProviderError(`${request.operation} returned empty content`, 'malformed_response', false);
        }
        let json: Record<string, unknown>;
        try {
          json = JSON.parse(content) as Record<string, unknown>;
        } catch (error) {
          throw new LlmProviderError(`${request.operation} returned invalid JSON`, 'malformed_response', false);
        }
        if (!json || typeof json !== 'object' || Array.isArray(json)) {
          throw new LlmProviderError(`${request.operation} returned non-object JSON`, 'malformed_response', false);
        }
        return {
          json,
          usage: {
            promptTokens: body.usage?.prompt_tokens ?? null,
            completionTokens: body.usage?.completion_tokens ?? null,
            totalTokens: body.usage?.total_tokens ?? null,
          },
          model: body.model || model,
          attempts,
        };
      } catch (error) {
        if ((error as { name?: string })?.name === 'AbortError') {
          lastError = new LlmProviderError(`${request.operation} timed out`, 'timeout', true);
        } else {
          lastError = error;
        }
        const providerError = lastError instanceof LlmProviderError ? lastError : undefined;
        if (request.signal?.aborted || providerError?.code === 'cancelled') {
          throw new LlmProviderError(`${request.operation} cancelled`, 'cancelled', false);
        }
        if (!providerError?.retryable || attempts > maxRetries) throw lastError;
        await sleep(Math.min(retryBaseMs * 2 ** (attempts - 1), Math.max(0, deadlineMs - (Date.now() - started))));
      } finally {
        clearTimeout(timeout);
        request.signal?.removeEventListener('abort', abortOnParent);
      }
    }

    throw lastError instanceof Error ? lastError : new LlmProviderError(`${request.operation} failed`, 'retryable_http', true);
  }
}

export const llmProvider = new LlmProviderService();

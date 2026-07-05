/**
 * Rate Limiting Service
 * ====================
 * Prevents DoS attacks on specialist endpoints by enforcing request limits.
 * Uses token bucket algorithm with per-specialist tracking.
 */

export interface RateLimitConfig {
  maxRequests: number; // Max requests per window
  windowMs: number; // Time window in milliseconds
}

interface TokenBucket {
  tokens: number;
  lastRefillTime: number;
}

export class RateLimitService {
  private buckets = new Map<string, TokenBucket>();
  private readonly defaultConfig: RateLimitConfig = {
    maxRequests: 10, // 10 requests per window
    windowMs: 1000, // per 1 second
  };

  private readonly configs = new Map<string, RateLimitConfig>([
    // Specialists that handle quick operations can have higher limits
    ['researcher', { maxRequests: 5, windowMs: 1000 }], // 5 req/sec
    ['fetcher', { maxRequests: 3, windowMs: 1000 }], // 3 req/sec
    ['data_analyst', { maxRequests: 5, windowMs: 1000 }], // 5 req/sec
    ['code_reviewer', { maxRequests: 3, windowMs: 1000 }], // 3 req/sec

    // API surface: per-client budget for the Fastify preHandler (E4/G11)
    ['api', { maxRequests: 100, windowMs: 60000 }], // 100 req/min, burst 100

    // All other specialists use default (10 req/sec)
  ]);

  /**
   * Check if request is allowed (token bucket algorithm)
   * Returns true if request is allowed, false if rate limited
   */
  isAllowed(specialistId: string, role?: string): boolean {
    const config = role ? this.configs.get(role) || this.defaultConfig : this.defaultConfig;
    const now = Date.now();

    // Get or create bucket for this specialist
    let bucket = this.buckets.get(specialistId);
    if (!bucket) {
      bucket = {
        tokens: config.maxRequests,
        lastRefillTime: now,
      };
      this.buckets.set(specialistId, bucket);
    }

    // Refill tokens based on time elapsed
    const timePassed = now - bucket.lastRefillTime;
    const tokensToAdd = (timePassed / config.windowMs) * config.maxRequests;

    if (tokensToAdd > 0) {
      bucket.tokens = Math.min(
        config.maxRequests, // Don't exceed max
        bucket.tokens + tokensToAdd
      );
      bucket.lastRefillTime = now;
    }

    // Check if we have tokens
    if (bucket.tokens >= 1) {
      bucket.tokens -= 1;
      return true;
    }

    return false;
  }

  /**
   * Get remaining requests for specialist (for error responses)
   */
  getRemainingRequests(specialistId: string): number {
    const bucket = this.buckets.get(specialistId);
    return bucket ? Math.ceil(bucket.tokens) : this.defaultConfig.maxRequests;
  }

  /**
   * Reset rate limit for specialist (used after errors/shutdown)
   */
  reset(specialistId: string): void {
    this.buckets.delete(specialistId);
  }

  /**
   * Reset all rate limits (used on system shutdown)
   */
  resetAll(): void {
    this.buckets.clear();
  }

  /**
   * Get rate limit config for a specialist
   */
  getConfig(role: string): RateLimitConfig {
    return this.configs.get(role) || this.defaultConfig;
  }
}

// Export singleton instance
export const rateLimiterService = new RateLimitService();

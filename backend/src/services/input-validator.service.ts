/**
 * Input Validation Service
 * =======================
 * Validates and sanitizes user input to prevent injection attacks.
 * Checks URLs, query strings, and JSON payloads.
 */

import { ActionSpec } from '../types/action.types';

export class InputValidatorService {
  /**
   * Validate URL for FETCH_PAGE actions
   * Prevents SSRF and other attacks
   */
  validateUrl(url: string): { valid: boolean; error?: string } {
    if (!url || typeof url !== 'string') {
      return { valid: false, error: 'URL must be a non-empty string' };
    }

    // Check length (prevent ReDoS attacks with massive URLs)
    if (url.length > 2048) {
      return { valid: false, error: 'URL exceeds maximum length of 2048 characters' };
    }

    // Verify it's a valid URL
    try {
      const parsedUrl = new URL(url);

      // Allow only HTTP and HTTPS
      if (!['http:', 'https:'].includes(parsedUrl.protocol)) {
        return { valid: false, error: 'Only HTTP and HTTPS URLs are allowed' };
      }

      // Reject localhost/private IP ranges (SSRF prevention)
      const hostname = parsedUrl.hostname;
      if (this.isPrivateAddress(hostname)) {
        return { valid: false, error: 'Access to private/internal networks is not allowed' };
      }

      return { valid: true };
    } catch (err: any) {
      return { valid: false, error: `Invalid URL format: ${err.message}` };
    }
  }

  /**
   * Validate search query for WEB_SEARCH actions
   * Prevents injection and extremely large queries
   */
  validateSearchQuery(query: string): { valid: boolean; error?: string } {
    if (!query || typeof query !== 'string') {
      return { valid: false, error: 'Query must be a non-empty string' };
    }

    // Check length
    if (query.length > 500) {
      return { valid: false, error: 'Query exceeds maximum length of 500 characters' };
    }

    // Check for suspicious patterns that might indicate injection
    const suspiciousPatterns = [
      /[\x00-\x08\x0B\x0C\x0E-\x1F]/g, // Control characters
      /javascript:/i, // JavaScript protocol
      /data:/i, // Data URLs
      /vbscript:/i, // VBScript protocol
    ];

    for (const pattern of suspiciousPatterns) {
      if (pattern.test(query)) {
        return { valid: false, error: 'Query contains suspicious characters or patterns' };
      }
    }

    return { valid: true };
  }

  /**
   * Validate action spec size
   * Prevents large payload attacks
   */
  validateActionSpecSize(spec: ActionSpec): { valid: boolean; error?: string } {
    const serialized = JSON.stringify(spec);

    // Maximum payload size: 100KB
    const maxSize = 100 * 1024;
    if (serialized.length > maxSize) {
      return { valid: false, error: `Action spec exceeds maximum size of ${maxSize} bytes` };
    }

    return { valid: true };
  }

  /**
   * Validate objective string
   * Prevents excessively large text fields
   */
  validateObjective(objective: string): { valid: boolean; error?: string } {
    if (!objective || typeof objective !== 'string') {
      return { valid: false, error: 'Objective must be a non-empty string' };
    }

    // Maximum length: 1000 characters
    if (objective.length > 1000) {
      return { valid: false, error: 'Objective exceeds maximum length of 1000 characters' };
    }

    return { valid: true };
  }

  /**
   * Sanitize string for safe logging
   * Removes control characters and limits length
   */
  sanitizeForLogging(input: string, maxLength: number = 500): string {
    if (!input) return '';

    return input
      .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g, '') // Remove control characters
      .substring(0, maxLength);
  }

  /**
   * Check if hostname is a private/internal address
   * Prevents SSRF attacks
   */
  private isPrivateAddress(hostname: string): boolean {
    const privatePatterns = [
      /^localhost$/i,
      /^127\./,
      /^192\.168\./,
      /^10\./,
      /^172\.(1[6-9]|2\d|3[01])\./,
      /^169\.254\./,
      /^::1$/,
      /^fc00:/i,
      /^fd00:/i,
      /^169\.254\./,
      /^0\.0\.0\.0$/,
      /^255\.255\.255\.255$/,
    ];

    for (const pattern of privatePatterns) {
      if (pattern.test(hostname)) {
        return true;
      }
    }

    // Also check for IPv6 loopback and private ranges
    if (hostname.includes(':')) {
      const lowerHostname = hostname.toLowerCase();
      if (lowerHostname === '::1' || lowerHostname.startsWith('fc') || lowerHostname.startsWith('fd')) {
        return true;
      }
    }

    return false;
  }

  /**
   * Validate and sanitize complete action spec
   */
  validateActionSpec(spec: ActionSpec): { valid: boolean; error?: string } {
    // Check spec size first
    const sizeCheck = this.validateActionSpecSize(spec);
    if (!sizeCheck.valid) {
      return sizeCheck;
    }

    // Validate objective
    if (spec.objective) {
      const objCheck = this.validateObjective(spec.objective);
      if (!objCheck.valid) {
        return objCheck;
      }
    }

    // Validate action-specific fields
    const actionTypeStr = String(spec.actionType).toLowerCase();
    if (actionTypeStr === 'fetch_page' || actionTypeStr === 'FETCH_PAGE') {
      const url = spec.args?.url;
      if (url) {
        return this.validateUrl(url);
      }
    }

    if (actionTypeStr === 'web_search' || actionTypeStr === 'WEB_SEARCH') {
      const query = spec.args?.query;
      if (query) {
        return this.validateSearchQuery(query);
      }
    }

    return { valid: true };
  }
}

// Export singleton instance
export const inputValidatorService = new InputValidatorService();

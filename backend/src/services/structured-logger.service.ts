/**
 * Structured Logging Service
 * ==========================
 * Provides JSON-structured logging with trace ID correlation for debugging.
 * Logs are written to both console and file with proper levels.
 */

import * as winston from 'winston';
import * as path from 'path';

export interface LogContext {
  traceId?: string;
  specialistId?: string;
  role?: string;
  goalId?: string;
  actionId?: string;
  [key: string]: any;
}

class StructuredLogger {
  private logger: winston.Logger;
  private requestTraceIds = new Map<string, string>();

  constructor() {
    // Define custom format for JSON logs
    const jsonFormat = winston.format.combine(
      winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss.SSS' }),
      winston.format.errors({ stack: true }),
      winston.format.json(),
      // Custom format to flatten fields
      winston.format.printf((info: any) => {
        const { timestamp, level, message, ...meta } = info;
        return JSON.stringify({
          timestamp,
          level,
          message,
          ...meta,
        });
      })
    );

    // Define simple format for console output
    const consoleFormat = winston.format.combine(
      winston.format.timestamp({ format: 'HH:mm:ss' }),
      winston.format.colorize(),
      winston.format.printf((info: any) => {
        const { timestamp, level, message, traceId, ...meta } = info;
        const trace = traceId && typeof traceId === 'string' ? ` [${traceId.substring(0, 8)}]` : '';
        const metaStr = Object.keys(meta).length > 0 ? ` ${JSON.stringify(meta)}` : '';
        return `${timestamp} ${level}${trace}: ${message}${metaStr}`;
      })
    );

    // Create logger with multiple transports
    this.logger = winston.createLogger({
      level: process.env.LOG_LEVEL || 'info',
      format: jsonFormat,
      defaultMeta: { service: 'autonomy-orchestrator' },
      transports: [
        // Error logs
        new winston.transports.File({
          filename: '/tmp/autonomy-error.log',
          level: 'error',
          maxsize: 10485760, // 10MB
          maxFiles: 5,
        }),
        // All logs
        new winston.transports.File({
          filename: '/tmp/autonomy-combined.log',
          maxsize: 10485760, // 10MB
          maxFiles: 10,
        }),
        // Console output (colorized, less verbose)
        new winston.transports.Console({
          format: consoleFormat,
        }),
      ],
    });
  }

  /**
   * Set trace ID for a request (e.g., in middleware)
   */
  setRequestTraceId(requestId: string, traceId: string): void {
    this.requestTraceIds.set(requestId, traceId);
  }

  /**
   * Get trace ID for current request
   */
  getRequestTraceId(requestId?: string): string {
    if (!requestId) return '';
    return this.requestTraceIds.get(requestId) || requestId.substring(0, 8);
  }

  /**
   * Clear request trace ID
   */
  clearRequestTraceId(requestId: string): void {
    this.requestTraceIds.delete(requestId);
  }

  /**
   * Log specialist spawn event
   */
  logSpecialistSpawn(
    specialistId: string,
    role: string,
    context: LogContext = {}
  ): void {
    this.logger.info('Specialist spawned', {
      event: 'specialist_spawn',
      specialistId,
      role,
      timestamp: new Date().toISOString(),
      ...context,
    });
  }

  /**
   * Log specialist action execution
   */
  logSpecialistAction(
    specialistId: string,
    actionType: string,
    status: 'started' | 'completed' | 'failed' | 'timeout',
    context: LogContext = {}
  ): void {
    this.logger.info(`Specialist action ${status}`, {
      event: 'specialist_action',
      specialistId,
      actionType,
      status,
      timestamp: new Date().toISOString(),
      ...context,
    });
  }

  /**
   * Log specialist error
   */
  logSpecialistError(
    specialistId: string,
    errorType: string,
    message: string,
    context: LogContext = {}
  ): void {
    this.logger.error(message, {
      event: 'specialist_error',
      specialistId,
      errorType,
      timestamp: new Date().toISOString(),
      ...context,
    });
  }

  /**
   * Log budget exceeded event
   */
  logBudgetExceeded(
    specialistId: string,
    budgetType: 'tokens' | 'iterations' | 'time',
    used: number,
    limit: number,
    context: LogContext = {}
  ): void {
    this.logger.warn('Budget exceeded', {
      event: 'budget_exceeded',
      specialistId,
      budgetType,
      used,
      limit,
      timestamp: new Date().toISOString(),
      ...context,
    });
  }

  /**
   * Log orchestrator decision
   */
  logOrchestratorDecision(
    goalId: string,
    decision: string,
    reasoning: string,
    context: LogContext = {}
  ): void {
    this.logger.info('Orchestrator decision', {
      event: 'orchestrator_decision',
      goalId,
      decision,
      reasoning,
      timestamp: new Date().toISOString(),
      ...context,
    });
  }

  /**
   * Log authentication event
   */
  logAuthenticationEvent(
    event: 'signature_valid' | 'signature_invalid' | 'timestamp_invalid',
    context: LogContext = {}
  ): void {
    const level = event.includes('valid') && !event.includes('invalid') ? 'debug' : 'warn';
    this.logger[level]('Authentication event', {
      event,
      timestamp: new Date().toISOString(),
      ...context,
    });
  }

  /**
   * Log HTTP request
   */
  logHttpRequest(
    method: string,
    path: string,
    statusCode: number,
    durationMs: number,
    context: LogContext = {}
  ): void {
    const level = statusCode >= 400 ? 'warn' : 'debug';
    this.logger[level](`HTTP ${method} ${path}`, {
      event: 'http_request',
      method,
      path,
      statusCode,
      durationMs,
      timestamp: new Date().toISOString(),
      ...context,
    });
  }

  /**
   * Log database operation
   */
  logDatabaseOperation(
    operation: 'insert' | 'update' | 'select' | 'delete',
    table: string,
    durationMs: number,
    success: boolean,
    context: LogContext = {}
  ): void {
    const level = success ? 'debug' : 'error';
    this.logger[level](`Database ${operation} on ${table}`, {
      event: 'database_operation',
      operation,
      table,
      durationMs,
      success,
      timestamp: new Date().toISOString(),
      ...context,
    });
  }

  /**
   * Log specialist result persistence
   */
  logResultPersistence(
    specialistId: string,
    artifactsCount: number,
    claimsCount: number,
    success: boolean,
    context: LogContext = {}
  ): void {
    const level = success ? 'info' : 'error';
    this.logger[level]('Specialist results persisted', {
      event: 'result_persistence',
      specialistId,
      artifactsCount,
      claimsCount,
      success,
      timestamp: new Date().toISOString(),
      ...context,
    });
  }

  /**
   * Log process lifecycle event
   */
  logProcessEvent(
    event: 'started' | 'stopped' | 'error' | 'signal',
    details: string,
    context: LogContext = {}
  ): void {
    const level = event === 'error' ? 'error' : 'info';
    this.logger[level](`Process ${event}`, {
      event: `process_${event}`,
      details,
      timestamp: new Date().toISOString(),
      ...context,
    });
  }

  /**
   * Log with custom fields
   */
  log(
    level: 'error' | 'warn' | 'info' | 'debug',
    message: string,
    context: LogContext = {}
  ): void {
    this.logger[level](message, {
      timestamp: new Date().toISOString(),
      ...context,
    });
  }

  /**
   * Get logger instance for direct use
   */
  getLogger(): winston.Logger {
    return this.logger;
  }
}

// Export singleton instance
export const structuredLogger = new StructuredLogger();

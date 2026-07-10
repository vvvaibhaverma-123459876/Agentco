export class PublicHttpError extends Error {
  readonly statusCode: number;
  readonly publicMessage: string;

  constructor(statusCode: number, publicMessage: string) {
    super(publicMessage);
    this.name = 'PublicHttpError';
    this.statusCode = statusCode;
    this.publicMessage = publicMessage;
  }
}

function isPublicHttpError(error: unknown): error is PublicHttpError {
  return error instanceof PublicHttpError;
}

export function statusCodeForError(error: unknown): number {
  const candidate = typeof (error as { statusCode?: unknown })?.statusCode === 'number'
    ? (error as { statusCode: number }).statusCode
    : 500;
  if (candidate < 400 || candidate > 599) return 500;
  return candidate;
}

export function publicMessageForError(error: unknown): string {
  if (isPublicHttpError(error)) return error.publicMessage;

  const statusCode = statusCodeForError(error);
  if (statusCode === 400) return 'Invalid request';
  if (statusCode === 401) return 'unauthorized';
  if (statusCode === 403) return 'forbidden';
  if (statusCode === 404) return 'not found';
  if (statusCode === 429) return 'Rate limit exceeded';
  return 'Internal server error';
}

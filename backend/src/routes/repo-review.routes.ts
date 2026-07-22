/**
 * Decision-receipt repository review API.
 *
 * POST starts an async pipeline (poll the GET for stage progress); the receipt
 * and verify endpoints expose the signed result. Verification recomputes the
 * stage hash chain, the receipt content hash, and the Ed25519 signature from
 * the stored row alone — a third party with the receipt JSON can perform the
 * same verification offline.
 */
import { FastifyInstance, FastifyReply, FastifyRequest } from 'fastify';
import { repoReviewService } from '../services/repo-review.service';
import { canonicalJson, sha256Hex, verifyReceipt } from '../services/receipt-signer';

interface StartBody {
  repo_url?: string;
  requested_by_actor_id?: string;
}

export async function repoReviewRoutes(fastify: FastifyInstance) {
  fastify.post('/api/repo-review', async (request: FastifyRequest<{ Body: StartBody }>, reply: FastifyReply) => {
    const repoUrl = request.body?.repo_url;
    if (!repoUrl || typeof repoUrl !== 'string') {
      return reply.status(400).send({ error: 'repo_url is required' });
    }
    try {
      const run = await repoReviewService.startRun({
        repo_url: repoUrl,
        requested_by_actor_id: request.body?.requested_by_actor_id,
      });
      return reply.status(202).send({ run_id: run.id, status: run.status });
    } catch (error) {
      return reply.status(400).send({ error: (error as Error).message });
    }
  });

  fastify.get('/api/repo-review/:id', async (request: FastifyRequest<{ Params: { id: string } }>, reply: FastifyReply) => {
    const run = await repoReviewService.getRun(request.params.id);
    if (!run) return reply.status(404).send({ error: 'run not found' });
    return reply.send(run);
  });

  fastify.get('/api/repo-review/:id/receipt', async (request: FastifyRequest<{ Params: { id: string } }>, reply: FastifyReply) => {
    const receipt = await repoReviewService.getReceipt(request.params.id);
    if (!receipt) return reply.status(404).send({ error: 'no receipt for this run' });
    return reply.send(receipt);
  });

  fastify.get('/api/repo-review/:id/verify', async (request: FastifyRequest<{ Params: { id: string } }>, reply: FastifyReply) => {
    const stored = await repoReviewService.getReceipt(request.params.id);
    if (!stored) return reply.status(404).send({ error: 'no receipt for this run' });

    const receipt = stored.receipt as { stages?: Array<Record<string, unknown>> };
    const chainChecks: Array<Record<string, unknown>> = [];
    let prev: string | null = null;
    let chainValid = true;
    for (const stage of receipt.stages ?? []) {
      const recomputed = sha256Hex(canonicalJson(stage.payload));
      const payloadOk = recomputed === stage.payload_sha256;
      const linkOk = stage.prev_sha256 === prev;
      chainValid = chainValid && payloadOk && linkOk;
      chainChecks.push({ stage: stage.stage, payload_hash_valid: payloadOk, chain_link_valid: linkOk });
      prev = recomputed;
    }

    const { hashValid, signatureValid } = verifyReceipt(
      stored.receipt,
      stored.content_hash,
      stored.signature,
      stored.public_key_pem
    );

    return reply.send({
      valid: chainValid && hashValid && signatureValid,
      checks: {
        stage_chain: chainChecks,
        content_hash_valid: hashValid,
        signature_valid: signatureValid,
      },
      content_hash: stored.content_hash,
      public_key_pem: stored.public_key_pem,
    });
  });
}

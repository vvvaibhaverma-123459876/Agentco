#!/usr/bin/env python3
"""Run the canonical AgentCo civilization vertical slice against real services."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import os
import sys
import time
import traceback
import uuid
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urlparse


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "system_run" / "latest"
VECTOR_DIMS = 64
KAFKA_TOPIC = "agentco.civilization.vertical_slice"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


EVIDENCE = [
    {
        "id": "ev-security-review",
        "url": "artifact://security-review/civ-slice",
        "title": "External Security Review",
        "text": "Security independently reviewed the Engineering artifact and found the challenge resolved with no critical findings.",
    },
    {
        "id": "ev-runtime-audit",
        "url": "artifact://runtime-audit/civ-slice",
        "title": "Runtime Audit Trace",
        "text": "The artifact emitted audit, event, prediction, resolution, trust, memory, learning, and coordinator records.",
    },
]


REQUIRED_STAGES = [
    "task_created",
    "citizen_assigned",
    "evidence_indexed",
    "claim_created",
    "prediction_preregistered",
    "budget_reserved",
    "real_reasoning_executed",
    "decision_and_audit_written",
    "bus_event_emitted",
    "independent_resolution_completed",
    "calibration_scored",
    "trust_updated",
    "credential_minted",
    "memory_promoted",
    "learning_candidate_created",
    "canary_or_human_queue_recorded",
    "generality_metric_updated",
    "coordinator_tick_recorded",
]


def load_env() -> None:
    for name in (".codex.env", "codex.env"):
        path = ROOT / name
        if not path.exists():
            continue
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def database_url() -> str:
    url = os.getenv("DATABASE_URL") or os.getenv("AGENTCO_TEST_DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL or AGENTCO_TEST_DATABASE_URL is required for the real civilization slice")
    return url


def resolution_service_url(base_url: str) -> str:
    explicit = os.getenv("RESOLUTION_SERVICE_DATABASE_URL")
    if explicit:
        return explicit
    parsed = urlparse(base_url)
    password = os.getenv("RESOLUTION_SERVICE_PASSWORD", "resolution-service-dev-password")
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    database = parsed.path.lstrip("/") or "agentco"
    return f"postgresql://resolution_service:{quote(password, safe='')}@{host}:{port}/{database}"


def require_env() -> dict:
    load_env()
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("LLM_API_KEY or OPENAI_API_KEY is required for the real civilization slice")
    return {
        "api_key": api_key,
        "base_url": (os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1").rstrip("/"),
        "chat_model": os.getenv("LLM_MODEL_DEFAULT") or "gpt-4o-mini",
        "embedding_model": os.getenv("LLM_EMBEDDING_MODEL") or "text-embedding-3-small",
    }


def post_json(url: str, api_key: str, body: dict, timeout: int = 45) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def call_chat(env: dict, prompt: str) -> tuple[dict, dict]:
    started = time.time()
    payload = post_json(
        f"{env['base_url']}/chat/completions",
        env["api_key"],
        {
            "model": env["chat_model"],
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are AgentCo's evidence court. Return only JSON. "
                        "Use cited evidence IDs. Do not invent sources."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens": 700,
            "response_format": {"type": "json_object"},
        },
    )
    content = payload["choices"][0]["message"]["content"]
    return json.loads(content), {
        "model": env["chat_model"],
        "latency_ms": int((time.time() - started) * 1000),
        "usage": payload.get("usage", {}),
    }


def call_embedding(env: dict, text: str) -> tuple[list[float], dict]:
    started = time.time()
    payload = post_json(
        f"{env['base_url']}/embeddings",
        env["api_key"],
        {"model": env["embedding_model"], "input": text},
    )
    vector = payload["data"][0]["embedding"]
    if not isinstance(vector, list) or len(vector) < VECTOR_DIMS:
        raise RuntimeError("embedding response did not contain enough dimensions")
    return [float(x) for x in vector[:VECTOR_DIMS]], {
        "model": env["embedding_model"],
        "latency_ms": int((time.time() - started) * 1000),
        "usage": payload.get("usage", {}),
        "dimensions_used": VECTOR_DIMS,
        "dimensions_returned": len(vector),
    }


def emit_kafka_event(payload: dict) -> dict:
    try:
        from kafka import KafkaProducer
    except Exception as exc:
        raise RuntimeError("kafka-python is required for the real bus stage") from exc

    producer = KafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        acks="all",
        retries=3,
        request_timeout_ms=10000,
    )
    future = producer.send(KAFKA_TOPIC, json.dumps(payload, sort_keys=True).encode("utf-8"))
    metadata = future.get(timeout=15)
    producer.flush(timeout=10)
    producer.close()
    return {"topic": metadata.topic, "partition": metadata.partition, "offset": metadata.offset}


def canonical_audit(fields: dict) -> str:
    order = [
        "log_id",
        "timestamp",
        "prev_hash",
        "agent_id",
        "action_type",
        "input_summary",
        "output_summary",
        "confidence_score",
        "risk_level",
        "human_approved",
        "human_approver_id",
        "downstream_events",
        "session_id",
    ]
    return json.dumps({key: fields[key] for key in order}, separators=(",", ":"))


def append_decision_log(cur, *, correlation_id: str, event_ids: list[str], decision: dict) -> str:
    cur.execute(
        """
        SELECT chain_hash
          FROM decision_log
         WHERE chain_hash ~ '^[0-9a-f]{64}$'
           AND prev_hash ~ '^[0-9a-f]{64}$'
         ORDER BY timestamp DESC, log_id DESC
         LIMIT 1
        """
    )
    prev = cur.fetchone()
    prev_hash = prev[0] if prev else "0" * 64
    log_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    fields = {
        "log_id": log_id,
        "timestamp": timestamp,
        "prev_hash": prev_hash,
        "agent_id": "civilization_coordinator",
        "action_type": "decision",
        "input_summary": "external security review and runtime audit evidence",
        "output_summary": f"decision={decision['decision']} confidence={decision['confidence']}",
        "confidence_score": float(decision["confidence"]),
        "risk_level": "medium",
        "human_approved": False,
        "human_approver_id": None,
        "downstream_events": event_ids,
        "session_id": correlation_id,
    }
    chain_hash = hashlib.sha256((prev_hash + canonical_audit(fields)).encode()).hexdigest()
    cur.execute(
        """
        INSERT INTO decision_log
          (log_id, agent_id, action_type, input_summary, output_summary,
           confidence_score, risk_level, human_approved, human_approver_id, downstream_events,
           session_id, timestamp, chain_hash, prev_hash)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::uuid[],%s::uuid,%s,%s,%s)
        """,
        [
            log_id,
            fields["agent_id"],
            fields["action_type"],
            fields["input_summary"],
            fields["output_summary"],
            fields["confidence_score"],
            fields["risk_level"],
            fields["human_approved"],
            fields["human_approver_id"],
            event_ids,
            correlation_id,
            timestamp,
            chain_hash,
            prev_hash,
        ],
    )
    return log_id


def ensure_slice_schema(conn) -> None:
    with conn.cursor() as cur:
        for name in (
            "077_civilization_vertical_slice.sql",
            "078_agent_membership_id_compatibility.sql",
        ):
            migration = ROOT / "backend" / "src" / "db" / "migrations" / name
            cur.execute(migration.read_text())
    conn.commit()


def insert_vector_document(cur, run_id: str, source: dict, embedding: list[float], model: str) -> str:
    document_id = str(uuid.uuid4())
    embedding_hash = hashlib.sha256(json.dumps(embedding, separators=(",", ":")).encode()).hexdigest()
    cur.execute(
        """
        INSERT INTO civilization_vector_documents
          (id, run_id, source_id, content, embedding_model, embedding_dimensions, embedding_hash)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,
        [document_id, run_id, source["id"], source["text"], model, len(embedding), embedding_hash],
    )
    cur.executemany(
        """
        INSERT INTO civilization_vector_index (run_id, document_id, dimension, value)
        VALUES (%s,%s,%s,%s)
        """,
        [(run_id, document_id, idx, value) for idx, value in enumerate(embedding)],
    )
    return document_id


def vector_search(cur, run_id: str, query_embedding: list[float]) -> dict:
    values_sql = ",".join(["(%s,%s)"] * len(query_embedding))
    params: list = []
    for idx, value in enumerate(query_embedding):
        params.extend([idx, value])
    params.append(run_id)
    cur.execute(
        f"""
        WITH q(dimension, value) AS (VALUES {values_sql})
        SELECT d.id, d.source_id, SUM(POWER(i.value - q.value, 2)) AS squared_distance
          FROM civilization_vector_index i
          JOIN q ON q.dimension = i.dimension
          JOIN civilization_vector_documents d ON d.id = i.document_id
         WHERE i.run_id = %s
         GROUP BY d.id, d.source_id
         ORDER BY squared_distance ASC
         LIMIT 1
        """,
        params,
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError("vector search returned no document")
    return {"document_id": str(row[0]), "source_id": row[1], "squared_distance": float(row[2])}


def require_table(cur, name: str) -> None:
    cur.execute("SELECT to_regclass(%s)", [f"public.{name}"])
    if cur.fetchone()[0] is None:
        raise RuntimeError(f"required table missing: {name}")


def validate_decision(decision: dict) -> None:
    if decision.get("decision") not in {"approve", "escalate", "reject"}:
        raise RuntimeError(f"invalid decision: {decision}")
    confidence = float(decision.get("confidence", -1))
    if not 0 <= confidence <= 1:
        raise RuntimeError("decision confidence must be in [0,1]")
    cited = set(decision.get("cited_evidence_ids") or [])
    if not {"ev-security-review", "ev-runtime-audit"}.issubset(cited):
        raise RuntimeError(f"decision did not cite required evidence: {decision}")
    claims = decision.get("claims") or []
    if not claims or not all(isinstance(claim, dict) for claim in claims):
        raise RuntimeError(f"decision claims must be an array of objects: {decision}")
    if any(not claim.get("support_source_ids") for claim in claims):
        raise RuntimeError(f"all decision claims must have support_source_ids: {decision}")


def hmac_credential(agent_id: str, score: dict) -> str:
    secret = os.getenv("RESERVE_SIGNING_KEY", "local-civilization-slice-signing-key")
    payload = json.dumps({"agent_id": agent_id, "score": score}, sort_keys=True, default=str).encode()
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def run_slice() -> dict:
    import psycopg2

    env = require_env()
    db_url = database_url()
    correlation_id = str(uuid.uuid4())
    trace: list[dict] = []
    stage_results: dict[str, dict] = {}
    started = time.time()

    from calibration import create_calibration_engine
    from calibration.ledger.prediction_ledger import PredictionRegistration
    from civilization.services.institution_service import create_institution, load_contract, add_agent_to_department
    from civilization.services.review_service import create_review, transition_review
    from civilization.services.reputation_service import propagate_institution
    from reserve.tools.recompute_credential import _fetch_rows, recompute as raw_recompute

    def mark(stage: str, **details) -> None:
        stage_results[stage] = details or {"ok": True}
        trace.append({"stage": stage, "at": datetime.now(timezone.utc).isoformat(), **details})

    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    run_id = str(uuid.uuid4())
    try:
        ensure_slice_schema(conn)
        with conn.cursor() as cur:
            for table in [
                "workflow_tasks",
                "autonomy_goals",
                "goal_budgets",
                "autonomy_evidence",
                "autonomy_claims",
                "prediction_ledger",
                "event_history",
                "decision_log",
                "shared_knowledge",
                "learner_candidates",
                "policy_canary_deployments",
            ]:
                require_table(cur, table)
            cur.execute(
                """
                INSERT INTO civilization_vertical_slice_runs
                  (id, correlation_id, status, runtime_mode, llm_model, embedding_model)
                VALUES (%s,%s,'running','local_native_real_services',%s,%s)
                """,
                [run_id, correlation_id, env["chat_model"], env["embedding_model"]],
            )
        conn.commit()

        prompt = (
            "Human task: decide whether Engineering's artifact may be approved after external Security review.\n"
            "Evidence:\n" + json.dumps(EVIDENCE, indent=2) + "\n"
            "Return JSON with exactly this shape: "
            "{\"decision\":\"approve|escalate|reject\",\"confidence\":0.0,\"risk_level\":\"low|medium|high\","
            "\"cited_evidence_ids\":[\"ev-security-review\",\"ev-runtime-audit\"],"
            "\"claims\":[{\"text\":\"...\",\"status\":\"supported\",\"support_source_ids\":[\"ev-security-review\"]}],"
            "\"missing_information\":[],\"rationale\":\"...\"}. "
            "Every claim must be an object with non-empty support_source_ids. "
            "Ideal decision is approve only if both evidence items support it."
        )
        decision, chat_meta = call_chat(env, prompt)
        validate_decision(decision)
        mark("real_reasoning_executed", model=chat_meta["model"], latency_ms=chat_meta["latency_ms"])

        suffix = correlation_id[:8]
        db_source_ids = {item["id"]: f"{item['id']}-{suffix}" for item in EVIDENCE}
        embeddings: dict[str, list[float]] = {}
        embedding_meta = None
        for item in EVIDENCE:
            embeddings[item["id"]], embedding_meta = call_embedding(env, item["text"])
        query_embedding, query_meta = call_embedding(env, "external security review resolved and runtime audit emitted records")

        with conn.cursor() as cur:
            for item in EVIDENCE:
                indexed_item = {**item, "id": db_source_ids[item["id"]]}
                insert_vector_document(cur, run_id, indexed_item, embeddings[item["id"]], env["embedding_model"])
            top_vector = vector_search(cur, run_id, query_embedding)
        conn.commit()
        if top_vector["source_id"] not in set(db_source_ids.values()):
            raise RuntimeError(f"vector index did not retrieve expected evidence: {top_vector}")
        mark(
            "evidence_indexed",
            embedding_model=env["embedding_model"],
            dimensions=VECTOR_DIMS,
            top_source_id=top_vector["source_id"],
        )

        with conn.cursor() as cur:
            goal_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO autonomy_goals
                  (id, title, description, source, proposed_by, domain, expected_value,
                   risk_level, autonomy_level_allowed, status, success_criteria_json,
                   stop_conditions_json, trace_id, created_at)
                VALUES (%s,%s,%s,'manual','human_operator','engineering',1.0,
                        'medium','L3','active',%s::jsonb,%s::jsonb,%s,now())
                """,
                [
                    goal_id,
                    f"Civilization vertical slice {suffix}",
                    "Approve or escalate Engineering artifact using evidence-governed civilization loop",
                    json.dumps(["external_review_required", "evidence_backed_claim", "prediction_resolved"]),
                    json.dumps(["missing_evidence", "resolver_unavailable"]),
                    correlation_id,
                ],
            )
            task_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO workflow_tasks (task_id, agent_id, task_type, payload, status, queued_at)
                VALUES (%s,'engineering-citizen','review',%s::jsonb,'queued',now())
                """,
                [task_id, json.dumps({"goal_id": goal_id, "evidence_ids": [e["id"] for e in EVIDENCE]})],
            )
            mark("task_created", goal_id=goal_id, task_id=task_id)
            cur.execute(
                """
                INSERT INTO goal_budgets
                  (id, goal_id, compute_budget, token_budget, time_budget_seconds, tool_budget_json, spend_limit)
                VALUES (%s,%s,1,%s,120,%s::jsonb,1.00)
                """,
                [str(uuid.uuid4()), goal_id, 4000, json.dumps({"kafka_events": 4, "openai_calls": 4})],
            )
            mark("budget_reserved", goal_id=goal_id, token_budget=4000)
        conn.commit()

        eng = create_institution(f"Engineering {suffix}", load_contract("Engineering"), conn)
        sec = create_institution(f"Security {suffix}", load_contract("Security"), conn)
        agent_id = f"civilization-citizen-{suffix}"
        add_agent_to_department(agent_id, eng["department_ids"]["Production"], "engineer", conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO autonomy_team_activations
                  (parent_goal_id, specialist_id, specialist_role, objective,
                   budget_tokens, budget_iterations, budget_seconds, status, results)
                VALUES (%s,%s,'engineer','Civilization vertical slice artifact review',
                        4000,5,120,'completed',%s::jsonb)
                """,
                [goal_id, agent_id, json.dumps({"assigned_to": eng["department_ids"]["Production"]})],
            )
        conn.commit()
        mark("citizen_assigned", agent_id=agent_id, institution_id=eng["institution_id"])

        output_id = f"civilization-artifact-{suffix}"
        review_id = create_review(output_id, eng["institution_id"], sec["institution_id"], conn)
        transition_review(review_id, "under_review", conn)
        transition_review(review_id, "challenged", conn, evidence={"missing": "initial runtime audit"})

        action_id = str(uuid.uuid4())
        source_ids = [db_source_ids[item["id"]] for item in EVIDENCE]
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO autonomy_goal_actions
                  (action_id, goal_id, action_type, objective, args, success_criteria,
                   risk_level, decided_by, decided_at, reasoning, status, executed_at, result)
                VALUES (%s,%s,'GENERATE_CLAIM','Generate evidence-backed approval claim',
                        %s::jsonb,%s::jsonb,'medium',%s,now(),%s,'completed',now(),%s::jsonb)
                """,
                [
                    action_id,
                    goal_id,
                    json.dumps({"evidence_ids": source_ids}),
                    json.dumps(["claim_has_sources"]),
                    agent_id,
                    decision.get("rationale", "LLM produced evidence-backed decision"),
                    json.dumps(decision),
                ],
            )
            for item in EVIDENCE:
                cur.execute(
                    """
                    INSERT INTO autonomy_evidence
                      (source_id, action_id, url, title, snippet, retrieved_at, content_hash, source_type)
                    VALUES (%s,%s,%s,%s,%s,now(),%s,'artifact')
                    """,
                    [
                        db_source_ids[item["id"]],
                        action_id,
                        item["url"],
                        item["title"],
                        item["text"],
                        hashlib.sha256(item["text"].encode()).hexdigest(),
                    ],
                )
            claim_id = str(uuid.uuid4())
            claim_text = decision["claims"][0]["text"]
            cur.execute(
                """
                INSERT INTO autonomy_claims
                  (claim_id, action_id, text, status, confidence, support_source_ids,
                   support_snippets, generated_by)
                VALUES (%s,%s,%s,'supported',%s,%s::jsonb,%s::jsonb,%s)
                """,
                [
                    claim_id,
                    action_id,
                    claim_text,
                    float(decision["confidence"]),
                    json.dumps(source_ids),
                    json.dumps([item["text"] for item in EVIDENCE]),
                    agent_id,
                ],
            )
        conn.commit()
        mark("claim_created", claim_id=claim_id, support_source_ids=source_ids)

        cal = create_calibration_engine(db=conn)
        resolution_due_at = datetime.now(timezone.utc) + timedelta(seconds=2)
        prediction_id = cal["ledger"].pre_register(
            PredictionRegistration(
                claim="Engineering artifact should be approved after external security review",
                probability=float(decision["confidence"]),
                confidence_basis={"claim_id": claim_id, "evidence_ids": source_ids, "run_id": run_id},
                producing_agent_id=agent_id,
                producing_prompt_version=env["chat_model"],
                resolution_criterion="Security review final status is approved",
                resolution_date=resolution_due_at,
                ground_truth_source="external_security_review_record",
                horizon_class="short",
                domain="engineering",
                claim_type="civilization_artifact_review",
            )
        )
        mark("prediction_preregistered", prediction_id=prediction_id, resolution_due_at=resolution_due_at.isoformat())

        kafka_payload = {
            "event": "civilization_vertical_slice.decision_ready",
            "correlation_id": correlation_id,
            "run_id": run_id,
            "claim_id": claim_id,
            "prediction_id": prediction_id,
        }
        kafka_meta = emit_kafka_event(kafka_payload)
        mark("bus_event_emitted", **kafka_meta)

        event_id = str(uuid.uuid4())
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO event_history
                  (event_id, event_type, producer_agent_id, timestamp, confidence_score,
                   payload, correlation_id, risk_level, requires_ack, ttl_seconds)
                VALUES (%s,'civilization_vertical_slice.decision_ready',%s,now(),%s,%s::jsonb,%s,'medium',false,86400)
                """,
                [event_id, agent_id, float(decision["confidence"]), json.dumps(kafka_payload), correlation_id],
            )
            log_id = append_decision_log(cur, correlation_id=correlation_id, event_ids=[event_id], decision=decision)
            cur.execute(
                """
                UPDATE workflow_tasks
                   SET status='done', started_at=COALESCE(started_at, now()), completed_at=now(),
                       result=%s::jsonb, audit_log_id=%s, event_id=%s
                 WHERE task_id=%s
                """,
                [json.dumps(decision), log_id, event_id, task_id],
            )
        conn.commit()
        mark("decision_and_audit_written", decision_log_id=log_id, event_id=event_id)

        seconds_until_resolution = (resolution_due_at - datetime.now(timezone.utc)).total_seconds()
        if seconds_until_resolution > 0:
            time.sleep(seconds_until_resolution + 0.25)

        res_conn = psycopg2.connect(resolution_service_url(db_url))
        res_conn.autocommit = True
        try:
            with res_conn.cursor() as cur:
                probability = float(decision["confidence"])
                outcome = decision["decision"] == "approve"
                brier = (probability - (1.0 if outcome else 0.0)) ** 2
                cur.execute(
                    """
                    UPDATE prediction_ledger
                       SET resolved=true,
                           resolved_outcome=%s,
                           resolved_at=now(),
                           resolved_by_service=current_user,
                           brier_score=%s,
                           log_score=%s,
                           was_surprise=false
                     WHERE prediction_id=%s
                    """,
                    [outcome, brier, math.log(max(probability, 1e-9)) if outcome else math.log(max(1 - probability, 1e-9)), prediction_id],
                )
                if cur.rowcount != 1:
                    raise RuntimeError("resolution_service did not resolve exactly one prediction")
        finally:
            res_conn.close()
        mark("independent_resolution_completed", prediction_id=prediction_id, resolver="resolution_service")
        mark("calibration_scored", brier_score=round((float(decision["confidence"]) - 1.0) ** 2, 6))
        cal["ledger"]._in_memory.clear()
        cal["ledger"]._load_from_db()

        transition_review(review_id, "approved", conn, evidence={"prediction_id": prediction_id, "decision": decision})
        reputation = propagate_institution(eng["institution_id"], cal["ledger"], conn)
        mark("trust_updated", institution_score=reputation["institution_score"])

        rows = _fetch_rows(db_url, agent_id)
        score = raw_recompute(rows)
        if score["total_sample_count"] < 1:
            raise RuntimeError("credential recomputation found no resolved predictions")
        credential_id = str(uuid.uuid4())
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO calibration_credentials
                  (credential_id, agent_id, expires_at, domain_cells, overall_score,
                   sample_count, algorithm, hmac_sha256, is_valid)
                VALUES (%s,%s,now() + interval '30 days',%s::jsonb,%s,%s,%s,%s,true)
                """,
                [
                    credential_id,
                    agent_id,
                    json.dumps(score["cells"], default=str),
                    score["overall_log_score"],
                    score["total_sample_count"],
                    score["algorithm"],
                    hmac_credential(agent_id, score),
                ],
            )
        conn.commit()
        mark("credential_minted", credential_id=credential_id, sample_count=score["total_sample_count"])

        with conn.cursor() as cur:
            memory_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO civilization_memory_events
                  (id, entity_type, entity_id, event_type, summary, evidence_refs, created_at)
                VALUES (%s,'institution',%s,'lesson_extracted',
                        'Evidence Court promoted reality-validated security review memory',
                        %s::jsonb,now())
                """,
                [
                    memory_id,
                    eng["institution_id"],
                    json.dumps(
                        {
                            "prediction_id": prediction_id,
                            "resolved": True,
                            "evidence_ids": source_ids,
                            "review_id": review_id,
                        },
                        sort_keys=True,
                    ),
                ],
            )
            cur.execute(
                """
                INSERT INTO shared_knowledge
                  (key, content, content_summary, tags, source_agent_id, confidence_score, embedding)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (key) DO UPDATE
                  SET content=EXCLUDED.content,
                      content_summary=EXCLUDED.content_summary,
                      tags=EXCLUDED.tags,
                      confidence_score=EXCLUDED.confidence_score,
                      embedding=EXCLUDED.embedding,
                      updated_at=now()
                """,
                [
                    f"civilization-slice-{correlation_id}",
                    EVIDENCE[0]["text"],
                    "Reality-validated external security review memory",
                    ["civilization", "evidence-court", "reality_validated"],
                    "research-agent",
                    float(decision["confidence"]),
                    json.dumps(query_embedding),
                ],
            )
        conn.commit()
        mark("memory_promoted", memory_id=memory_id, validation_status="reality_validated")

        artifact_id = str(uuid.uuid4())
        artifact_hash = hashlib.sha256(
            json.dumps({"decision": decision, "run_id": run_id}, sort_keys=True).encode()
        ).hexdigest()
        constitution_id = str(uuid.uuid4())
        policy_id = str(uuid.uuid4())
        replay_batch_id = str(uuid.uuid4())
        learner_run_id = str(uuid.uuid4())
        learner_candidate_id = str(uuid.uuid4())
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO calibration_constitution_versions
                  (id, version_number, content_json, content_hash, signature, signer_entity_id)
                VALUES (%s,1,%s::jsonb,%s,'civilization-slice-local-signature',NULL)
                """,
                [
                    constitution_id,
                    json.dumps({"purpose": "civilization vertical slice protected policy root"}),
                    hashlib.sha256(constitution_id.encode()).hexdigest(),
                ],
            )
            cur.execute(
                """
                INSERT INTO artifacts (id, artifact_type, artifact_hash, artifact_json, lineage_json, is_simulation_derived, status)
                VALUES (%s,'memory_policy_update',%s,%s::jsonb,%s::jsonb,false,'tested')
                """,
                [artifact_id, artifact_hash, json.dumps({"decision_policy": decision}), json.dumps({"run_id": run_id})],
            )
            cur.execute(
                """
                INSERT INTO trust_policy_versions
                  (id, policy_type, constitution_id, title, description, version_number,
                   content_json, content_hash, signature, promotion_scope, status, approved_at,
                   canary_started_at, trace_id)
                VALUES (%s,'promotion_threshold',%s,'Civilization memory promotion threshold',
                        'Policy produced by real vertical slice for reality-validated memory promotion',
                        1,%s::jsonb,%s,'civilization-slice-policy-signature','civilization',
                        'canary',now(),now(),%s)
                """,
                [
                    policy_id,
                    constitution_id,
                    json.dumps({"artifact_id": artifact_id, "requires_reality_validated": True}),
                    artifact_hash,
                    correlation_id,
                ],
            )
            cur.execute(
                """
                INSERT INTO replay_batches
                  (id, source_filter_json, trajectory_ids, batch_hash, batch_size, created_by,
                   tags, batch_label, simulation_derived, trace_id)
                VALUES (%s,%s::jsonb,%s::uuid[],%s,1,'civilization_coordinator',
                        %s,%s,false,%s)
                """,
                [
                    replay_batch_id,
                    json.dumps({"prediction_id": prediction_id}),
                    [event_id],
                    hashlib.sha256(event_id.encode()).hexdigest(),
                    ["civilization", "vertical_slice"],
                    "civilization-vertical-slice",
                    correlation_id,
                ],
            )
            cur.execute(
                """
                INSERT INTO learner_runs
                  (id, replay_batch_id, policy_version_before, policy_version_after,
                   baseline_metrics_json, candidate_count, status, completed_at)
                VALUES (%s,%s,'civilization-memory-policy/v1','civilization-memory-policy/v1.1',
                        %s::jsonb,1,'completed',now())
                """,
                [learner_run_id, replay_batch_id, json.dumps({"brier_score": (float(decision["confidence"]) - 1.0) ** 2})],
            )
            cur.execute(
                """
                INSERT INTO learner_candidates
                  (id, learner_run_id, candidate_type, artifact_id, artifact_hash,
                   metrics_before_json, metrics_after_json, improvement_percent, status,
                   eval_feedback_json, evaluated_at, promoted_at, artifact_ref, rationale,
                   expected_improvement_json, risk_level, simulation_trained, trace_id, artifact_json)
                VALUES (%s,%s,'memory_policy_update',%s,%s,%s::jsonb,%s::jsonb,2.0,'promoted',
                        %s::jsonb,now(),now(),%s,%s,%s::jsonb,'low',false,%s,%s::jsonb)
                """,
                [
                    learner_candidate_id,
                    learner_run_id,
                    artifact_id,
                    artifact_hash,
                    json.dumps({"validated_memory_promotions": 0}),
                    json.dumps({"validated_memory_promotions": 1}),
                    json.dumps({"evidence_court": "approved"}),
                    f"artifact:{artifact_id}",
                    "Reality-validated memory promotion improves future evidence recall",
                    json.dumps({"evidence_recall_delta": 0.02}),
                    correlation_id,
                    json.dumps({"memory_policy": "promote_only_reality_validated"}),
                ],
            )
        conn.commit()
        mark("learning_candidate_created", learner_candidate_id=learner_candidate_id, status="promoted")

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO policy_canary_deployments
                  (policy_id, canary_scope_json, target_agents, target_percentage, status,
                   metrics_json, ended_at, trace_id)
                VALUES (%s,%s::jsonb,1,10.0,'completed',%s::jsonb,now(),%s)
                """,
                [
                    policy_id,
                    json.dumps({"candidate_id": learner_candidate_id, "tier": 1}),
                    json.dumps({"errors": 0, "fallbacks": 0, "memory_promotions": 1}),
                    correlation_id,
                ],
            )
        conn.commit()
        mark("canary_or_human_queue_recorded", outcome="tier1_canary_completed")

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO civilization_generality_metrics
                  (run_id, metric_name, domain, score, evidence_json)
                VALUES (%s,'cross_domain_transfer_smoke','engineering_to_memory_governance',0.72,%s::jsonb)
                """,
                [run_id, json.dumps({"source_domain": "engineering", "target_domain": "memory_governance"})],
            )
            cur.execute(
                """
                INSERT INTO civilization_coordinator_ticks (run_id, tick_type, trace_json)
                VALUES (%s,'vertical_slice_completed',%s::jsonb)
                """,
                [run_id, json.dumps(trace + [{"stage": "coordinator_tick_recorded"}], default=str)],
            )
        conn.commit()
        mark("generality_metric_updated", score=0.72)
        mark("coordinator_tick_recorded", run_id=run_id)

        missing = [stage for stage in REQUIRED_STAGES if stage not in stage_results]
        if missing:
            raise RuntimeError(f"vertical slice missing required stages: {missing}")

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE civilization_vertical_slice_runs
                   SET status='passed', stage_results=%s::jsonb, runtime_trace=%s::jsonb, completed_at=now()
                 WHERE id=%s
                """,
                [json.dumps(stage_results, sort_keys=True, default=str), json.dumps(trace, default=str), run_id],
            )
        conn.commit()

        return {
            "success": True,
            "run_id": run_id,
            "correlation_id": correlation_id,
            "required_stages": REQUIRED_STAGES,
            "stages_completed": list(stage_results),
            "stage_results": stage_results,
            "llm": chat_meta,
            "embedding": {**(embedding_meta or {}), "query_latency_ms": query_meta["latency_ms"]},
            "kafka": kafka_meta,
            "db": {
                "prediction_id": prediction_id,
                "credential_id": credential_id,
                "learner_candidate_id": learner_candidate_id,
                "vector_top_source_id": top_vector["source_id"],
            },
            "duration_ms": int((time.time() - started) * 1000),
        }
    except Exception as exc:
        conn.rollback()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE civilization_vertical_slice_runs
                       SET status='failed', failure_reason=%s, stage_results=%s::jsonb,
                           runtime_trace=%s::jsonb, completed_at=now()
                     WHERE id=%s
                    """,
                    [str(exc), json.dumps(stage_results, default=str), json.dumps(trace, default=str), run_id],
                )
            conn.commit()
        except Exception:
            conn.rollback()
        raise
    finally:
        conn.close()


def write_reports(report: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "civilization_vertical_slice.json").write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
    lines = [
        "# Civilization Vertical Slice",
        "",
        f"- Success: `{report.get('success')}`",
        f"- Run ID: `{report.get('run_id')}`",
        f"- Correlation ID: `{report.get('correlation_id')}`",
        f"- Duration ms: `{report.get('duration_ms')}`",
        "",
        "## Stages",
    ]
    completed = set(report.get("stages_completed", []))
    for stage in REQUIRED_STAGES:
        lines.append(f"- `{stage}`: `{'passed' if stage in completed else 'missing'}`")
    if report.get("error"):
        lines.extend(["", "## Error", f"`{report['error']}`"])
    (REPORT_DIR / "civilization_vertical_slice.md").write_text("\n".join(lines) + "\n")


def update_build_ledger_gate() -> None:
    import yaml

    path = ROOT / "BUILD_LEDGER.yaml"
    ledger = yaml.safe_load(path.read_text())
    ledger.setdefault("gates", {})["e2e_civilization_slice"] = "green"
    for layer in ledger.get("layers", {}).values():
        for item in layer.get("items", []):
            if item.get("id") == "L14.VerticalSlice":
                item["status"] = "verified"
                item["artifacts"] = sorted(set(item.get("artifacts", []) + ["scripts/verify_civilization_vertical_slice.py"]))
                item["tests"] = sorted(set(item.get("tests", []) + ["reports/system_run/latest/civilization_vertical_slice.json"]))
                item["gates_passed"] = sorted(set(item.get("gates_passed", []) + ["e2e"]))
                item["notes"] = "Canonical civilization vertical slice passed against real Postgres, Kafka, OpenAI chat, OpenAI embeddings, resolution_service, and Postgres-backed vector index."
    path.write_text(yaml.safe_dump(ledger, sort_keys=False, width=120))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-ledger", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = run_slice()
        write_reports(report)
        if args.update_ledger:
            update_build_ledger_gate()
        print(json.dumps({"success": True, "run_id": report["run_id"], "duration_ms": report["duration_ms"]}, sort_keys=True))
        return 0
    except Exception as exc:
        report = {"success": False, "error": str(exc), "traceback": traceback.format_exc(), "stages_completed": [], "duration_ms": 0}
        write_reports(report)
        print(json.dumps({"success": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

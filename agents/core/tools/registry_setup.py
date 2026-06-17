"""
Register all real tool handlers into the tool_registry at startup.
Import this module once (e.g. from base_agent.__init__) to wire everything.
"""
from __future__ import annotations

from ..tool_registry import register_tool
from .handlers import (
    handle_audit_log,
    handle_event_bus,
    handle_shared_knowledge_read,
    handle_shared_knowledge_write,
    handle_memory_read,
    handle_memory_write,
    handle_prompt_registry_read,
    handle_human_override,
)

_TOOL_SCHEMAS: dict[str, dict] = {
    "audit_log": {
        "name": "audit_log",
        "description": "Write an immutable audit entry to the decision log.",
        "parameters": {
            "type": "object",
            "properties": {
                "action_type": {"type": "string", "enum": ["decision","api_call","event_published","escalation"]},
                "input_summary":  {"type": "string"},
                "output_summary": {"type": "string"},
                "confidence_score": {"type": "number"},
                "risk_level": {"type": "string", "enum": ["low","medium","high","critical"]},
            },
            "required": ["action_type","input_summary","output_summary","confidence_score","risk_level"],
        },
    },
    "event_bus": {
        "name": "event_bus",
        "description": "Publish a signed event to the Kafka event bus.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_type":        {"type": "string"},
                "payload":           {"type": "object"},
                "confidence_score":  {"type": "number"},
                "risk_level":        {"type": "string", "enum": ["low","medium","high","critical"]},
                "requires_ack":      {"type": "boolean"},
                "correlation_id":    {"type": "string"},
            },
            "required": ["event_type","payload","confidence_score","risk_level","requires_ack"],
        },
    },
    "shared_knowledge": {
        "name": "shared_knowledge",
        "description": "Read from the shared knowledge base (semantic search).",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    },
    "shared_knowledge_write": {
        "name": "shared_knowledge_write",
        "description": "Write to the shared knowledge base (permitted agents only).",
        "parameters": {
            "type": "object",
            "properties": {
                "key":              {"type": "string"},
                "content":          {"type": "string"},
                "confidence_score": {"type": "number"},
                "tags":             {"type": "array", "items": {"type": "string"}},
            },
            "required": ["key","content","confidence_score"],
        },
    },
    "memory_read": {
        "name": "memory_read",
        "description": "Read a value from agent-private memory.",
        "parameters": {
            "type": "object",
            "properties": {
                "key":       {"type": "string"},
                "namespace": {"type": "string", "default": "default"},
            },
            "required": ["key"],
        },
    },
    "memory_write": {
        "name": "memory_write",
        "description": "Write a value to agent-private memory.",
        "parameters": {
            "type": "object",
            "properties": {
                "key":         {"type": "string"},
                "value":       {},
                "namespace":   {"type": "string", "default": "default"},
                "ttl_seconds": {"type": "integer"},
            },
            "required": ["key","value"],
        },
    },
    "prompt_registry": {
        "name": "prompt_registry",
        "description": "Read a versioned system prompt from the prompt registry.",
        "parameters": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string"},
                "version":  {"type": "string"},
            },
            "required": ["agent_id"],
        },
    },
    "human_override_interface": {
        "name": "human_override_interface",
        "description": "Queue an action for human approval. The action is BLOCKED until approved.",
        "parameters": {
            "type": "object",
            "properties": {
                "action":     {"type": "string"},
                "risk_level": {"type": "string", "enum": ["high","critical"]},
                "context":    {"type": "object"},
                "risk_score": {"type": "number"},
            },
            "required": ["action","risk_level","context"],
        },
    },
}


def register_all_tools() -> None:
    """Register every tool handler. Call once at startup."""
    register_tool("audit_log",             _TOOL_SCHEMAS["audit_log"],             handle_audit_log)
    register_tool("event_bus",             _TOOL_SCHEMAS["event_bus"],             handle_event_bus)
    register_tool("shared_knowledge",      _TOOL_SCHEMAS["shared_knowledge"],      handle_shared_knowledge_read)
    register_tool("shared_knowledge_write",_TOOL_SCHEMAS["shared_knowledge_write"],handle_shared_knowledge_write)
    register_tool("memory_read",           _TOOL_SCHEMAS["memory_read"],           handle_memory_read)
    register_tool("memory_write",          _TOOL_SCHEMAS["memory_write"],          handle_memory_write)
    register_tool("prompt_registry",       _TOOL_SCHEMAS["prompt_registry"],       handle_prompt_registry_read)
    register_tool("human_override_interface", _TOOL_SCHEMAS["human_override_interface"], handle_human_override)

"""Fail-closed checks for production secret defaults."""
from __future__ import annotations

import os
import re
from collections.abc import Mapping


DEV_DEFAULTS = {
    "EVENT_BUS_HMAC_KEY": {"", "dev-insecure-key"},
    "EVENT_BUS_SIGNING_KEY": {"", "dev-key-replace-in-production"},
    "RESERVE_SIGNING_KEY": {"dev-insecure-key"},
    "RESOLUTION_SERVICE_PASSWORD": {"", "resolution-service-dev-password"},
    "VAULT_TOKEN": {"", "root"},
    "JWT_SECRET": {"", "change-me-generate-with-openssl-rand-hex-64"},
    "AGENTCO_API_KEY": {"", "dev-api-key"},
}


def assert_production_secrets(env: Mapping[str, str] | None = None) -> None:
    env = env or os.environ
    if env.get("AGENTCO_ENV") != "production":
        return

    failures: list[str] = []
    for key, defaults in DEV_DEFAULTS.items():
        if env.get(key, "") in defaults:
            failures.append(key)

    for key in ("DATABASE_URL", "AGENTCO_TEST_DATABASE_URL"):
        value = env.get(key, "")
        if re.search(r"://[^:]+:password@", value):
            failures.append(key)

    if failures:
        raise RuntimeError(
            "Refusing to start in production with dev-default or missing secrets: "
            + ", ".join(sorted(set(failures)))
        )

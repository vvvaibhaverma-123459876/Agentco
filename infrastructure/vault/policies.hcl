# ============================================================
# AgentCo HashiCorp Vault Policies
# ============================================================
# Apply each policy block with:
#   vault policy write <policy-name> policies.hcl
# or import individual policy files per department.
#
# Secret engine: KV v2 mounted at "secrets/"
# Path convention: secrets/agentco/<department>/<secret-name>
# ============================================================

# ------------------------------------------------------------
# Executive Agents (CEO, CFO, COO, CTO cluster)
# Read/write their own namespace; read shared config.
# ------------------------------------------------------------
path "secrets/data/agentco/executive/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secrets/metadata/agentco/executive/*" {
  capabilities = ["list", "read", "delete"]
}

path "secrets/data/agentco/shared/*" {
  capabilities = ["read", "list"]
}

path "secrets/metadata/agentco/shared/*" {
  capabilities = ["list", "read"]
}

# Executive agents may read all department secrets for oversight.
path "secrets/data/agentco/+/*" {
  capabilities = ["read", "list"]
}

path "secrets/metadata/agentco/+/*" {
  capabilities = ["list", "read"]
}

# ------------------------------------------------------------
# Engineering Agents
# Read/write engineering namespace; read shared and infra secrets.
# ------------------------------------------------------------
path "secrets/data/agentco/engineering/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secrets/metadata/agentco/engineering/*" {
  capabilities = ["list", "read", "delete"]
}

path "secrets/data/agentco/shared/*" {
  capabilities = ["read", "list"]
}

path "secrets/metadata/agentco/shared/*" {
  capabilities = ["list", "read"]
}

# Engineering agents need infra secrets (DB credentials, cloud keys).
path "secrets/data/agentco/infrastructure/*" {
  capabilities = ["read", "list"]
}

path "secrets/metadata/agentco/infrastructure/*" {
  capabilities = ["list", "read"]
}

# ------------------------------------------------------------
# Product Agents
# Read-only access to product namespace and shared config.
# Product agents do not need write access to any production secrets.
# ------------------------------------------------------------
path "secrets/data/agentco/product/*" {
  capabilities = ["read", "list"]
}

path "secrets/metadata/agentco/product/*" {
  capabilities = ["list", "read"]
}

path "secrets/data/agentco/shared/*" {
  capabilities = ["read", "list"]
}

path "secrets/metadata/agentco/shared/*" {
  capabilities = ["list", "read"]
}

# ------------------------------------------------------------
# Sales Agents
# Read/write sales namespace (CRM keys, outreach credentials);
# read shared config only.
# ------------------------------------------------------------
path "secrets/data/agentco/sales/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secrets/metadata/agentco/sales/*" {
  capabilities = ["list", "read", "delete"]
}

path "secrets/data/agentco/shared/*" {
  capabilities = ["read", "list"]
}

path "secrets/metadata/agentco/shared/*" {
  capabilities = ["list", "read"]
}

# ------------------------------------------------------------
# Marketing Agents
# Read/write marketing namespace; read shared config.
# ------------------------------------------------------------
path "secrets/data/agentco/marketing/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secrets/metadata/agentco/marketing/*" {
  capabilities = ["list", "read", "delete"]
}

path "secrets/data/agentco/shared/*" {
  capabilities = ["read", "list"]
}

path "secrets/metadata/agentco/shared/*" {
  capabilities = ["list", "read"]
}

# ------------------------------------------------------------
# Customer Experience Agents
# Read/write CX namespace (support tool keys, survey APIs);
# read shared config.
# ------------------------------------------------------------
path "secrets/data/agentco/customer-experience/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secrets/metadata/agentco/customer-experience/*" {
  capabilities = ["list", "read", "delete"]
}

path "secrets/data/agentco/shared/*" {
  capabilities = ["read", "list"]
}

path "secrets/metadata/agentco/shared/*" {
  capabilities = ["list", "read"]
}

# ------------------------------------------------------------
# People-Ops Agents
# Read-only to PeopleOps namespace (HRIS API keys, ATS tokens).
# Explicitly denied write capability — no agent may alter
# production HR records without a human approval step.
# ------------------------------------------------------------
path "secrets/data/agentco/people-ops/*" {
  capabilities = ["read", "list"]
}

path "secrets/metadata/agentco/people-ops/*" {
  capabilities = ["list", "read"]
}

path "secrets/data/agentco/shared/*" {
  capabilities = ["read", "list"]
}

path "secrets/metadata/agentco/shared/*" {
  capabilities = ["list", "read"]
}

# Explicitly deny create/update/delete/patch on people-ops secrets.
path "secrets/data/agentco/people-ops/*" {
  capabilities = ["deny"]
  denied_parameters = {
    "*" = []
  }
}

# Override: allow read back after deny block (Vault evaluates most permissive).
# Implemented by splitting into two separate named policies:
#   1. people-ops-agents-read  (this file section)
#   2. people-ops-agents-deny-write  (applied as additional policy)
#
# Deny write policy to attach alongside this one:
#   vault policy write people-ops-agents-deny-write - <<EOF
#   path "secrets/data/agentco/people-ops/*" {
#     capabilities = ["deny"]
#   }
#   EOF
# Note: attach read policy first, then the deny-write policy wins for mutations.

# ------------------------------------------------------------
# Legal Agents
# Strictly read-only — legal agents observe and flag but never
# mutate secrets. Scoped to legal namespace and shared config.
# ------------------------------------------------------------
path "secrets/data/agentco/legal/*" {
  capabilities = ["read", "list"]
}

path "secrets/metadata/agentco/legal/*" {
  capabilities = ["list", "read"]
}

path "secrets/data/agentco/shared/*" {
  capabilities = ["read", "list"]
}

path "secrets/metadata/agentco/shared/*" {
  capabilities = ["list", "read"]
}

# Deny all write operations for legal agents.
path "secrets/data/agentco/legal/*" {
  capabilities = ["read", "list"]
  # No create / update / delete / patch — omission enforces restriction.
}

# ------------------------------------------------------------
# Design Agents
# Read-only to design namespace (Figma tokens, asset CDN keys);
# read shared config.
# ------------------------------------------------------------
path "secrets/data/agentco/design/*" {
  capabilities = ["read", "list"]
}

path "secrets/metadata/agentco/design/*" {
  capabilities = ["list", "read"]
}

path "secrets/data/agentco/shared/*" {
  capabilities = ["read", "list"]
}

path "secrets/metadata/agentco/shared/*" {
  capabilities = ["list", "read"]
}

# ------------------------------------------------------------
# Shared / Common Policy (attach to all agent tokens)
# Allows agents to renew their own tokens and look up their
# own token info — required for credential rotation.
# ------------------------------------------------------------
path "auth/token/lookup-self" {
  capabilities = ["read"]
}

path "auth/token/renew-self" {
  capabilities = ["update"]
}

path "auth/token/revoke-self" {
  capabilities = ["update"]
}

path "sys/capabilities-self" {
  capabilities = ["update"]
}

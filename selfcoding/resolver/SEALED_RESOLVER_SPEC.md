# SEALED RESOLVER SPECIFICATION

## Purpose
The sealed resolver is the structural guardrail that prevents generated code from:
- Creating, modifying, or writing to ground-truth data
- Inspecting or modifying the resolver's internals
- Injecting configuration or alternative data sources
- Altering calibration scoring logic

It is not a feature. It is the wall. Every byte of this module is immutable and external to generated code.

## Public Interface (ONLY what generated code can call)

### `score_prediction(instrument, prediction_date, predicted_direction, confidence) -> dict`

**Input parameters:**
- `instrument` (str): Instrument name, e.g., "NIFTY 50"
- `prediction_date` (str): Date prediction was made, format "YYYY-MM-DD"
- `predicted_direction` (str): "up" or "down"
- `confidence` (float): [0.0, 1.0]

**Returns (always, even on error):**
```json
{
  "prediction_date": "2024-10-21",
  "resolution_date": "2024-10-22",
  "instrument": "NIFTY 50",
  "predicted_direction": "up",
  "confidence": 0.75,
  "actual_open": 24956.15,
  "actual_close": 24781.10,
  "actual_direction": "down",
  "hit": false,
  "score": -0.75,
  "timestamp": "2026-06-20T12:00:00+00:00"
}
```

**Score semantics:**
- `hit=true` → `score = confidence` (reward)
- `hit=false` → `score = -confidence` (penalty)

**Errors raised (cannot be caught by generated code; propagate to parent):**
- `ValueError`: Invalid prediction_date format, invalid direction, confidence out of range
- `FileNotFoundError`: Instrument not found in frozen data, no next trading day
- `PermissionError`: Read access denied to frozen data (structural failure, fatal)
- `ResolverInaccessibleError`: Generated code attempted to access internals (structural failure, fatal)

## What Generated Code CANNOT Do

### Cannot import or introspect resolver internals
```python
# FORBIDDEN:
from selfcoding.resolver.sealed_resolver import SealedResolver
from selfcoding.resolver.sealed_resolver import _load_instrument_data
import inspect; inspect.getsource(resolver.score_prediction)
```

Generated code receives ONLY the **result** of `score_prediction()` calls, never the resolver instance or any internal methods.

### Cannot write to frozen data
```python
# FORBIDDEN:
df.to_csv("/path/to/frozen/data/nifty_50_REAL.csv")
with open("/path/to/frozen/data/METADATA.json", "w") as f:
    f.write(...)
```

The frozen_data_path is mounted read-only at the filesystem level. Writes fail with `PermissionError` before reaching Python code.

### Cannot modify the resolver module itself
```python
# FORBIDDEN:
import selfcoding.resolver.sealed_resolver as sr
sr.SealedResolver.score_prediction = custom_scoring_function
del sr.SealedResolver.__setattr__
```

The module is read-only on disk and imported into the parent process (not generated code). Generated code runs in a child process and cannot modify parent imports.

### Cannot create alternative data sources
```python
# FORBIDDEN:
custom_data = {"NIFTY 50": {"2024-10-21": {"open": 0, "close": 1}}}
# Then pass to resolver (resolver.score_prediction doesn't accept data parameter)
```

The resolver has NO parameter for data source. It reads from the frozen mount only.

### Cannot precompute or smuggle answers
```python
# FORBIDDEN:
# Read resolver source, reverse-engineer scoring
with open("/path/to/sealed_resolver.py") as f:
    source = f.read()  # Could work, but...
    
# Try to pass pre-computed answers to resolver
resolver.score_prediction(..., "precomputed_answer_up")  # Invalid direction, raises ValueError
```

The resolver accepts only valid inputs and produces only valid outputs. Any attempt to smuggle data fails at the interface.

## Filesystem Permissions (Structural Enforcement)

### Frozen Data Path
- **Location:** `/Users/Zet/Desktop/Agentco/evals/experiments/nse_phase6_data_frozen/`
- **Permissions:** `755` (owner r+w, group r, others r) OR mounted `ro` in container
- **Process permission:** Generated code runs with a UID that has NO write access to this path
- **Enforcement:** OS-level filesystem, not Python code

### Sealed Resolver Module
- **Location:** `/Users/Zet/Desktop/Agentco/selfcoding/resolver/sealed_resolver.py`
- **Permissions:** `644` (immutable at deployment time)
- **Process permission:** Cannot be modified or reloaded by generated code
- **Enforcement:** Child process isolation + read-only mount of parent imports

### Generated Code Scratch Directory
- **Location:** `/Users/Zet/Desktop/Agentco/selfcoding/sandbox/scratch/`
- **Permissions:** `700` (owner only)
- **Scope:** Generated code CAN read/write here, isolated from everything else
- **Enforcement:** chroot or similar at sandbox exec level

## Invariants

### Invariant 1: Immutability
Once instantiated in the parent process, the SealedResolver cannot be modified:
- `__setattr__` raises `ResolverInaccessibleError` on any assignment
- Data cache is read-only (loaded once, never reloaded)
- Public method is the only reachable interface

### Invariant 2: Data Isolation
Frozen data is read-only at BOTH code and OS level:
- Code: No `write()` method on the resolver
- OS: Process has no write permission to frozen_data_path
- If both fail, escalate to fatal error (parent process exits)

### Invariant 3: Interface Minimalism
Generated code can ONLY call `score_prediction()` with valid inputs:
- Signature is fixed: no kwargs, no injection points
- Invalid inputs raise ValueError (fails fast)
- Valid inputs produce deterministic output from frozen data

### Invariant 4: No Escape Hatch
There is no way for generated code to reach the resolver instance or frozen data:
- Generated code runs in a child process (or container)
- Parent process does not expose resolver reference
- Resolver is instantiated in parent, results passed to child as dicts (not objects)
- Child cannot import parent modules (sandbox enforcement)

## Testing (See test_wall_holds.py)

Every breach attempt in the adversarial test must fail:
1. **Overwrite frozen data**: Write fails (PermissionError at OS level)
2. **Modify resolver internals**: Cannot import or access (structural, not behavioral)
3. **Reverse-engineer scoring**: Source readable but signature is fixed, no backdoors
4. **Inject alternate data**: Interface accepts no data parameter
5. **Precompute answers**: Interface accepts only valid direction/confidence, enforces semantics

## Recovery and Escalation

If ANY breach is successful:
- The wall is NOT structural — do not deploy
- Escalate to a fatal error (parent process exits immediately)
- Audit log records which breach succeeded
- Operator review required before re-enabling self-extension

## No Exceptions

This specification is invariant. There are no legitimate reasons for generated code to:
- Write to frozen data
- Modify the resolver
- Access resolver internals
- Inject configuration or alternate data

If a use case requires any of these, the use case is outside the scope of self-extension and must be handled by the operator (human) manually.

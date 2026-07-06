# Python Requirements

`requirements.lock.txt` is the pinned install set for CI and local verification.
It is generated from:

- `requirements/requirements-runtime.txt`
- `requirements/requirements-dev.txt`
- `agents/requirements.txt`

Regenerate after changing any input requirements file:

```bash
uv pip compile requirements/requirements-runtime.txt requirements/requirements-dev.txt agents/requirements.txt -o requirements/requirements.lock.txt
```

Install from the lockfile:

```bash
python3.13 -m pip install -r requirements/requirements.lock.txt
```

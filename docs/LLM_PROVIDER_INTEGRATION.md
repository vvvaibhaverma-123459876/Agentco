# LLM Provider Integration Guide

**Status:** Unified multi-provider LLM service ready  
**Supported Providers:** 10+ (OpenAI, Anthropic, Ollama, Groq, Fireworks, Together, etc.)

---

## Quick Start

### Using OpenAI (Default)

```python
from autonomy import get_llm

# Get LLM service (uses OpenAI by default)
llm = get_llm("standard")

# Make a completion
response = llm.complete(
    prompt="Analyze this claim: ...",
    system="You are analyzing evidence for a trustworthiness system",
    temperature=0.7,
    max_tokens=500
)

print(response)
```

### Using Any Provider (Anthropic, Ollama, etc.)

```python
import os
from autonomy import get_llm

# Switch provider via environment variables
os.environ["LLM_PROVIDER"] = "anthropic"
os.environ["LLM_API_KEY"] = "sk-ant-..."
os.environ["LLM_MODEL_DEFAULT"] = "claude-opus-4-1"

# Same code works with Claude
llm = get_llm("standard")
response = llm.complete("Same prompt works with any provider...")
```

---

## Supported Providers

### OpenAI-Compatible (Same API format)
- **OpenAI** (default)
  ```
  Provider: openai
  Models: gpt-4o, gpt-4o-mini, gpt-4-turbo
  Default: gpt-4o-mini (standard tier)
  ```

- **Ollama** (local)
  ```
  Provider: ollama
  Base URL: http://localhost:11434/v1
  Models: phi4, qwen2.5:7b, llama2, etc.
  Default: qwen2.5:7b
  ```

- **Groq** (fast inference)
  ```
  Provider: groq
  Base URL: https://api.groq.com/openai/v1
  Models: llama-3.1-70b-versatile, llama-3.1-8b-instant
  Default: llama-3.1-8b-instant
  ```

- **Together AI**
  ```
  Provider: together
  Base URL: https://api.together.xyz/v1
  ```

- **Fireworks**
  ```
  Provider: fireworks
  Base URL: https://api.fireworks.ai/inference/v1
  ```

- **Mistral**
  ```
  Provider: mistral
  Base URL: https://api.mistral.ai/v1
  Models: mistral-large, mistral-medium, mistral-small
  ```

- **DeepSeek**
  ```
  Provider: deepseek
  Base URL: https://api.deepseek.com/v1
  ```

- **OpenRouter**
  ```
  Provider: openrouter
  Base URL: https://openrouter.ai/api/v1
  ```

- **Anyscale**
  ```
  Provider: anyscale
  Base URL: https://api.endpoints.anyscale.com/v1
  ```

### Native Adapters (Custom API format)
- **Anthropic**
  ```
  Provider: anthropic
  Models: claude-opus-4-1, claude-sonnet-4-6, claude-haiku-4-5
  Default: claude-haiku-4-5 (standard tier)
  ```

---

## Configuration

### Environment Variables

```bash
# Global provider configuration
export LLM_PROVIDER=openai          # or: anthropic, ollama, groq, etc.
export LLM_API_KEY=sk-...           # API key for the provider
export LLM_BASE_URL=https://...     # Optional: custom base URL

# Tier-specific overrides (optional)
export LLM_PROVIDER_STANDARD=openai
export LLM_API_KEY_STANDARD=sk-...
export LLM_MODEL_STANDARD=gpt-4o-mini

# Model configuration
export LLM_MODEL_DEFAULT=gpt-4o-mini
export LLM_MODEL_FRONTIER=gpt-4o
export LLM_MODEL_CODER=gpt-4o-mini
```

### Tiers

Agentco uses 4 tiers with specific use cases:

- **frontier** (most capable)
  - Used for: Complex reasoning, decision-making
  - Default: gpt-4o (OpenAI), claude-opus (Anthropic)

- **standard** (balanced)
  - Used for: General completions, analysis
  - Default: gpt-4o-mini (OpenAI), claude-haiku (Anthropic)

- **monitor** (lightweight)
  - Used for: Quick checks, validation
  - Default: gpt-4o-mini, claude-haiku

- **coder** (code-focused)
  - Used for: Code generation, analysis
  - Default: gpt-4o-mini (OpenAI), claude-sonnet (Anthropic)

---

## Integration in Components

### Before (Hardcoded - DON'T DO THIS)

```python
# Bad: hardcoded OpenAI
from openai import OpenAI

client = OpenAI(api_key="sk-...")
response = client.chat.completions.create(
    model="gpt-4o-mini",  # Fixed to OpenAI
    messages=[...]
)
```

### After (Provider-Agnostic - DO THIS)

```python
# Good: works with any provider
from autonomy import get_llm

llm = get_llm("standard")  # Works with OpenAI, Anthropic, Ollama, etc.
response = llm.complete(
    prompt="Analyze this...",
    system="You are...",
)
```

---

## How Components Should Use LLM

### Learning Loop Integration

```python
from autonomy import get_llm

class AutonomousLearningLoop:
    def __init__(self):
        self.llm = get_llm("frontier")  # Use best model for reasoning
        
    def extract_claims(self, signal_text: str) -> list[str]:
        response = self.llm.complete(
            prompt=signal_text,
            system="Extract factual claims from this signal",
            max_tokens=500
        )
        return self._parse_claims(response)
    
    def generate_hypothesis(self, claims: list[str]) -> dict:
        response = self.llm.complete(
            prompt=f"Given these claims: {claims}",
            system="Generate a testable hypothesis",
            max_tokens=300
        )
        return self._parse_hypothesis(response)
```

### Ingestion Pipeline Integration

```python
from autonomy import get_llm

class IntelligentClaimExtractor:
    def __init__(self):
        self.llm = get_llm("standard")  # Balanced for document processing
    
    def extract(self, document_content: str) -> list[str]:
        response = self.llm.complete(
            prompt=document_content,
            system="Extract key factual claims from this document",
            max_tokens=1000
        )
        return self._parse_claims(response)
```

### Governance Integration

```python
from autonomy import get_llm

class GovernanceDecisionMaker:
    def __init__(self):
        self.llm = get_llm("frontier")  # Best reasoning for decisions
    
    def reason_about_proposal(self, proposal: dict) -> str:
        response = self.llm.complete(
            prompt=f"Evaluate this proposal: {proposal}",
            system="You are a governance reasoner. Provide brief rationale.",
            temperature=0.5  # More consistent for decisions
        )
        return response
```

---

## Batch Operations

```python
from autonomy import get_llm

llm = get_llm("standard")

# Process multiple items
prompts = [
    "Analyze claim 1",
    "Analyze claim 2",
    "Analyze claim 3",
]

results = llm.batch_complete(
    prompts,
    system="You are analyzing claims",
    max_tokens=200
)

print(results)  # List of responses
```

---

## Checking Provider Info

```python
from autonomy import get_llm

llm = get_llm("standard")
info = llm.get_provider_info()

print(info)
# {
#   'tier': 'standard',
#   'provider': 'openai',
#   'model': 'gpt-4o-mini',
#   'base_url': 'https://api.openai.com/v1',
#   'provider_type': 'openai_compatible',
#   'is_local': False
# }
```

---

## Error Handling

```python
from autonomy import get_llm
from runtime.base_agent.provider_config import ConfigurationError

try:
    llm = get_llm("standard")
    response = llm.complete("Prompt...")
except ConfigurationError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"LLM error: {e}")
```

---

## Testing with Different Providers

```bash
# Test with OpenAI (default)
export LLM_PROVIDER=openai
python3 my_script.py

# Test with Anthropic
export LLM_PROVIDER=anthropic
export LLM_API_KEY=sk-ant-...
python3 my_script.py

# Test with local Ollama
export LLM_PROVIDER=ollama
export LLM_BASE_URL=http://localhost:11434/v1
python3 my_script.py  # No API key needed for Ollama
```

---

## Next Steps: Component Integration

To make ALL layers use real LLM:

1. **Learning Loop** - Use `get_llm("frontier")` for claim extraction
2. **Ingestion** - Use `get_llm("standard")` for document understanding
3. **RAG System** - Use `get_llm("standard")` for generation
4. **Governance** - Use `get_llm("frontier")` for reasoning
5. **Validation** - Use `get_llm("monitor")` for checks
6. **Simulation** - Use `get_llm("standard")` for scenario testing

Each component gets the right tier for its task, configured at runtime via environment variables.

---

## Summary

✅ **Any provider can be used** - OpenAI, Anthropic, Ollama, Groq, etc.  
✅ **No hardcoding required** - Configure via environment variables  
✅ **Consistent API** - All components use `get_llm()` and `.complete()`  
✅ **Easy switching** - Change provider without code changes  
✅ **Tier-based allocation** - Frontier tasks get best models, monitors get lightweight ones  


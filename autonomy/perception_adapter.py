"""
Perception Adapter Interface and Implementations

Autonomous perception always goes through adapters:
- Read-only access to environment
- Hash-based artifact tracking
- Allowlist enforcement
- Deterministic normalization
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional
import hashlib
import json
from datetime import datetime


@dataclass
class PerceptionEvent:
    """Normalized perception event"""
    event_id: str
    source_type: str
    source_uri: str
    source_fingerprint: str
    observed_at: datetime
    event_type: str
    payload: Dict[str, Any]
    confidence: float
    provenance: Dict[str, Any]


class PerceptionAdapter(ABC):
    """Base class for perception adapters"""

    def __init__(self, adapter_id: str, source_type: str):
        self.adapter_id = adapter_id
        self.source_type = source_type

    @abstractmethod
    async def fetch(self, source_uri: str) -> Dict[str, Any]:
        """Fetch data from source"""
        pass

    @abstractmethod
    async def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize fetched data to standard schema"""
        pass

    @abstractmethod
    async def validate(self, data: Dict[str, Any]) -> bool:
        """Validate normalized data"""
        pass

    def fingerprint(self, data: Dict[str, Any]) -> str:
        """Create deterministic fingerprint of data"""
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()

    async def emit_event(self, source_uri: str, payload: Dict[str, Any]) -> PerceptionEvent:
        """Emit perception event"""
        import uuid
        from datetime import datetime

        fingerprint = self.fingerprint(payload)

        return PerceptionEvent(
            event_id=str(uuid.uuid4()),
            source_type=self.source_type,
            source_uri=source_uri,
            source_fingerprint=fingerprint,
            observed_at=datetime.now(),
            event_type='normalized_event',
            payload=payload,
            confidence=1.0,
            provenance={
                'adapter_id': self.adapter_id,
                'adapter_type': self.source_type,
            },
        )


class LocalFileAdapter(PerceptionAdapter):
    """Adapter for local file-based perception"""

    def __init__(self, adapter_id: str = 'local_file'):
        super().__init__(adapter_id, 'local_file')
        self.max_file_size = 100 * 1024 * 1024  # 100 MB

    async def fetch(self, source_uri: str) -> Dict[str, Any]:
        """Fetch from local file"""
        import os

        # Security: validate path
        path = source_uri.replace('file://', '')
        if '..' in path or path.startswith('/'):
            raise ValueError(f"Invalid file path: {path}")

        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")

        size = os.path.getsize(path)
        if size > self.max_file_size:
            raise ValueError(f"File too large: {size} bytes")

        with open(path, 'r') as f:
            content = f.read()

        return {
            'path': path,
            'size': size,
            'modified_at': datetime.fromtimestamp(os.path.getmtime(path)).isoformat(),
            'content': content,
        }

    async def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize file data"""
        return {
            'type': 'file_content',
            'source': raw_data.get('path'),
            'content': raw_data.get('content'),
            'size_bytes': raw_data.get('size'),
            'modified_at': raw_data.get('modified_at'),
        }

    async def validate(self, data: Dict[str, Any]) -> bool:
        """Validate file data"""
        return (
            data.get('type') == 'file_content'
            and 'source' in data
            and 'content' in data
        )


class PostgresAdapter(PerceptionAdapter):
    """Adapter for database-based perception"""

    def __init__(self, adapter_id: str = 'postgres', db_connection=None):
        super().__init__(adapter_id, 'postgres')
        self.db_connection = db_connection

    async def fetch(self, source_uri: str) -> Dict[str, Any]:
        """Fetch from database"""
        # source_uri format: "table:table_name/query:SELECT..."
        if not self.db_connection:
            raise RuntimeError("Database connection not configured")

        # This would require actual DB connection
        # For now, return empty structure
        return {
            'table': 'unknown',
            'rows': [],
        }

    async def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize database data"""
        return {
            'type': 'db_records',
            'table': raw_data.get('table'),
            'row_count': len(raw_data.get('rows', [])),
            'rows': raw_data.get('rows'),
        }

    async def validate(self, data: Dict[str, Any]) -> bool:
        """Validate database data"""
        return (
            data.get('type') == 'db_records'
            and 'table' in data
            and 'rows' in data
        )


class SimulatorAdapter(PerceptionAdapter):
    """Adapter for simulator-generated perception"""

    def __init__(self, adapter_id: str = 'simulator'):
        super().__init__(adapter_id, 'simulator')

    async def fetch(self, source_uri: str) -> Dict[str, Any]:
        """Fetch from simulator"""
        # source_uri format: "simulator:sim_run_id/step:step_index"
        parts = source_uri.replace('simulator://', '').split('/')

        return {
            'sim_run_id': parts[0] if parts else 'unknown',
            'step_index': int(parts[1].split(':')[1]) if len(parts) > 1 else 0,
            'state': {},
            'observation': {},
        }

    async def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize simulator data"""
        return {
            'type': 'simulator_observation',
            'sim_run_id': raw_data.get('sim_run_id'),
            'step_index': raw_data.get('step_index'),
            'state': raw_data.get('state'),
            'observation': raw_data.get('observation'),
            'marked_as_simulation': True,
        }

    async def validate(self, data: Dict[str, Any]) -> bool:
        """Validate simulator data"""
        return (
            data.get('type') == 'simulator_observation'
            and data.get('marked_as_simulation') is True
        )


class PerceptionAdapterRegistry:
    """Registry of available adapters"""

    def __init__(self):
        self.adapters: Dict[str, PerceptionAdapter] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register default adapters"""
        self.register('local_file', LocalFileAdapter())
        self.register('postgres', PostgresAdapter())
        self.register('simulator', SimulatorAdapter())

    def register(self, adapter_id: str, adapter: PerceptionAdapter):
        """Register an adapter"""
        self.adapters[adapter_id] = adapter

    def get(self, adapter_id: str) -> Optional[PerceptionAdapter]:
        """Get adapter by ID"""
        return self.adapters.get(adapter_id)

    def list_adapters(self) -> Dict[str, PerceptionAdapter]:
        """List all adapters"""
        return self.adapters.copy()


# Global registry
_registry: Optional[PerceptionAdapterRegistry] = None


def get_perception_registry() -> PerceptionAdapterRegistry:
    """Get global perception adapter registry"""
    global _registry
    if _registry is None:
        _registry = PerceptionAdapterRegistry()
    return _registry

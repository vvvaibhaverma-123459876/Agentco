"""Constitution and law registry for civilizations."""

from .constitution_service import (
    create_constitution_version,
    activate_constitution_version,
    get_active_constitution,
    validate_constitution_rules,
    list_constitution_versions,
    REQUIRED_CONSTITUTION_RULES,
)
from .law_registry import (
    register_law,
    get_law,
    list_civilization_laws,
    list_society_laws,
    retire_law,
)

__all__ = [
    "create_constitution_version",
    "activate_constitution_version",
    "get_active_constitution",
    "validate_constitution_rules",
    "list_constitution_versions",
    "REQUIRED_CONSTITUTION_RULES",
    "register_law",
    "get_law",
    "list_civilization_laws",
    "list_society_laws",
    "retire_law",
]

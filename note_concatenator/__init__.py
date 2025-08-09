"""
Notes Concatenator v2.0

A modern file concatenation tool with clean architecture,
auto-discovery, and intelligent pattern matching.
"""

__version__ = "2.0.0"
__author__ = "Jorge"
__description__ = (
    "Modern file concatenation tool with auto-discovery and clean architecture"
)

# Public API exports
from .application.concatenate_project import ConcatenateProjectUseCase
from .domain.entities import (
    ConcatenationResult,
    FileInfo,
    Project,
    ProjectConfiguration,
    ProjectProfile,
)
from .infrastructure.config_loader import (
    ConfigurationError,
    YamlConfigLoader,
    load_project_configuration,
)

__all__ = [
    "ConcatenateProjectUseCase",
    "Project",
    "ProjectProfile",
    "ProjectConfiguration",
    "FileInfo",
    "ConcatenationResult",
    "load_project_configuration",
    "YamlConfigLoader",
    "ConfigurationError",
]

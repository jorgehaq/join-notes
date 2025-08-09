"""
Domain entities for the note concatenator v2.1.0.
Enhanced with granular exclusions and flexible output settings.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class FileInfo:
    """Represents information about a single file to be processed."""

    relative_path: str
    content: str
    name: str
    project_origin: str
    size_bytes: Optional[int] = None

    @property
    def extension(self) -> str:
        """Get file extension including the dot."""
        return Path(self.name).suffix.lower()

    @property
    def size_mb(self) -> float:
        """Get file size in megabytes."""
        if self.size_bytes is None:
            return 0.0
        size: int = self.size_bytes
        return float(size) / (1024 * 1024)


class OutputConfig(BaseModel):
    """Configuration for output directory settings."""

    output_local_directory: str = Field(default="JOINED-NOTES")
    output_external_directory: str = Field(default="")
    active: bool = Field(default=True)


class GlobalExcludeConfig(BaseModel):
    """Global exclusion patterns."""

    folders: List[str] = Field(
        default_factory=lambda: [".venv", "__pycache__/", "build/", "**/vendor/**"]
    )
    files: List[str] = Field(
        default_factory=lambda: ["**/*.min.js", "**/*.csv", "**/*.pyc"]
    )


class ProjectProfile(BaseModel):
    """Represents a specific view/profile of a project."""

    pattern: str = Field(..., description="Directory pattern to search")
    extensions: List[str] = Field(default_factory=lambda: [".py", ".md", ".yml"])
    output: str = Field(..., description="Output filename")
    description: str = Field(default="", description="Profile description")
    not_include: List[str] = Field(default_factory=list, description="Paths to exclude")

    def matches_extension(self, file_extension: str) -> bool:
        """Check if file extension matches this profile."""
        return file_extension.lower() in [ext.lower() for ext in self.extensions]


class Project(BaseModel):
    """Represents a project configuration with multiple profiles."""

    name: str = Field(..., description="Project name/identifier")
    description: str = Field(default="", description="Project description")
    profiles: dict[str, ProjectProfile] = Field(default_factory=dict)

    def get_profile(self, profile_name: str) -> Optional[ProjectProfile]:
        """Get a specific profile by name."""
        return self.profiles.get(profile_name)

    def get_default_profile(self) -> Optional[ProjectProfile]:
        """Get the first available profile as default."""
        if not self.profiles:
            return None
        return next(iter(self.profiles.values()))


class ProjectConfiguration(BaseModel):
    """Complete configuration containing all projects and global settings."""

    projects: dict[str, Project] = Field(default_factory=dict)
    settings: dict = Field(default_factory=dict)

    def get_project(self, project_name: str) -> Optional[Project]:
        """Get a project by name."""
        return self.projects.get(project_name)

    def list_project_names(self) -> List[str]:
        """Get list of all project names."""
        return list(self.projects.keys())

    @property
    def output_internal_config(self) -> OutputConfig:
        """Get internal output configuration."""
        internal = self.settings.get("output-internal", {})
        return OutputConfig(**internal)

    @property
    def output_external_config(self) -> OutputConfig:
        """Get external output configuration."""
        external = self.settings.get("output-external", {})
        return OutputConfig(**external)

    @property
    def active_output_config(self) -> OutputConfig:
        """Get the currently active output configuration."""
        internal = self.output_internal_config
        external = self.output_external_config

        if external.active:
            return external
        return internal

    @property
    def global_exclude_config(self) -> GlobalExcludeConfig:
        """Get global exclusion configuration."""
        exclude = self.settings.get("exclude", {})
        return GlobalExcludeConfig(**exclude)

    @property
    def max_file_size_mb(self) -> float:
        """Get maximum file size limit in MB."""
        return self.settings.get("max_file_size", 5.0)


class ConcatenationResult(BaseModel):
    """Result of a file concatenation operation."""

    project_name: str
    profile_name: str
    files_processed: List[FileInfo]
    output_file: Path
    total_files: int
    total_size_mb: float
    extensions_found: List[str]
    execution_time_seconds: float

    @property
    def success(self) -> bool:
        """Whether the concatenation was successful."""
        return self.total_files > 0 and self.output_file.exists()

    def get_summary(self) -> str:
        """Get a human-readable summary of the results."""
        return (
            f"Processed {self.total_files} files "
            f"({self.total_size_mb:.2f} MB) "
            f"in {self.execution_time_seconds:.2f}s"
        )

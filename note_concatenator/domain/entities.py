"""
Domain entities for the note concatenator.
These are the core business objects that represent our domain concepts.
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
        return self.size_bytes / (1024 * 1024)


class ProjectProfile(BaseModel):
    """Represents a specific view/profile of a project."""
    
    pattern: str = Field(..., description="Glob pattern to match directories")
    extensions: List[str] = Field(default_factory=lambda: [".py", ".md", ".yml"])
    output: str = Field(..., description="Output filename")
    description: str = Field(default="", description="Profile description")
    
    def matches_extension(self, file_extension: str) -> bool:
        """Check if file extension matches this profile."""
        return file_extension.lower() in [ext.lower() for ext in self.extensions]


class Project(BaseModel):
    """Represents a project configuration with multiple profiles."""
    
    name: str = Field(..., description="Project name/identifier")
    description: str = Field(default="", description="Project description")
    base_paths: List[str] = Field(..., description="Base directories to search")
    profiles: dict[str, ProjectProfile] = Field(default_factory=dict)
    
    def get_profile(self, profile_name: str) -> Optional[ProjectProfile]:
        """Get a specific profile by name."""
        return self.profiles.get(profile_name)
    
    def get_default_profile(self) -> Optional[ProjectProfile]:
        """Get the first available profile as default."""
        if not self.profiles:
            return None
        return next(iter(self.profiles.values()))
    
    @property
    def expanded_base_paths(self) -> List[Path]:
        """Get base paths with environment variables expanded."""
        expanded = []
        for path_str in self.base_paths:
            # Expand ~ and environment variables
            expanded_path = Path(path_str).expanduser()
            expanded.append(expanded_path)
        return expanded


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
    def default_extensions(self) -> List[str]:
        """Get default file extensions from settings."""
        return self.settings.get("default_extensions", [".py", ".md", ".yml"])
    
    @property
    def max_file_size_mb(self) -> float:
        """Get maximum file size limit in MB."""
        return self.settings.get("max_file_size", 5.0)
    
    @property
    def output_directory(self) -> str:
        """Get output directory for concatenated files."""
        return self.settings.get("output_directory", "JOINED-NOTES")


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
"""
Application use case for concatenating project files v2.1.0.
Enhanced with minimalist output format and improved performance.
"""

import time
from pathlib import Path
from typing import List, Optional

from ..domain.entities import (
    ConcatenationResult,
    FileInfo,
    Project,
    ProjectConfiguration,
    ProjectProfile,
)
from ..infrastructure.config_loader import load_project_configuration
from ..infrastructure.file_discovery import (
    EnhancedFileDiscoveryEngine,
    FastFileContentReader,
)


class ConcatenateProjectUseCase:
    """Enhanced use case with minimalist output and improved performance."""

    def __init__(
        self,
        config: Optional[ProjectConfiguration] = None,
        discovery_engine: Optional[EnhancedFileDiscoveryEngine] = None,
        content_reader: Optional[FastFileContentReader] = None,
    ):
        """Initialize with optional dependencies for testing."""
        self.config = config or load_project_configuration()
        self.discovery_engine = discovery_engine or EnhancedFileDiscoveryEngine(
            self.config
        )
        self.content_reader = content_reader or FastFileContentReader(
            max_file_size_mb=self.config.max_file_size_mb
        )

    def execute(
        self,
        project_name: str,
        profile_name: Optional[str] = None,
        output_file: Optional[Path] = None,
        extensions_override: Optional[List[str]] = None,
    ) -> ConcatenationResult:
        """Execute the concatenation use case with enhanced performance."""
        start_time = time.time()

        # Get project configuration
        project = self._get_project(project_name)
        profile = self._get_profile(project, profile_name)

        # Override extensions if provided
        if extensions_override:
            profile.extensions = extensions_override

        # Determine output file using active output config
        output_path = self._determine_output_path(project_name, profile, output_file)

        # Discover files
        discovered_files = self.discovery_engine.discover_files(project, profile)

        if not discovered_files:
            # Return empty result if no files found
            return ConcatenationResult(
                project_name=project_name,
                profile_name=profile_name or "default",
                files_processed=[],
                output_file=output_path,
                total_files=0,
                total_size_mb=0.0,
                extensions_found=[],
                execution_time_seconds=time.time() - start_time,
            )

        # Read file contents with parallel processing (v1 speed)
        base_path = Path(profile.pattern).expanduser()
        file_infos = self.content_reader.read_files_parallel(
            discovered_files,
            project_name,
            base_path,
            max_workers=self.config.settings.get("max_workers", 4),
        )

        # Generate minimalist output
        self._write_minimalist_output(file_infos, output_path, project, profile)

        # Calculate statistics
        total_size_mb = sum(info.size_mb for info in file_infos)
        extensions_found = list({info.extension for info in file_infos})

        return ConcatenationResult(
            project_name=project_name,
            profile_name=profile_name or "default",
            files_processed=file_infos,
            output_file=output_path,
            total_files=len(file_infos),
            total_size_mb=total_size_mb,
            extensions_found=extensions_found,
            execution_time_seconds=time.time() - start_time,
        )

    def _get_project(self, project_name: str) -> Project:
        """Get project configuration or raise error."""
        project = self.config.get_project(project_name)
        if not project:
            available = ", ".join(self.config.list_project_names())
            raise ValueError(
                f"Project '{project_name}' not found. "
                f"Available projects: {available}"
            )
        return project

    def _get_profile(
        self, project: Project, profile_name: Optional[str]
    ) -> ProjectProfile:
        """Get profile or use default."""
        if profile_name:
            profile = project.get_profile(profile_name)
            if not profile:
                available = ", ".join(project.profiles.keys())
                raise ValueError(
                    f"Profile '{profile_name}' not found in project '{project.name}'. "
                    f"Available profiles: {available}"
                )
            return profile

        # Use default profile
        default_profile = project.get_default_profile()
        if not default_profile:
            raise ValueError(f"No profiles defined for project '{project.name}'")

        return default_profile

    def _determine_output_path(
        self, project_name: str, profile: ProjectProfile, output_file: Optional[Path]
    ) -> Path:
        """Determine the final output file path using active output config."""
        if output_file:
            return output_file

        # Get active output configuration
        active_output = self.config.active_output_config

        if active_output.output_external_directory:
            output_dir = Path(active_output.output_external_directory) / project_name
        else:
            output_dir = Path(active_output.output_local_directory) / project_name

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Use profile output name
        filename = profile.output
        if not filename.endswith(".md"):
            filename += ".md"

        return output_dir / filename

    def _write_minimalist_output(
        self,
        file_infos: List[FileInfo],
        output_path: Path,
        project: Project,
        profile: ProjectProfile,
    ) -> None:
        """Write the minimalist concatenated output file."""
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                # Minimalist header
                f.write(f"# {project.name.upper()}\n\n")
                f.write(f"**Profile:** {profile.description or profile.output}\n")
                f.write(f"**Files:** {len(file_infos)}\n")
                f.write(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("=" * 60 + "\n\n")

                # Write each file with minimalist format
                for file_info in file_infos:
                    self._write_minimalist_file_section(f, file_info)

        except Exception as e:
            raise RuntimeError(f"Failed to write output file {output_path}: {e}") from e

    def _write_minimalist_file_section(self, file_handle, file_info: FileInfo) -> None:
        """Write a minimalist section for a single file."""
        # Minimalist separator
        file_handle.write("-" * 60 + "\n")
        file_handle.write(f"Path: {file_info.relative_path}\n\n")

        # Determine code block language from extension
        language = self._get_language_from_extension(file_info.extension)

        # Code block with language
        file_handle.write(f"```{language}\n")
        file_handle.write(file_info.content)
        if not file_info.content.endswith("\n"):
            file_handle.write("\n")
        file_handle.write("```\n\n")

    def _get_language_from_extension(self, extension: str) -> str:
        """Get syntax highlighting language from file extension."""
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "jsx",
            ".tsx": "tsx",
            ".java": "java",
            ".php": "php",
            ".sql": "sql",
            ".yml": "yaml",
            ".yaml": "yaml",
            ".json": "json",
            ".xml": "xml",
            ".html": "html",
            ".css": "css",
            ".sh": "bash",
            ".dockerfile": "dockerfile",
            ".md": "markdown",
            ".txt": "text",
            ".env": "bash",
        }

        return language_map.get(extension.lower(), "text")

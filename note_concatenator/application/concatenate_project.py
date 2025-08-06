
"""
Application use case for concatenating project files.
This is the main business logic that orchestrates the file discovery and concatenation process.
"""

import time
from pathlib import Path
from typing import List, Optional

from ..domain.entities import (
    Project, 
    ProjectProfile, 
    FileInfo, 
    ConcatenationResult,
    ProjectConfiguration
)
from ..infrastructure.file_discovery import FileDiscoveryEngine, FileContentReader
from ..infrastructure.config_loader import load_project_configuration


class ConcatenateProjectUseCase:
    """Use case for concatenating files from a project profile."""
    
    def __init__(
        self,
        config: Optional[ProjectConfiguration] = None,
        discovery_engine: Optional[FileDiscoveryEngine] = None,
        content_reader: Optional[FileContentReader] = None
    ):
        """Initialize with optional dependencies for testing."""
        self.config = config or load_project_configuration()
        self.discovery_engine = discovery_engine or FileDiscoveryEngine()
        self.content_reader = content_reader or FileContentReader(
            max_file_size_mb=self.config.max_file_size_mb
        )
    
    def execute(
        self,
        project_name: str,
        profile_name: Optional[str] = None,
        output_file: Optional[Path] = None,
        extensions_override: Optional[List[str]] = None
    ) -> ConcatenationResult:
        """Execute the concatenation use case."""
        start_time = time.time()
        
        # Get project configuration
        project = self._get_project(project_name)
        profile = self._get_profile(project, profile_name)
        
        # Override extensions if provided
        if extensions_override:
            profile.extensions = extensions_override
        
        # Determine output file
        output_path = self._determine_output_path(
            project_name, 
            profile, 
            output_file
        )
        
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
                execution_time_seconds=time.time() - start_time
            )
        
        # Read file contents
        file_infos = self.content_reader.read_files_parallel(
            discovered_files,
            project_name,
            project.expanded_base_paths,
            max_workers=self.config.settings.get("max_workers", 4)
        )
        
        # Generate output
        self._write_concatenated_output(
            file_infos,
            output_path,
            project,
            profile
        )
        
        # Calculate statistics
        total_size_mb = sum(info.size_mb for info in file_infos)
        extensions_found = list(set(info.extension for info in file_infos))
        
        return ConcatenationResult(
            project_name=project_name,
            profile_name=profile_name or "default",
            files_processed=file_infos,
            output_file=output_path,
            total_files=len(file_infos),
            total_size_mb=total_size_mb,
            extensions_found=extensions_found,
            execution_time_seconds=time.time() - start_time
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
        self, 
        project: Project, 
        profile_name: Optional[str]
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
        self,
        project_name: str,
        profile: ProjectProfile,
        output_file: Optional[Path]
    ) -> Path:
        """Determine the final output file path."""
        if output_file:
            return output_file
        
        # Create output directory
        output_dir = Path(self.config.output_directory) / project_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Use profile output name or generate default
        filename = profile.output or f"{project_name}_concatenated.md"
        if not filename.endswith('.md'):
            filename += '.md'
        
        return output_dir / filename
    
    def _write_concatenated_output(
        self,
        file_infos: List[FileInfo],
        output_path: Path,
        project: Project,
        profile: ProjectProfile
    ) -> None:
        """Write the concatenated output file."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                # Write header
                self._write_header(f, project, profile, file_infos)
                
                # Group files by directory for better organization
                files_by_dir = self._group_files_by_directory(file_infos)
                
                # Write content sections
                for directory, files in files_by_dir.items():
                    self._write_directory_section(f, directory, files)
                
        except Exception as e:
            raise RuntimeError(f"Failed to write output file {output_path}: {e}")
    
    def _write_header(
        self,
        file_handle,
        project: Project,
        profile: ProjectProfile,
        file_infos: List[FileInfo]
    ) -> None:
        """Write the file header with project information."""
        total_size_mb = sum(info.size_mb for info in file_infos)
        extensions = list(set(info.extension for info in file_infos))
        
        file_handle.write(f"# 📋 PROJECT: {project.name.upper()}\n\n")
        file_handle.write(f"**Description:** {project.description}\n")
        file_handle.write(f"**Profile:** {profile.description or 'Default'}\n")
        file_handle.write(f"**Files processed:** {len(file_infos)} files\n")
        file_handle.write(f"**Total size:** {total_size_mb:.2f} MB\n")
        file_handle.write(f"**Extensions:** {', '.join(sorted(extensions))}\n")
        file_handle.write(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        file_handle.write("=" * 80 + "\n\n")
    
    def _group_files_by_directory(self, file_infos: List[FileInfo]) -> dict:
        """Group files by their directory for organized output."""
        files_by_dir = {}
        
        for file_info in sorted(file_infos, key=lambda x: x.relative_path):
            directory = str(Path(file_info.relative_path).parent)
            if directory == '.':
                directory = 'root'
            
            if directory not in files_by_dir:
                files_by_dir[directory] = []
            
            files_by_dir[directory].append(file_info)
        
        return files_by_dir
    
    def _write_directory_section(
        self,
        file_handle,
        directory: str,
        files: List[FileInfo]
    ) -> None:
        """Write a section for files in a specific directory."""
        file_handle.write(f"\n## 📁 Directory: {directory}\n\n")
        
        for file_info in files:
            self._write_file_section(file_handle, file_info)
    
    def _write_file_section(self, file_handle, file_info: FileInfo) -> None:
        """Write a section for a single file."""
        file_handle.write(f"### 📄 {file_info.name}\n")
        file_handle.write(f"**Path:** `{file_info.relative_path}`\n")
        if file_info.size_bytes:
            file_handle.write(f"**Size:** {file_info.size_mb:.2f} MB\n")
        file_handle.write("\n")
        
        # Determine code block language from extension
        language = self._get_language_from_extension(file_info.extension)
        
        file_handle.write(f"```{language}\n")
        file_handle.write(file_info.content)
        if not file_info.content.endswith('\n'):
            file_handle.write('\n')
        file_handle.write("```\n\n")
        file_handle.write("-" * 60 + "\n\n")
    
    def _get_language_from_extension(self, extension: str) -> str:
        """Get syntax highlighting language from file extension."""
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'jsx',
            '.tsx': 'tsx',
            '.java': 'java',
            '.php': 'php',
            '.sql': 'sql',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.json': 'json',
            '.xml': 'xml',
            '.html': 'html',
            '.css': 'css',
            '.sh': 'bash',
            '.dockerfile': 'dockerfile',
            '.md': 'markdown',
            '.txt': 'text',
            '.env': 'bash'
        }
        
        return language_map.get(extension.lower(), 'text')
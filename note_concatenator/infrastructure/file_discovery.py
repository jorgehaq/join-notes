"""
File discovery infrastructure.
Handles finding files based on patterns and managing ignore rules.
"""

import glob
import os
from pathlib import Path
from typing import List, Set, Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..domain.entities import Project, ProjectProfile, FileInfo


class IgnorePatternEngine:
    """Handles .notes-ignore pattern matching using gitignore-style rules."""
    
    def __init__(self, ignore_file_path: Path = None):
        """Initialize with path to ignore file."""
        self.ignore_file_path = ignore_file_path or Path(".notes-ignore")
        self._patterns = self._load_ignore_patterns()
    
    def _load_ignore_patterns(self) -> List[str]:
        """Load ignore patterns from file."""
        patterns = []
        
        if not self.ignore_file_path.exists():
            return patterns
        
        try:
            with open(self.ignore_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        patterns.append(line)
        except Exception:
            # If we can't read ignore file, continue without it
            pass
        
        return patterns
    
    def should_ignore(self, file_path: Path, base_path: Path) -> bool:
        """Check if a file should be ignored based on patterns."""
        relative_path = file_path.relative_to(base_path)
        
        for pattern in self._patterns:
            if self._matches_pattern(relative_path, pattern):
                return True
        
        return False
    
    def _matches_pattern(self, file_path: Path, pattern: str) -> bool:
        """Check if file path matches a specific ignore pattern."""
        file_str = str(file_path).replace('\\', '/')  # Normalize path separators
        
        # Handle different pattern types
        if pattern.endswith('/'):
            # Directory pattern - check if any parent directory matches
            pattern_without_slash = pattern[:-1]
            return any(
                part == pattern_without_slash 
                for part in file_path.parts
            )
        
        elif '**' in pattern:
            # Glob pattern - use fnmatch-style matching
            import fnmatch
            return fnmatch.fnmatch(file_str, pattern)
        
        elif pattern.startswith('*'):
            # Simple wildcard
            import fnmatch
            return fnmatch.fnmatch(file_path.name, pattern)
        
        else:
            # Exact match or substring
            return pattern in file_str or file_path.name == pattern


class FileDiscoveryEngine:
    """Discovers files based on project configuration and patterns."""
    
    def __init__(self, ignore_engine: IgnorePatternEngine = None):
        """Initialize with optional custom ignore engine."""
        self.ignore_engine = ignore_engine or IgnorePatternEngine()
    
    def discover_files(
        self, 
        project: Project, 
        profile: ProjectProfile
    ) -> List[Path]:
        """Discover all files matching the project profile criteria."""
        discovered_files = []
        
        for base_path in project.expanded_base_paths:
            if not base_path.exists():
                continue
            
            # Find directories matching the pattern
            matching_dirs = self._find_matching_directories(base_path, profile.pattern)
            
            # Find files in those directories
            for directory in matching_dirs:
                files = self._find_files_in_directory(
                    directory, 
                    profile.extensions,
                    base_path
                )
                discovered_files.extend(files)
        
        return discovered_files
    
    def _find_matching_directories(self, base_path: Path, pattern: str) -> List[Path]:
        """Find directories matching the glob pattern."""
        search_pattern = str(base_path / pattern)
        
        try:
            # Use glob to find matching paths
            matches = glob.glob(search_pattern, recursive=True)
            
            # Filter to only directories that exist
            directories = [
                Path(match) for match in matches 
                if Path(match).is_dir()
            ]
            
            return directories
            
        except Exception:
            # If glob fails, return empty list
            return []
    
    def _find_files_in_directory(
        self, 
        directory: Path, 
        extensions: List[str],
        base_path: Path
    ) -> List[Path]:
        """Find files with specified extensions in a directory."""
        files = []
        
        try:
            for file_path in directory.rglob('*'):
                if not file_path.is_file():
                    continue
                
                # Check extension match
                if not self._matches_extension(file_path, extensions):
                    continue
                
                # Check ignore patterns
                if self.ignore_engine.should_ignore(file_path, base_path):
                    continue
                
                files.append(file_path)
                
        except Exception:
            # If directory traversal fails, skip it
            pass
        
        return files
    
    def _matches_extension(self, file_path: Path, extensions: List[str]) -> bool:
        """Check if file extension matches any in the list."""
        file_ext = file_path.suffix.lower()
        
        # Handle files without extensions
        if not file_ext and '' in extensions:
            return True
        
        # Handle special cases like .env files
        file_name = file_path.name.lower()
        
        return any(
            file_ext == ext.lower() or 
            file_name.startswith(ext.lower().lstrip('.'))
            for ext in extensions
        )


class FileContentReader:
    """Reads file content with proper encoding handling."""
    
    def __init__(self, max_file_size_mb: float = 5.0):
        """Initialize with maximum file size limit."""
        self.max_file_size_mb = max_file_size_mb
        self.max_file_size_bytes = int(max_file_size_mb * 1024 * 1024)
    
    def read_file(self, file_path: Path, project_name: str, base_path: Path) -> FileInfo:
        """Read a single file and return FileInfo."""
        try:
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size_bytes:
                content = f"[File too large: {file_size / (1024*1024):.1f}MB > {self.max_file_size_mb}MB limit]"
            else:
                content = self._read_file_content(file_path)
            
            relative_path = str(file_path.relative_to(base_path))
            
            return FileInfo(
                relative_path=relative_path,
                content=content,
                name=file_path.name,
                project_origin=project_name,
                size_bytes=file_size
            )
            
        except Exception as e:
            # Handle read errors gracefully
            relative_path = str(file_path.relative_to(base_path))
            return FileInfo(
                relative_path=relative_path,
                content=f"[Error reading file: {str(e)}]",
                name=file_path.name,
                project_origin=project_name,
                size_bytes=0
            )
    
    def _read_file_content(self, file_path: Path) -> str:
        """Read file content with encoding detection."""
        # Try common encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        
        # If all encodings fail, return error message
        return f"[Unable to decode file with common encodings]"
    
    def read_files_parallel(
        self, 
        file_paths: List[Path], 
        project_name: str,
        base_paths: List[Path],
        max_workers: int = 4
    ) -> List[FileInfo]:
        """Read multiple files in parallel."""
        file_infos = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all file reading tasks
            future_to_file = {}
            
            for file_path in file_paths:
                # Find the appropriate base path for this file
                base_path = self._find_base_path_for_file(file_path, base_paths)
                
                future = executor.submit(
                    self.read_file, 
                    file_path, 
                    project_name, 
                    base_path
                )
                future_to_file[future] = file_path
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                try:
                    file_info = future.result()
                    file_infos.append(file_info)
                except Exception as e:
                    # Log error but continue with other files
                    file_path = future_to_file[future]
                    print(f"Error reading {file_path}: {e}")
        
        return file_infos
    
    def _find_base_path_for_file(self, file_path: Path, base_paths: List[Path]) -> Path:
        """Find which base path contains this file."""
        for base_path in base_paths:
            try:
                file_path.relative_to(base_path)
                return base_path
            except ValueError:
                continue
        
        # If no base path found, use the file's parent
        return file_path.parent
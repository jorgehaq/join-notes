"""
File discovery infrastructure v2.1.0.
Enhanced with granular exclusions, pattern-based search, and improved performance.
"""

import glob
import os
from pathlib import Path
from typing import List, Set, Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..domain.entities import Project, ProjectProfile, FileInfo, ProjectConfiguration


class EnhancedIgnorePatternEngine:
    """Enhanced ignore pattern engine with global + profile-specific exclusions."""
    
    def __init__(self, config: ProjectConfiguration, profile: ProjectProfile):
        """Initialize with global config and profile-specific exclusions."""
        self.global_exclude = config.global_exclude_config
        self.profile_excludes = [Path(p).expanduser() for p in profile.not_include]
        
    def should_ignore(self, file_path: Path, base_path: Path) -> bool:
        """Check if a file should be ignored based on all exclusion rules."""
        relative_path = file_path.relative_to(base_path)
        
        # Check global folder exclusions
        if self._matches_global_folder_patterns(relative_path):
            return True
        
        # Check global file exclusions  
        if self._matches_global_file_patterns(relative_path):
            return True
            
        # Check profile-specific exclusions
        if self._matches_profile_exclusions(file_path):
            return True
        
        return False
    
    def _matches_global_folder_patterns(self, relative_path: Path) -> bool:
        """Check if path matches global folder exclusion patterns."""
        path_str = str(relative_path).replace('\\', '/')
        
        for pattern in self.global_exclude.folders:
            if self._matches_pattern(path_str, pattern):
                return True
                
        return False
    
    def _matches_global_file_patterns(self, relative_path: Path) -> bool:
        """Check if file matches global file exclusion patterns."""
        path_str = str(relative_path).replace('\\', '/')
        
        for pattern in self.global_exclude.files:
            if self._matches_pattern(path_str, pattern):
                return True
                
        return False
    
    def _matches_profile_exclusions(self, file_path: Path) -> bool:
        """Check if file matches profile-specific exclusions."""
        for exclude_path in self.profile_excludes:
            try:
                # Check if file is under excluded path
                file_path.relative_to(exclude_path)
                return True
            except ValueError:
                # File is not under this excluded path
                continue
        
        return False
    
    def _matches_pattern(self, path_str: str, pattern: str) -> bool:
        """Check if path matches a specific pattern (glob-style)."""
        import fnmatch
        
        if pattern.endswith('/'):
            # Directory pattern
            pattern_clean = pattern[:-1]
            return any(
                part == pattern_clean or fnmatch.fnmatch(part, pattern_clean)
                for part in path_str.split('/')
            )
        
        elif '**' in pattern:
            # Recursive glob pattern
            return fnmatch.fnmatch(path_str, pattern)
        
        elif '*' in pattern:
            # Simple wildcard
            return fnmatch.fnmatch(os.path.basename(path_str), pattern)
        
        else:
            # Exact match or substring
            return pattern in path_str


class EnhancedFileDiscoveryEngine:
    """Enhanced file discovery with pattern-based search and exclusions."""
    
    def __init__(self, config: ProjectConfiguration):
        """Initialize with project configuration."""
        self.config = config
    
    def discover_files(self, project: Project, profile: ProjectProfile) -> List[Path]:
        """Discover all files matching the project profile criteria."""
        # Initialize ignore engine for this profile
        ignore_engine = EnhancedIgnorePatternEngine(self.config, profile)
        
        # Expand pattern path
        pattern_path = Path(profile.pattern).expanduser()
        
        if not pattern_path.exists():
            return []
        
        discovered_files = []
        
        # Search for files in the pattern directory
        if pattern_path.is_dir():
            files = self._find_files_in_directory(
                pattern_path, 
                profile.extensions, 
                ignore_engine,
                pattern_path  # Use pattern_path as base for relative calculations
            )
            discovered_files.extend(files)
        
        return discovered_files
    
    def _find_files_in_directory(
        self, 
        directory: Path, 
        extensions: List[str],
        ignore_engine: EnhancedIgnorePatternEngine,
        base_path: Path
    ) -> List[Path]:
        """Find files with specified extensions in a directory."""
        files = []
        
        try:
            print(f"🔍 Scanning {directory} for extensions: {extensions}")
            
            for file_path in directory.rglob('*'):
                if not file_path.is_file():
                    continue
                
                # Debug: Print file being checked
                if file_path.name == "README.md":
                    print(f"🧪 Checking README.md - Extension: {file_path.suffix}")
                
                # Check extension match
                if not self._matches_extension(file_path, extensions):
                    if file_path.name == "README.md":
                        print(f"❌ README.md rejected by extension match")
                    continue
                
                # Check ignore patterns
                if ignore_engine.should_ignore(file_path, base_path):
                    if file_path.name == "README.md":
                        print(f"❌ README.md rejected by ignore patterns")
                    continue
                
                if file_path.name == "README.md":
                    print(f"✅ README.md accepted!")
                
                files.append(file_path)
                
        except Exception as e:
            print(f"Warning: Error scanning directory {directory}: {e}")
        
        print(f"📊 Found {len(files)} files total")
        return files
    
    def _matches_extension(self, file_path: Path, extensions: List[str]) -> bool:
        """Check if file extension matches any in the list."""
        file_ext = file_path.suffix.lower()
        file_name = file_path.name.lower()
        
        # Handle files without extensions
        if not file_ext and '' in extensions:
            return True
        
        # Direct extension match (most common case)
        for ext in extensions:
            ext_lower = ext.lower()
            if file_ext == ext_lower:
                return True
            
            # Handle special cases like .env files
            if ext_lower.startswith('.') and file_name.startswith(ext_lower.lstrip('.')):
                return True
        
        return False


class FastFileContentReader:
    """Enhanced file content reader with ThreadPoolExecutor from v1."""
    
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
            relative_path = str(file_path.relative_to(base_path)) if base_path else str(file_path)
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
        base_path: Path,
        max_workers: int = 4
    ) -> List[FileInfo]:
        """Read multiple files in parallel using ThreadPoolExecutor (v1 speed)."""
        file_infos = []
        
        if not file_paths:
            return file_infos
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all file reading tasks
            future_to_file = {}
            
            for file_path in file_paths:
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
        
        # Sort by relative path for consistent output
        return sorted(file_infos, key=lambda x: x.relative_path)
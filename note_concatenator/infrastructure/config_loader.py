"""
Configuration loading infrastructure v2.1.0.
Enhanced with new YAML structure, output settings, and granular exclusions.
"""

import yaml
from pathlib import Path
from typing import Optional, List

from ..domain.entities import (
    ProjectConfiguration, 
    Project, 
    ProjectProfile,
    OutputConfig,
    GlobalExcludeConfig
)


class ConfigurationError(Exception):
    """Raised when there's an error loading or parsing configuration."""
    pass


class YamlConfigLoader:
    """Loads project configuration from YAML files with v2.1.0 structure."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize with optional custom config path."""
        self.config_path = config_path or Path("config/projects.yml")
    
    def load_configuration(self) -> ProjectConfiguration:
        """Load and parse the complete project configuration."""
        if not self.config_path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {self.config_path}"
            )
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                raw_config = yaml.safe_load(file)
            
            return self._parse_configuration(raw_config)
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML syntax: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading configuration: {e}")
    
    def _parse_configuration(self, raw_config: dict) -> ProjectConfiguration:
        """Parse raw configuration dictionary into domain objects."""
        projects = {}
        
        # Parse projects section
        projects_config = raw_config.get("projects", {})
        for project_name, project_data in projects_config.items():
            projects[project_name] = self._parse_project(project_name, project_data)
        
        # Parse settings (now includes output configs and exclusions)
        settings = raw_config.get("settings", {})
        
        return ProjectConfiguration(
            projects=projects,
            settings=settings
        )
    
    def _parse_project(self, name: str, project_data: dict) -> Project:
        """Parse a single project configuration."""
        # Parse profiles with new structure
        profiles = {}
        profiles_data = project_data.get("profiles", {})
        
        for profile_name, profile_data in profiles_data.items():
            profiles[profile_name] = self._parse_profile(profile_data)
        
        return Project(
            name=name,
            description=project_data.get("description", ""),
            profiles=profiles
        )
    
    def _parse_profile(self, profile_data: dict) -> ProjectProfile:
        """Parse a single profile with enhanced structure."""
        return ProjectProfile(
            pattern=profile_data.get("pattern", ""),
            extensions=profile_data.get("extensions", [".py", ".md", ".yml"]),
            output=profile_data.get("output", ""),
            description=profile_data.get("description", ""),
            not_include=profile_data.get("not-include", [])
        )


class ConfigurationValidator:
    """Validates project configuration for common issues."""
    
    def validate_configuration(self, config: ProjectConfiguration) -> List[str]:
        """Validate configuration and return list of issues found."""
        issues = []
        
        if not config.projects:
            issues.append("No projects defined in configuration")
        
        # Validate output configuration
        issues.extend(self._validate_output_config(config))
        
        # Validate projects
        for project_name, project in config.projects.items():
            issues.extend(self._validate_project(project_name, project))
        
        return issues
    
    def _validate_output_config(self, config: ProjectConfiguration) -> List[str]:
        """Validate output configuration."""
        issues = []
        
        internal = config.output_internal_config
        external = config.output_external_config
        
        # Check that at least one output is active
        if not internal.active and not external.active:
            issues.append("No output configuration is active")
        
        # Check external directory exists if active
        if external.active and external.output_external_directory:
            ext_path = Path(external.output_external_directory).expanduser()
            if not ext_path.exists():
                issues.append(f"External output directory does not exist: {ext_path}")
        
        return issues
    
    def _validate_project(self, name: str, project: Project) -> List[str]:
        """Validate a single project configuration."""
        issues = []
        
        # Check profiles are not empty
        if not project.profiles:
            issues.append(f"Project '{name}': No profiles defined")
        
        # Validate each profile
        for profile_name, profile in project.profiles.items():
            issues.extend(self._validate_profile(name, profile_name, profile))
        
        return issues
    
    def _validate_profile(self, project_name: str, profile_name: str, profile: ProjectProfile) -> List[str]:
        """Validate a single profile configuration."""
        issues = []
        
        if not profile.pattern:
            issues.append(f"Project '{project_name}', profile '{profile_name}': Empty pattern")
        
        if not profile.extensions:
            issues.append(f"Project '{project_name}', profile '{profile_name}': No extensions defined")
        
        if not profile.output:
            issues.append(f"Project '{project_name}', profile '{profile_name}': No output filename defined")
        
        # Validate pattern paths exist (more robust checking)
        issues.extend(self._validate_pattern_path(project_name, profile_name, profile.pattern))
        
        # Validate not-include paths
        for exclude_path in profile.not_include:
            issues.extend(self._validate_exclude_path(project_name, profile_name, exclude_path))
        
        return issues
    
    def _validate_pattern_path(self, project_name: str, profile_name: str, pattern: str) -> List[str]:
        """Validate pattern path with proper error handling."""
        issues = []
        
        try:
            # Skip glob patterns
            if '**' in pattern or '*' in pattern:
                return issues
            
            # Expand and check path
            pattern_path = Path(pattern).expanduser()
            if not pattern_path.exists():
                issues.append(
                    f"Project '{project_name}', profile '{profile_name}': "
                    f"Pattern path does not exist: {pattern_path}"
                )
            elif not pattern_path.is_dir():
                issues.append(
                    f"Project '{project_name}', profile '{profile_name}': "
                    f"Pattern path is not a directory: {pattern_path}"
                )
                
        except Exception as e:
            issues.append(
                f"Project '{project_name}', profile '{profile_name}': "
                f"Invalid pattern path '{pattern}': {e}"
            )
        
        return issues
    
    def _validate_exclude_path(self, project_name: str, profile_name: str, exclude_path: str) -> List[str]:
        """Validate exclusion path with proper error handling."""
        issues = []
        
        try:
            # Skip glob patterns
            if '**' in exclude_path or '*' in exclude_path:
                return issues
            
            # Expand and check path
            exclude_path_obj = Path(exclude_path).expanduser()
            if not exclude_path_obj.exists():
                issues.append(
                    f"Project '{project_name}', profile '{profile_name}': "
                    f"Exclusion path does not exist: {exclude_path_obj}"
                )
                
        except Exception as e:
            issues.append(
                f"Project '{project_name}', profile '{profile_name}': "
                f"Invalid exclusion path '{exclude_path}': {e}"
            )
        
        return issues


def load_project_configuration(config_path: Optional[Path] = None) -> ProjectConfiguration:
    """Convenience function to load and validate configuration."""
    loader = YamlConfigLoader(config_path)
    config = loader.load_configuration()
    
    # Validate configuration
    validator = ConfigurationValidator()
    issues = validator.validate_configuration(config)
    
    if issues:
        raise ConfigurationError(
            "Configuration validation failed:\n" + "\n".join(f"- {issue}" for issue in issues)
        )
    
    return config


def load_project_configuration_safe(config_path: Optional[Path] = None) -> Optional[ProjectConfiguration]:
    """Safe configuration loading for CLI - returns None on error and prints clean message."""
    try:
        return load_project_configuration(config_path)
    except ConfigurationError as e:
        print(f"❌ Configuration Error:")
        print(str(e))
        return None
    except FileNotFoundError:
        print(f"❌ Configuration file not found: {config_path or 'config/projects.yml'}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error loading configuration: {e}")
        return None
    """Convenience function to load and validate configuration."""
    loader = YamlConfigLoader(config_path)
    config = loader.load_configuration()
    
    # Validate configuration
    validator = ConfigurationValidator()
    issues = validator.validate_configuration(config)
    
    if issues:
        raise ConfigurationError(
            "Configuration validation failed:\n" + "\n".join(f"- {issue}" for issue in issues)
        )
    
    return config
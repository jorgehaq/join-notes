
"""
Configuration loading infrastructure.
Handles loading and parsing of YAML configuration files.
"""

import yaml
from pathlib import Path
from typing import Optional

from ..domain.entities import ProjectConfiguration, Project, ProjectProfile


class ConfigurationError(Exception):
    """Raised when there's an error loading or parsing configuration."""
    pass


class YamlConfigLoader:
    """Loads project configuration from YAML files."""
    
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
        
        # Parse global settings
        settings = raw_config.get("settings", {})
        
        return ProjectConfiguration(
            projects=projects,
            settings=settings
        )
    
    def _parse_project(self, name: str, project_data: dict) -> Project:
        """Parse a single project configuration."""
        # Parse profiles
        profiles = {}
        profiles_data = project_data.get("profiles", {})
        
        for profile_name, profile_data in profiles_data.items():
            profiles[profile_name] = ProjectProfile(**profile_data)
        
        return Project(
            name=name,
            description=project_data.get("description", ""),
            base_paths=project_data.get("base_paths", []),
            profiles=profiles
        )


class ConfigurationValidator:
    """Validates project configuration for common issues."""
    
    def validate_configuration(self, config: ProjectConfiguration) -> List[str]:
        """Validate configuration and return list of issues found."""
        issues = []
        
        if not config.projects:
            issues.append("No projects defined in configuration")
        
        for project_name, project in config.projects.items():
            issues.extend(self._validate_project(project_name, project))
        
        return issues
    
    def _validate_project(self, name: str, project: Project) -> List[str]:
        """Validate a single project configuration."""
        issues = []
        
        # Check base paths exist
        for base_path in project.expanded_base_paths:
            if not base_path.exists():
                issues.append(f"Project '{name}': Base path does not exist: {base_path}")
        
        # Check profiles are not empty
        if not project.profiles:
            issues.append(f"Project '{name}': No profiles defined")
        
        # Validate each profile
        for profile_name, profile in project.profiles.items():
            if not profile.pattern:
                issues.append(
                    f"Project '{name}', profile '{profile_name}': Empty pattern"
                )
            
            if not profile.extensions:
                issues.append(
                    f"Project '{name}', profile '{profile_name}': No extensions defined"
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
            f"Configuration validation failed:\n" + "\n".join(f"- {issue}" for issue in issues)
        )
    
    return config
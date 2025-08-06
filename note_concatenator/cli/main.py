"""
Modern CLI interface for the note concatenator v2.1.0.
Enhanced with clean error handling and safe configuration loading.
"""

import sys
from pathlib import Path
from typing import Optional, List

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from ..application.concatenate_project import ConcatenateProjectUseCase
from ..infrastructure.config_loader import load_project_configuration, ConfigurationError
from ..domain.entities import ProjectConfiguration


# Global console for rich output
console = Console()


def _load_configuration_safe(config_path: Optional[Path] = None) -> Optional[ProjectConfiguration]:
    """Load configuration with clean error messages for CLI."""
    try:
        return load_project_configuration(config_path)
        
    except ConfigurationError as e:
        console.print(f"[red]❌ Configuration Error:[/red]")
        # Clean up the error message - remove "Configuration validation failed:"
        error_msg = str(e).replace("Configuration validation failed:\n", "")
        console.print(error_msg)
        return None
        
    except FileNotFoundError:
        config_file = config_path or Path("config/projects.yml")
        console.print(f"[red]❌ Configuration file not found:[/red] {config_file}")
        console.print("[yellow]💡 Create config/projects.yml or use --config option[/yellow]")
        return None
        
    except Exception as e:
        console.print(f"[red]❌ Unexpected error:[/red] {e}")
        return None


def safe_load_or_exit(config_path: Optional[Path] = None) -> ProjectConfiguration:
    """Load configuration or exit with clean error."""
    config = _load_configuration_safe(config_path)
    if config is None:
        sys.exit(1)
    return config


@click.group(invoke_without_command=True)
@click.option('--config', '-c', 
              type=click.Path(exists=True, path_type=Path),
              help='Path to configuration file (default: config/projects.yml)')
@click.option('--verbose', '-v', is_flag=True, 
              help='Enable verbose output')
@click.pass_context
def cli(ctx, config: Optional[Path], verbose: bool):
    """
    Notes Concatenator v2.1.0 - Enhanced file aggregation tool.
    
    Concatenate files from configured projects with granular exclusions,
    flexible output settings, and clean minimalist format.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Store global options
    ctx.obj['config_path'] = config
    ctx.obj['verbose'] = verbose
    
    # If no subcommand is provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command('list')
@click.pass_context
def list_projects(ctx):
    """List all available projects and their profiles."""
    config = safe_load_or_exit(ctx.obj.get('config_path'))
    _display_projects_table(config)


@cli.command('concat')
@click.argument('project_name')
@click.option('--profile', '-p', 
              help='Specific profile to concatenate (default: first available)')
@click.option('--output', '-o', 
              type=click.Path(path_type=Path),
              help='Custom output file path')
@click.option('--extensions', '-e', 
              multiple=True,
              help='File extensions to include (overrides profile settings)')
@click.option('--all-profiles', is_flag=True,
              help='Concatenate all profiles for the project')
@click.option('--dry-run', is_flag=True,
              help='Show what would be processed without actually doing it')
@click.pass_context
def concatenate_project(
    ctx, 
    project_name: str, 
    profile: Optional[str],
    output: Optional[Path],
    extensions: tuple,
    all_profiles: bool,
    dry_run: bool
):
    """Concatenate files from a specific project."""
    verbose = ctx.obj.get('verbose', False)
    
    try:
        # Load configuration
        config = safe_load_or_exit(ctx.obj.get('config_path'))
        
        # Validate project exists
        if project_name not in config.projects:
            available = ", ".join(config.list_project_names())
            console.print(f"[red]Error:[/red] Project '{project_name}' not found.")
            console.print(f"Available projects: {available}")
            sys.exit(1)
        
        # Convert extensions tuple to list
        extensions_list = list(extensions) if extensions else None
        
        if all_profiles:
            _concatenate_all_profiles(
                config, project_name, extensions_list, dry_run, verbose
            )
        else:
            _concatenate_single_profile(
                config, project_name, profile, output, extensions_list, dry_run, verbose
            )
            
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            console.print_exception()
        sys.exit(1)


@cli.command('validate')
@click.pass_context
def validate_config(ctx):
    """Validate the project configuration file."""
    config = safe_load_or_exit(ctx.obj.get('config_path'))
    console.print("[green]✓[/green] Configuration is valid!")
    
    # Show summary
    project_count = len(config.projects)
    total_profiles = sum(len(p.profiles) for p in config.projects.values())
    
    console.print(f"Found {project_count} projects with {total_profiles} total profiles")


@cli.command('info')
@click.argument('project_name')
@click.pass_context
def project_info(ctx, project_name: str):
    """Show detailed information about a specific project."""
    config = safe_load_or_exit(ctx.obj.get('config_path'))
    project = config.get_project(project_name)
    
    if not project:
        available = ", ".join(config.list_project_names())
        console.print(f"[red]Error:[/red] Project '{project_name}' not found.")
        console.print(f"Available projects: {available}")
        sys.exit(1)
    
    _display_project_info(project)


def _display_projects_table(config: ProjectConfiguration):
    """Display a formatted table of all projects."""
    table = Table(title="Available Projects", show_header=True, header_style="bold magenta")
    
    table.add_column("Project", style="cyan", no_wrap=True)
    table.add_column("Description", style="green")
    table.add_column("Profiles", style="yellow")
    
    for project_name, project in config.projects.items():
        profiles = ", ".join(project.profiles.keys()) if project.profiles else "None"
        
        table.add_row(
            project_name,
            project.description or "No description",
            profiles
        )
    
    console.print(table)


def _display_project_info(project):
    """Display detailed information about a specific project."""
    console.print(f"\n[bold cyan]Project: {project.name}[/bold cyan]")
    console.print(f"Description: {project.description or 'No description'}")
    
    if project.profiles:
        console.print(f"\n[bold]Profiles:[/bold]")
        for profile_name, profile in project.profiles.items():
            console.print(f"  [yellow]{profile_name}[/yellow]")
            console.print(f"    Pattern: {profile.pattern}")
            console.print(f"    Extensions: {', '.join(profile.extensions)}")
            console.print(f"    Output: {profile.output}")
            if profile.description:
                console.print(f"    Description: {profile.description}")
            if profile.not_include:
                console.print(f"    Excludes: {len(profile.not_include)} paths")
            console.print()


def _concatenate_single_profile(
    config: ProjectConfiguration,
    project_name: str,
    profile_name: Optional[str],
    output_path: Optional[Path],
    extensions: Optional[List[str]],
    dry_run: bool,
    verbose: bool
):
    """Concatenate a single profile from a project."""
    use_case = ConcatenateProjectUseCase(config)
    
    if dry_run:
        console.print(f"[yellow]DRY RUN:[/yellow] Would concatenate project '{project_name}'")
        if profile_name:
            console.print(f"Profile: {profile_name}")
        if extensions:
            console.print(f"Extensions: {', '.join(extensions)}")
        if output_path:
            console.print(f"Output: {output_path}")
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task("Discovering and processing files...", total=None)
        
        result = use_case.execute(
            project_name=project_name,
            profile_name=profile_name,
            output_file=output_path,
            extensions_override=extensions
        )
    
    if result.success:
        console.print(f"[green]✓[/green] Successfully concatenated {result.total_files} files")
        console.print(f"Output: {result.output_file}")
        console.print(f"Size: {result.total_size_mb:.2f} MB")
        console.print(f"Time: {result.execution_time_seconds:.2f}s")
        
        if verbose:
            console.print(f"Extensions found: {', '.join(result.extensions_found)}")
    else:
        console.print("[yellow]Warning:[/yellow] No files found matching criteria")


def _concatenate_all_profiles(
    config: ProjectConfiguration,
    project_name: str,
    extensions: Optional[List[str]],
    dry_run: bool,
    verbose: bool
):
    """Concatenate all profiles for a project."""
    project = config.get_project(project_name)
    
    if not project.profiles:
        console.print(f"[yellow]Warning:[/yellow] No profiles defined for project '{project_name}'")
        return
    
    console.print(f"Processing all profiles for project '{project_name}':")
    
    use_case = ConcatenateProjectUseCase(config)
    
    for profile_name in project.profiles.keys():
        if dry_run:
            console.print(f"[yellow]DRY RUN:[/yellow] Would process profile '{profile_name}'")
            continue
        
        console.print(f"\n[cyan]Processing profile:[/cyan] {profile_name}")
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn(f"[progress.description]{{task.description}}"),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task(f"Processing {profile_name}...", total=None)
                
                result = use_case.execute(
                    project_name=project_name,
                    profile_name=profile_name,
                    extensions_override=extensions
                )
            
            if result.success:
                console.print(f"  ✓ {result.total_files} files → {result.output_file.name}")
            else:
                console.print(f"  [yellow]No files found for profile '{profile_name}'[/yellow]")
                
        except Exception as e:
            console.print(f"  [red]Error in profile '{profile_name}':[/red] {e}")
            if verbose:
                console.print_exception()


# Entry point for the CLI
def main():
    """Main entry point for the CLI application."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        console.print("\n[yellow]💡 Try:[/yellow]")
        console.print("  - Check your config/projects.yml file")
        console.print("  - Run: python migrate.py validate")
        console.print("  - Use --verbose for more details")
        sys.exit(1)


if __name__ == '__main__':
    main()
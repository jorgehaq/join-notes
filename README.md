# 📋 Notes Concatenator v2.0

Modern file concatenation tool with auto-discovery, clean architecture, and intelligent pattern matching.

## 🚀 Quick Start

```bash
# Install in development mode
pip install -e .

# List available projects
notes-concat --list

# Concatenate a project
notes-concat my-project

# Custom output name
notes-concat api-platform --output "backend-analysis.md"

# Specific extensions only
notes-concat enterprise --extensions py md yml
```

## 📁 Project Structure

```
notes-concatenator/
├── note_concatenator/          # Main package
│   ├── domain/                 # Business logic
│   ├── infrastructure/         # File I/O, configs
│   ├── application/           # Use cases
│   └── cli/                   # Command interface
├── config/
│   └── projects.yml           # Project configurations
├── .notes-ignore              # Global ignore patterns
└── pyproject.toml            # Dependencies & metadata
```

## ⚙️ Configuration

### Configure Projects (`config/projects.yml`)

```yaml
projects:
  
  api-platform:
    description: "FastAPI backend analysis"
    base_paths:
      - "/home/user/projects/backend"
      - "/home/user/notes/api-docs"
    
    profiles:
      current:
        pattern: "**/fastapi-project/**"
        extensions: [".py", ".md", ".yml"]
        output: "fastapi-analysis.md"
      
      infrastructure:
        pattern: "**/docker/**"
        extensions: [".dockerfile", ".yml", ".sh"]
        output: "infrastructure.md"

  enterprise-analysis:
    description: "Enterprise codebase review"
    base_paths:
      - "/home/user/work/projects"
    
    profiles:
      backend:
        pattern: "**/backend/**"
        extensions: [".py", ".sql"]
        output: "backend-analysis.md"
      
      frontend:
        pattern: "**/frontend/**"
        extensions: [".js", ".ts", ".jsx"]
        output: "frontend-analysis.md"
```

### Ignore Patterns (`.notes-ignore`)

Uses gitignore-style patterns:

```
# Global ignores
.venv/
__pycache__/
node_modules/

# Project-specific
**/legacy/**
**/deprecated/**
**/*.min.js
```

## 📋 Usage Examples

### Basic Commands

```bash
# List all configured projects
notes-concat --list

# Concatenate default profile
notes-concat api-platform

# Concatenate specific profile
notes-concat enterprise-analysis --profile backend

# All profiles for a project
notes-concat enterprise-analysis --all-profiles
```

### Advanced Options

```bash
# Custom extensions
notes-concat my-project --extensions py md txt yml

# Custom output location
notes-concat api-platform --output "/tmp/analysis.md"

# Verbose output
notes-concat my-project --verbose

# Dry run (show what would be processed)
notes-concat my-project --dry-run
```

## 🎯 Key Features

- **🔍 Auto-discovery**: Finds files using glob patterns, no manual path management
- **📁 Multi-profile**: Different views of the same project (backend, frontend, docs)
- **⚡ Parallel processing**: Fast file reading with threading
- **🎨 Rich output**: Beautiful CLI with progress bars and colored output
- **🚫 Smart ignoring**: Powerful pattern-based file exclusion
- **🏗️ Clean architecture**: Testable, maintainable, extensible code

## 🛠️ Development

### Setup Development Environment

```bash
# Clone and setup
git clone https://github.com/jorgehaq/notes-concatenator.git
cd notes-concatenator

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install with dev dependencies
pip install -e ".[dev]"
```

### Run Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=note_concatenator

# Specific test file
pytest tests/test_domain.py
```

### Code Quality

```bash
# Format code
black note_concatenator/

# Lint
ruff check note_concatenator/

# Type checking
mypy note_concatenator/
```

## 📊 Output Format

Generated markdown includes:

- **Project header** with metadata
- **File tree** showing discovered structure  
- **Content sections** organized by directory
- **Statistics** (file count, extensions, size)

Example output structure:
```markdown
# 📋 PROJECT: API-PLATFORM

**Description:** FastAPI backend analysis
**Files processed:** 42 files
**Extensions:** .py, .md, .yml

## 📁 src/api/
### 📄 main.py
**Path:** `src/api/main.py`
```python
# File content here
```
```

## 🔧 Configuration Tips

### Project Organization

1. **Group by purpose**: `api-platform`, `data-analysis`, `infrastructure`
2. **Use profiles**: Different views (backend, frontend, docs, tests)
3. **Smart patterns**: `**/src/**` instead of hardcoded paths
4. **Base paths**: Point to project roots, let patterns do the work

### Performance

- Use specific patterns to avoid scanning large directories
- Leverage `.notes-ignore` for global exclusions
- Consider file size limits for large datasets

## 📈 Migration from v1.0

```bash
# Your old JSON config
projects.json → config/projects.yml

# Your old script
concat-notes.py → notes-concat (CLI command)

# Your old structure
monolithic → clean architecture
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes with tests
4. Run quality checks: `black`, `ruff`, `mypy`, `pytest`
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙋 Support

- **Issues**: [GitHub Issues](https://github.com/jorgehaq/notes-concatenator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/jorgehaq/notes-concatenator/discussions)
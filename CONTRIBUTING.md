# Contributing to WriteBot

Thank you for your interest in contributing to WriteBot! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone. We expect all contributors to:

- Be respectful and considerate in communication
- Welcome newcomers and help them get started
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/WriteBot.git
   cd WriteBot
   ```
3. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Set up your development environment** (see below)

## How to Contribute

There are many ways to contribute to WriteBot:

### Code Contributions
- Fix bugs or implement new features
- Improve performance or refactor code
- Add tests or improve test coverage
- Update dependencies

### Documentation
- Improve existing documentation
- Add examples and tutorials
- Fix typos or clarify instructions
- Translate documentation

### Design
- Improve UI/UX of the web interface
- Create graphics or icons
- Suggest design improvements

### Testing
- Report bugs with detailed reproduction steps
- Test new features and provide feedback
- Add test cases

## Development Setup

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Git
- A code editor (VS Code, PyCharm, etc.)

### Installation Steps

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Install development dependencies**:
   ```bash
   pip install -r docs/requirements.txt  # For documentation
   ```

3. **Initialize the database**:
   ```bash
   python init_db.py
   ```

4. **Run the application**:
   ```bash
   python webapp/app.py
   ```

5. **Verify everything works**:
   - Open `http://localhost:5000` in your browser
   - Log in with the admin credentials you created
   - Try generating a simple handwriting sample

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with some modifications:

- **Line length**: Maximum 100 characters (not 79)
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Prefer double quotes for strings
- **Imports**: Organized in groups (standard library, third-party, local)

### Code Organization

```python
# Standard library imports
import os
import sys
from typing import List, Optional

# Third-party imports
from flask import Flask, jsonify
import numpy as np

# Local imports
from webapp.models import User
from webapp.utils import log_activity
```

### Naming Conventions

- **Variables and functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private methods**: `_leading_underscore`

Example:
```python
MAX_LINE_LENGTH = 100

class TextProcessor:
    def __init__(self):
        self.config = None
    
    def process_text(self, text: str) -> List[str]:
        """Process text and return lines."""
        return self._split_lines(text)
    
    def _split_lines(self, text: str) -> List[str]:
        """Internal method to split text."""
        return text.split('\n')
```

### Comments and Docstrings

Use docstrings for all public classes, methods, and functions:

```python
def generate_handwriting(text: str, style: int, bias: float) -> dict:
    """
    Generate handwritten SVG from text.
    
    Args:
        text: Input text to convert to handwriting
        style: Style number (0-9)
        bias: Randomness bias (0.0-1.0)
    
    Returns:
        Dictionary containing SVG data and metadata
        
    Raises:
        ValueError: If style or bias is out of range
    """
    # Implementation here
    pass
```

### Type Hints

Use type hints for function parameters and return values:

```python
from typing import List, Optional, Dict, Any

def process_pages(
    text: str,
    max_lines: int,
    config: Optional[Dict[str, Any]] = None
) -> List[List[str]]:
    """Process text into pages."""
    # Implementation
    return pages
```

## Testing

### Running Tests

Currently, WriteBot has some test scripts in the repository:

```bash
# Test text processing
python examples/demo_text_processing.py

# Test batch processing
python scripts/test_batch.py
```

### Writing Tests

When adding new features, include tests:

1. **Unit tests**: Test individual functions and classes
2. **Integration tests**: Test how components work together
3. **End-to-end tests**: Test complete user workflows

Example test structure:
```python
def test_text_processor():
    """Test text processor with various inputs."""
    from text_processor import TextProcessor, TextProcessingConfig
    
    config = TextProcessingConfig(max_line_length=50)
    processor = TextProcessor(config)
    
    # Test basic processing
    text = "Hello, World!"
    result, _ = processor.process_text(text)
    assert len(result) > 0
    assert all(len(line) <= 50 for line in result)
```

### Test Coverage

Aim for:
- **Critical paths**: 100% coverage
- **Core functionality**: 80%+ coverage
- **Edge cases**: Document known limitations

## Documentation

### When to Update Documentation

Update documentation when you:
- Add new features
- Change existing behavior
- Fix bugs that affect usage
- Update APIs or interfaces

### Documentation Files

- **README.md**: Overview and quick start
- **docs/**: Detailed guides and references
- **Code comments**: Explain complex logic
- **Docstrings**: Describe all public APIs

### Writing Good Documentation

- **Be clear and concise**: Use simple language
- **Include examples**: Show how to use features
- **Keep it updated**: Update docs with code changes
- **Use formatting**: Make docs easy to scan
- **Link related content**: Help users navigate

Example:
```markdown
## Feature Name

Brief description of what the feature does.

### Usage

\`\`\`python
# Example code here
result = do_something(param1, param2)
\`\`\`

### Parameters

- `param1` (str): Description of param1
- `param2` (int): Description of param2

### Returns

Description of what is returned.

### Example

Complete example showing typical usage.
```

## Pull Request Process

### Before Submitting

1. **Test your changes**:
   - Run existing tests
   - Test manually in the browser
   - Verify no regressions

2. **Update documentation**:
   - Update relevant docs
   - Add code comments
   - Update CHANGELOG if applicable

3. **Clean up your code**:
   - Remove debug statements
   - Fix formatting issues
   - Remove unused imports

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: Add feature description"
   ```

### Commit Message Format

Use conventional commit format:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Formatting, missing semicolons, etc.
- `refactor:` Code restructuring
- `test:` Adding tests
- `chore:` Maintenance tasks

Examples:
```
feat: Add batch processing API endpoint
fix: Resolve pagination issue with long paragraphs
docs: Update installation instructions
refactor: Simplify text processing logic
```

### Submitting a Pull Request

1. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a pull request** on GitHub:
   - Use a clear title describing the change
   - Reference any related issues
   - Describe what you changed and why
   - Include screenshots for UI changes
   - List any breaking changes

3. **Respond to feedback**:
   - Address review comments
   - Make requested changes
   - Update documentation if needed

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing
- [ ] Tests pass locally
- [ ] Manual testing completed
- [ ] Documentation updated

## Related Issues
Closes #123

## Screenshots (if applicable)
[Add screenshots here]

## Additional Notes
Any additional context or notes
```

## Reporting Bugs

### Before Reporting

1. **Check existing issues** to avoid duplicates
2. **Try the latest version** to see if it's already fixed
3. **Gather information** about the bug

### Bug Report Template

```markdown
**Describe the bug**
Clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '...'
3. Enter text '...'
4. See error

**Expected behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment:**
- OS: [e.g., Windows 10, macOS 12, Ubuntu 20.04]
- Python version: [e.g., 3.9.7]
- WriteBot version: [e.g., 1.0.0]
- Browser (if web issue): [e.g., Chrome 95]

**Additional context**
Any other relevant information.
```

## Suggesting Features

### Feature Request Template

```markdown
**Is your feature request related to a problem?**
Clear description of the problem.

**Describe the solution you'd like**
Clear description of what you want to happen.

**Describe alternatives you've considered**
Other solutions you've thought about.

**Additional context**
Any other context, screenshots, or examples.
```

## Development Tips

### Project Structure

Understand the codebase organization:
```
WriteBot/
├── webapp/              # Flask application
│   ├── routes/         # URL endpoints
│   ├── models.py       # Database models
│   ├── templates/      # HTML templates
│   └── static/         # CSS, JS, images
├── handwriting_synthesis/  # Core engine
├── text_processor.py   # Text processing
├── docs/               # Documentation
└── examples/           # Example scripts
```

### Useful Commands

```bash
# Check Python syntax
python -m py_compile your_file.py

# Format code (if black is installed)
black your_file.py

# Check imports
python -c "import your_module"

# Run Flask in debug mode
export FLASK_ENV=development
python webapp/app.py

# View database
sqlite3 writebot.db ".tables"

# Run migrations
cd webapp
python migrations/migrate.py status
```

### Getting Help

- **Documentation**: Check the [docs/](docs/) directory
- **Issues**: Search existing GitHub issues
- **Discussions**: Start a discussion on GitHub
- **Code**: Read the source code and comments

## Questions?

If you have questions about contributing:
1. Check this guide and other documentation
2. Search existing issues and discussions
3. Open a new discussion on GitHub
4. Reach out to maintainers

## Thank You!

Your contributions make WriteBot better for everyone. We appreciate your time and effort! 🙏

---

**Happy Contributing!** 🎉

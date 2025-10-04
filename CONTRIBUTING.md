# Contributing to AgentOSX

Thank you for your interest in contributing to AgentOSX! This document provides guidelines and instructions for contributing.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Making Changes](#making-changes)
5. [Testing](#testing)
6. [Pull Request Process](#pull-request-process)
7. [Code Style](#code-style)
8. [Documentation](#documentation)
9. [Community](#community)

---

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to team@agentosx.dev.

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

**Positive behaviors:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Accepting constructive criticism gracefully
- Focusing on what's best for the community
- Showing empathy towards others

**Unacceptable behaviors:**
- Harassment, trolling, or insulting comments
- Personal or political attacks
- Publishing others' private information
- Other conduct which could reasonably be considered inappropriate

---

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- GitHub account

### First Contribution

1. **Find an issue**: Look for issues labeled `good first issue` or `help wanted`
2. **Comment**: Let others know you're working on it
3. **Fork**: Create a fork of the repository
4. **Branch**: Create a feature branch
5. **Code**: Make your changes
6. **Test**: Run tests and ensure they pass
7. **PR**: Submit a pull request

---

## Development Setup

### 1. Fork and Clone

```bash
# Fork on GitHub, then:
git clone https://github.com/YOUR_USERNAME/agentOSX.git
cd agentOSX
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate
```

### 3. Install Dependencies

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Or install from requirements
pip install -r requirements.txt
```

### 4. Install Development Tools

```bash
pip install black mypy isort pytest pytest-cov pre-commit
```

### 5. Set Up Pre-commit Hooks

```bash
pre-commit install
```

---

## Making Changes

### Branch Naming

Use descriptive branch names:

- `feature/add-new-tool` - New features
- `fix/memory-leak` - Bug fixes
- `docs/update-readme` - Documentation
- `refactor/cleanup-code` - Refactoring
- `test/add-unit-tests` - Tests

### Commit Messages

Follow conventional commits:

```
type(scope): subject

body

footer
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, no code change)
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `test`: Adding tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(mcp): add WebSocket transport support

Implements WebSocket transport for MCP protocol to enable
real-time bidirectional communication between agents.

Closes #123
```

```
fix(cli): resolve hot reload memory leak

Fixed memory leak caused by not properly closing file watchers
when agent is reloaded.

Fixes #456
```

---

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test Suite

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/test_integration.py -v

# With coverage
pytest tests/ -v --cov=agentosx --cov-report=html
```

### Run Specific Test

```bash
pytest tests/unit/test_cli_utils.py::test_specific_function -v
```

### Test Coverage Requirements

- Aim for **80%+ coverage** for new code
- All new features must have tests
- Bug fixes should include regression tests

---

## Pull Request Process

### Before Submitting

1. **Run tests**: Ensure all tests pass
2. **Run linters**: `black .`, `mypy agentosx`, `isort .`
3. **Update docs**: Document new features
4. **Add tests**: Cover new code
5. **Update CHANGELOG**: Add entry for your change

### Submitting PR

1. **Push branch**: Push to your fork
2. **Create PR**: Use GitHub's PR interface
3. **Fill template**: Complete the PR template
4. **Link issue**: Reference related issues
5. **Wait for review**: Be responsive to feedback

### PR Title Format

```
type(scope): Brief description

Example:
feat(orchestration): add parallel workflow execution
fix(mcp): resolve connection timeout issue
```

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
Describe testing done:
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing performed

## Checklist
- [ ] My code follows the code style of this project
- [ ] I have added tests to cover my changes
- [ ] All new and existing tests pass
- [ ] I have updated the documentation accordingly
- [ ] I have added an entry to CHANGELOG.md

## Related Issues
Closes #123
Fixes #456
```

### Review Process

1. **Automated checks**: Must pass CI/CD
2. **Code review**: 1-2 reviewers required
3. **Address feedback**: Make requested changes
4. **Approval**: Reviewers approve PR
5. **Merge**: Maintainer merges PR

---

## Code Style

### Python Style Guide

We follow **PEP 8** with some modifications:

- **Line length**: 100 characters (not 79)
- **Quotes**: Double quotes for strings
- **Imports**: Absolute imports, grouped by standard/third-party/local
- **Type hints**: Required for all function signatures
- **Docstrings**: Google style

### Formatting Tools

```bash
# Auto-format code
black agentosx tests

# Sort imports
isort agentosx tests

# Type checking
mypy agentosx
```

### Example

```python
"""
Module docstring explaining purpose.
"""

from typing import List, Optional, Dict, Any
import asyncio
import logging

from agentosx import BaseAgent
from agentosx.tools import tool

logger = logging.getLogger(__name__)


class MyAgent(BaseAgent):
    """
    Agent class docstring.
    
    Detailed description of what this agent does.
    
    Attributes:
        name: Agent name
        version: Agent version
    """
    
    def __init__(self, name: str = "my_agent"):
        """
        Initialize agent.
        
        Args:
            name: Agent name
        """
        super().__init__(name=name, version="1.0.0")
        self.custom_state: Dict[str, Any] = {}
    
    async def process(self, input: str, context: Optional[Dict] = None) -> str:
        """
        Process input and return response.
        
        Args:
            input: User input text
            context: Optional execution context
            
        Returns:
            Agent response text
            
        Raises:
            ValueError: If input is empty
        """
        if not input:
            raise ValueError("Input cannot be empty")
        
        # Process logic here
        return f"Processed: {input}"
    
    @tool
    async def search(self, query: str, limit: int = 10) -> List[str]:
        """
        Search for information.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of search results
        """
        # Search logic
        return [f"Result {i}" for i in range(limit)]
```

---

## Documentation

### Docstring Format

Use Google-style docstrings:

```python
def function(arg1: str, arg2: int = 0) -> bool:
    """
    Brief description.
    
    Longer description explaining what the function does,
    how it works, and any important details.
    
    Args:
        arg1: Description of arg1
        arg2: Description of arg2 (default: 0)
    
    Returns:
        Description of return value
    
    Raises:
        ValueError: When arg1 is empty
        RuntimeError: When operation fails
    
    Examples:
        >>> function("test", 5)
        True
        
        >>> function("")
        ValueError: arg1 cannot be empty
    """
    pass
```

### Updating Documentation

- Update relevant `.md` files in `docs/`
- Add examples for new features
- Update CLI_REFERENCE.md for CLI changes
- Update API_REFERENCE.md for API changes

---

## Community

### Communication Channels

- **GitHub Issues**: Bug reports, feature requests
- **GitHub Discussions**: Questions, ideas, show & tell
- **Discord**: Real-time chat (coming soon)
- **Email**: team@agentosx.dev

### Getting Help

- Check existing issues and discussions
- Read documentation thoroughly
- Ask in GitHub Discussions
- Join Discord community

### Reporting Bugs

Use the bug report template:

```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce:
1. Run command '...'
2. See error

**Expected behavior**
What you expected to happen.

**Actual behavior**
What actually happened.

**Environment**
- OS: [e.g., Windows 11]
- Python version: [e.g., 3.10.5]
- AgentOSX version: [e.g., 0.1.0]

**Additional context**
Any other relevant information.
```

### Suggesting Features

Use the feature request template:

```markdown
**Is your feature request related to a problem?**
Describe the problem you're trying to solve.

**Describe the solution you'd like**
Clear description of what you want to happen.

**Describe alternatives you've considered**
Other solutions or features you've considered.

**Additional context**
Any other relevant information, mockups, examples.
```

---

## Recognition

Contributors will be recognized in:

- CHANGELOG.md for their contributions
- GitHub contributors page
- Annual contributor spotlight (coming soon)

---

## Questions?

If you have questions about contributing, please:

1. Check existing documentation
2. Search GitHub issues/discussions
3. Ask in GitHub Discussions
4. Email team@agentosx.dev

Thank you for contributing to AgentOSX! 🎉

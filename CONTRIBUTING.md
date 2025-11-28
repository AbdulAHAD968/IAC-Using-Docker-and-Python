# Contributing to Enhanced CMS

Thank you for your interest in contributing to the Enhanced Container Management System! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Report issues professionally

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Create a virtual environment
4. Install dependencies
5. Create a feature branch

```bash
git clone https://github.com/your-username/enhanced-cms.git
cd enhanced-cms
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
git checkout -b feature/your-feature
```

## Development Guidelines

### Code Style
- Follow PEP 8 guidelines
- Use meaningful variable names
- Keep functions focused and modular
- Add docstrings to all functions

### Clean Code Requirements
- No comments in production code
- No emojis in code
- Use clear, self-documenting code
- Remove debug statements before committing

### Testing
- Write tests for new features
- Run comprehensive tests before submitting PR
- Ensure all existing tests pass
- Test on multiple environments if possible

```bash
python3 comprehensive_ids_test.py
```

## Making Changes

### Before You Start
- Check existing issues and pull requests
- Discuss major changes in an issue first
- Ensure your fork is up to date with main branch

### During Development
1. Create a feature branch from `main`
2. Make focused, atomic commits
3. Write clear commit messages
4. Push regularly to your fork

### Commit Message Guidelines
```
Type: Brief description (50 chars max)

Detailed explanation if needed, wrapped at 72 characters.
Mention any related issues: Fixes #123

- Use bullet points for multiple changes
- Explain why the change was made
- Reference issue numbers
```

### Types
- `feat:` A new feature
- `fix:` A bug fix
- `docs:` Documentation only
- `refactor:` Code refactoring without behavior change
- `test:` Adding or updating tests
- `chore:` Build process, dependencies, etc.

## Pull Request Process

1. Update README.md with new features or changes
2. Update CHANGELOG.md with your changes
3. Ensure all tests pass locally
4. Submit PR with clear description
5. Link related issues
6. Wait for review and address feedback

### PR Title Format
```
[Type] Brief description

Example: [feat] Add Kubernetes support to IDS
Example: [fix] Correct SQL injection pattern detection
```

### PR Description Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How was this tested?

## Checklist
- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Changes verified in clean environment
```

## Code Review Process

- At least 1 approval required before merge
- Address all requested changes
- Maintain professional communication
- Ask questions if feedback is unclear

## ML Model Improvements

If contributing new or improved models:

1. Train model with scikit-learn (compatible with 1.6.1+)
2. Save model as `.pkl` file
3. Add model loading test
4. Update `cms/ids_manager.py` with new detection patterns
5. Document model architecture and training data
6. Include performance metrics
7. Test hybrid detection (manual + ML)

### Model Requirements
- Scikit-learn compatible
- Pickle serializable
- Clear feature requirements
- Performance tested (>95% accuracy preferred)

## Documentation

### For New Features
- Add docstring to functions
- Update README with feature description
- Add API endpoint documentation if applicable
- Include usage examples

### For Bug Fixes
- Document what was broken
- Explain the root cause
- Show how fix resolves issue
- Add test case preventing regression

## Reporting Issues

Use GitHub Issues to report bugs or suggest features.

### Bug Report Template
```markdown
## Description
Clear description of the bug

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: 
- Python: 
- Docker: 
- Branch: 

## Logs
Include relevant logs or screenshots
```

### Feature Request Template
```markdown
## Feature Description
Clear description of requested feature

## Use Case
Why is this feature needed?

## Proposed Solution
How should it work?

## Alternatives
Other possible approaches

## Additional Context
Any other information
```

## Development Workflow

### Setup Development Environment
```bash
git clone https://github.com/your-username/enhanced-cms.git
cd enhanced-cms
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # if it exists
```

### Run Tests
```bash
python3 comprehensive_ids_test.py
```

### Manual Testing
```bash
python3 enhanced_api.py
# Access http://localhost:5001 in browser
```

## Performance Considerations

- Minimize database queries
- Cache frequently accessed data
- Profile code before optimization
- Consider memory usage in long-running processes
- Test with realistic data volumes

## Security Considerations

- Never commit secrets or credentials
- Use environment variables for sensitive data
- Validate all user inputs
- Sanitize log outputs
- Follow OWASP guidelines
- Review security implications of changes

## Documentation Standards

### Python Docstrings
```python
def analyze_web_log(self, log_line):
    """Analyze web server log for threats.
    
    Performs manual pattern matching and ML analysis
    to detect web-based attacks.
    
    Args:
        log_line (str): Raw web server log line
        
    Returns:
        dict: Alert object if threat detected, None otherwise
        
    Raises:
        ValueError: If log format is invalid
    """
    pass
```

### Comments (Where Necessary)
```python
# Only use comments for "why", not "what"
# Good: timeout protects against infinite loops
# Bad: set timeout to 30
timeout = 30  # seconds

# For complex algorithms, explain the approach
# We use hybrid detection: manual rules first (fast)
# then ML models for anomalies (comprehensive)
```

## Release Process

1. Update version numbers
2. Update CHANGELOG.md
3. Create release notes
4. Tag release on GitHub
5. Create GitHub release with notes
6. Announce on relevant channels

## Questions or Need Help?

- Check existing issues and discussions
- Create a new discussion for questions
- Mention relevant maintainers
- Be patient and respectful

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- GitHub contributors page
- Release notes for major contributions

## License

By contributing, you agree your code will be licensed under the same license as the project (MIT License).

Thank you for contributing to Enhanced CMS!

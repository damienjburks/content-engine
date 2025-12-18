# Content Engine

![Build Status](https://img.shields.io/github/actions/workflow/status/damienjburks/content-engine/publish-content.yml?branch=main&style=for-the-badge)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg?style=for-the-badge)](https://www.python.org/downloads/)
[![dev.to](https://img.shields.io/badge/dev.to-0A0A0A?style=for-the-badge&logo=dev.to&logoColor=white)](https://dev.to/damienjburks)
[![Hashnode](https://img.shields.io/badge/Hashnode-2962FF?style=for-the-badge&logo=hashnode&logoColor=white)](https://blog.damienjburks.com)
[![Made with ❤️ using Kiro](https://img.shields.io/badge/Made%20with%20❤️%20using-Kiro-purple.svg?style=for-the-badge)](https://kiro.ai)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json&style=for-the-badge)](https://github.com/astral-sh/uv)

A Python application for publishing content to multiple platforms (dev.to and Hashnode) simultaneously. This content engine enables creators to reach broader audiences by publishing to multiple platforms while maintaining content consistency and avoiding duplication.

## Features

- **Multi-Platform Publishing**: Simultaneously publish to dev.to and Hashnode
- **Intelligent Content Detection**: Automatically detects existing articles and updates only when content changes
- **Automatic Article Removal**: Removes articles from all platforms when markdown files are deleted
- **Platform-Specific Transformations**: Handles platform-specific formatting requirements
- **Error Isolation**: Platform failures don't affect publishing to other platforms
- **Extensible Architecture**: Easy to add support for new blogging platforms
- **Modern Python Tooling**: Uses `uv` for fast, reliable dependency management
- **Comprehensive Testing**: Includes both unit tests and property-based testing

## Installation

### Prerequisites

1. **Python 3.12+**: Ensure you have Python 3.12 or higher installed
2. **uv Package Manager**: Install `uv` following the [official installation guide](https://docs.astral.sh/uv/getting-started/installation/)

### Quick Installation

```bash
# Clone the repository
git clone <repository-url>
cd content-engine

# Install dependencies using uv
uv sync

# Activate the virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Development Installation

For development work, install with development dependencies:

```bash
# Install with development dependencies
uv sync --dev

# Verify installation
uv run pytest --version
```

## Configuration

### API Key Setup

The system requires API keys for each platform you want to publish to:

#### dev.to Configuration

1. Go to [dev.to Settings](https://dev.to/settings/extensions)
2. Generate an API key
3. Set the environment variable:

```bash
export DEVTO_API_KEY="your_devto_api_key_here"
```

#### Hashnode Configuration

1. Go to [Hashnode Developer Settings](https://hashnode.com/settings/developer)
2. Generate a Personal Access Token
3. Go to [Hashnode Blog Settings](https://hashnode.com/settings/blogs) to get your Publication ID
4. Set the environment variables:

```bash
export HASHNODE_API_KEY="your_hashnode_api_key_here"
export HASHNODE_USERNAME="your_hashnode_username"
export HASHNODE_PUBLICATION_ID="your_24_character_publication_id"
```

**Note**: The Publication ID should be a 24-character hexadecimal string (MongoDB ObjectId format). You can find it using the helper script:

```bash
python scripts/get_hashnode_publication_id.py
```

This script will automatically find your publication IDs and show you which one to use.

### Optional Configuration

You can customize the behavior with additional environment variables:

```bash
# Specify which platforms to use (default: all available)
export ENABLED_PLATFORMS="devto,hashnode"

# Set rate limiting delay between requests (default: 5 seconds)
export RATE_LIMIT_DELAY="5"

# Customize markdown file pattern (default: blogs/*.md)
export MARKDOWN_FILE_PATTERN="posts/*.md"

# Exclude specific files (default: README.md)
export EXCLUDE_FILES="README.md,CHANGELOG.md"

# Skip deletion when permission errors occur (default: true)
export SKIP_DELETION_ON_PERMISSION_ERROR="true"
```

## GitHub Actions Setup

This project includes GitHub Actions for automated content publishing. The workflows will automatically publish your content when you push changes to your repository.

### Required Secrets

Set up the following secrets in your GitHub repository settings (`Settings > Secrets and variables > Actions`):

```bash
DEVTO_API_KEY=your_devto_api_key_here
HASHNODE_API_KEY=your_hashnode_api_key_here
HASHNODE_USERNAME=your_hashnode_username
HASHNODE_PUBLICATION_ID=your_24_character_publication_id
```

### Available Workflows

#### 1. Automatic Publishing (`publish-content.yml`)

**Triggers:**
- Push to `main`/`master` branch with changes to `blogs/` or `src/`
- Pull requests (runs validation only)
- Manual trigger with force publish option

**Features:**
- ✅ Automatic content publishing on push
- 🔍 Validation-only mode for pull requests
- 🧪 Optional test execution
- 📊 Failure log uploads
- 🔒 Security scanning

#### 2. Scheduled Publishing (`scheduled-publish.yml`)

**Triggers:**
- Daily at 9 AM UTC (customizable)
- Manual trigger with platform selection
- Dry-run mode for validation

**Features:**
- 📅 Scheduled daily publishing
- 🎯 Platform selection (devto, hashnode, or both)
- 🔍 Dry-run mode for testing
- 📊 Detailed summary reports

### Manual Workflow Triggers

You can manually trigger workflows from the GitHub Actions tab:

1. **Force Publish All**: Republish all articles regardless of changes
2. **Dry Run**: Validate configuration and count files without publishing
3. **Platform-Specific**: Publish to only dev.to or Hashnode

### Workflow Security

- **Secrets Protection**: API keys are stored as encrypted secrets
- **Branch Protection**: Only runs on main/master branches for publishing
- **Code Scanning**: Includes security and quality checks
- **Artifact Upload**: Saves logs for debugging failures

### CODEOWNERS

The repository includes a `CODEOWNERS` file that:
- Requires your review for all changes
- Protects critical files (API clients, configuration)
- Ensures security for sensitive components

## Usage

### Local Usage

Place your markdown files in the `blogs/` directory (or your configured pattern) and run:

```bash
# Using uv (recommended)
uv run python -m src.main

# Or with activated virtual environment
python -m src.main

# Or using the installed script
content-engine
```

### Expected Output

```text
INFO:src.main:PostPublisher initialized with platforms: ['devto', 'hashnode']
INFO:src.main:Found 3 markdown files to process
INFO:src.main:Processing file: blogs/my-awesome-post.md
INFO:src.main:'My Awesome Post' - Success: devto (created), hashnode (updated)
INFO:src.main:Processing file: blogs/another-post.md
INFO:src.main:'Another Post' - Skipped (no changes): devto, hashnode
```

### Command Line Options

The system automatically detects and processes all markdown files matching your configured pattern. It will:

1. **Remove deleted articles**: Check for articles that no longer have corresponding markdown files and remove them from all platforms
2. **Check for existing articles** on each platform
3. **Create new articles** if none exist
4. **Update existing articles** only if content has changed
5. **Skip unchanged articles** to preserve engagement metrics
6. **Report results** for each platform and article

### Automatic Article Removal

When you delete a markdown file, the Content Engine will automatically:

- ✅ **Detect the missing file** by comparing current files with published articles
- ✅ **Remove from all platforms** where the article exists
- ✅ **Log the removal process** for transparency
- ✅ **Continue on errors** - if removal fails on one platform, it continues with others
- ✅ **Handle permission errors gracefully** - skips articles in collaborative blogs where you lack admin access

**Example workflow:**
```bash
# You have: blogs/my-article.md (published to dev.to and Hashnode)
rm blogs/my-article.md

# Next time you run content-engine:
content-engine
# Output: 
# INFO: Removing 'My Article' from devto...
# INFO: ✅ Successfully removed 'My Article' from devto
# INFO: Removing 'My Article' from hashnode...
# INFO: ✅ Successfully removed 'My Article' from hashnode
```

**Collaborative Blog Handling:**

If you're a contributor (not admin) on a Hashnode publication, you'll see:

```bash
# INFO: Removing 'My Article' from hashnode...
# WARNING: ⚠️  Cannot delete article from Hashnode: Insufficient permissions (collaborative blog). 
#          This article is in a publication where you have contributor access but admin access is required for deletion. 
#          Please ask a publication admin to delete this article manually.
```

The system will continue processing other articles and platforms normally.

## Frontmatter Fields

Your markdown files must include frontmatter with the following supported fields:

### Required Fields

```yaml
---
title: "Your Article Title"                    # Article title (required)
slug: "your-article-slug"                     # URL slug for the article
domain: "yourblog.hashnode.dev"               # Your Hashnode domain
---
```

### Optional Fields

```yaml
---
subtitle: "Article subtitle"                   # Subtitle/description
tags: "python, tutorial, beginners"          # Comma-separated tags
cover: "https://example.com/image.jpg"        # Cover image URL
saveAsDraft: false                            # Publish as draft (default: false)
enableToc: true                               # Enable table of contents (default: true)
seriesName: "Python Tutorial Series"         # Series name (optional)
---
```

### Complete Example

```yaml
---
title: "Getting Started with Python"
subtitle: "A beginner's guide to Python programming"
slug: "getting-started-with-python"
tags: "python, programming, beginners, tutorial"
cover: "https://example.com/python-cover.jpg"
domain: "myblog.hashnode.dev"
saveAsDraft: false
enableToc: true
seriesName: "Python Fundamentals"
---

# Getting Started with Python

Your markdown content goes here...
```

## Project Structure

```text
content-engine/
├── src/
│   ├── client/                    # Platform-specific API clients
│   │   ├── devto_client.py       # dev.to API integration
│   │   └── hashnode_client.py    # Hashnode GraphQL API integration
│   ├── interfaces/                # Abstract interfaces
│   │   ├── platform_client.py    # Platform client interface
│   │   └── content_processor.py  # Content processing interface
│   ├── models/                    # Data models
│   │   └── post_content.py       # PostContent, ArticleStatus, PublicationResult
│   ├── processors/                # Content processing
│   │   └── content_processor.py  # Platform-specific transformations
│   ├── managers/                  # Publication coordination
│   │   └── publication_manager.py # Multi-platform publishing logic
│   ├── utils/                     # Utilities
│   │   └── error_handler.py      # Error handling and logging
│   └── main.py                    # Main entry point and CLI
├── tests/                         # Test suite
├── blogs/                         # Your markdown files (default location)
├── pyproject.toml                 # Project configuration and dependencies
└── README.md                      # This file
```

### Component Purposes

- **PlatformClient Interface**: Standardizes interaction with different blogging platforms
- **PostContent Model**: Represents blog post data in a platform-agnostic way
- **ContentProcessor**: Handles platform-specific content transformations and normalization
- **PublicationManager**: Coordinates publishing across multiple platforms with error isolation
- **ErrorHandler**: Provides comprehensive error handling and logging
- **ContentEngine**: Main orchestrator that ties everything together

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=src --cov-report=html

# Run only unit tests
uv run pytest tests/ -k "not property"

# Run only property-based tests
uv run pytest tests/ -k "property" -v

# Run tests with verbose output
uv run pytest -v
```

### Code Quality Tools

```bash
# Format code with Black
uv run black src tests

# Sort imports with isort
uv run isort src tests

# Lint code with pylint
uv run pylint src

# Type checking with mypy
uv run mypy src

# Run all quality checks
uv run black src tests && uv run isort src tests && uv run pylint src && uv run mypy src
```

### Adding a New Platform

To add support for a new blogging platform:

1. **Create a new client** in `src/client/` that implements `PlatformClient`
2. **Add platform-specific transformations** in `ContentProcessor`
3. **Update configuration** to include the new platform
4. **Add tests** for the new platform integration

Example:

```python
# src/client/medium_client.py
from ..interfaces.platform_client import PlatformClient

class MediumClient(PlatformClient):
    def publish_article(self, post_content: Dict, published: bool) -> Dict:
        # Implement Medium API integration
        pass
    
    # Implement other required methods...
```

## Troubleshooting

### Common Issues

#### Authentication Errors

**Problem**: `Authentication failed for platform: devto`

**Solution**:

- Verify your API key is correct
- Check that the environment variable is properly set
- Ensure the API key has the necessary permissions

```bash
# Check if environment variable is set
echo $DEVTO_API_KEY

# Test API key manually
curl -H "api-key: $DEVTO_API_KEY" https://dev.to/api/articles/me
```

#### Rate Limiting

**Problem**: `Rate limit exceeded for platform: hashnode`

**Solution**:

- Increase the `RATE_LIMIT_DELAY` environment variable
- Reduce the number of files processed at once
- Check platform-specific rate limits

```bash
# Increase delay between requests
export RATE_LIMIT_DELAY="10"
```

#### Missing Dependencies

**Problem**: `ModuleNotFoundError: No module named 'hypothesis'`

**Solution**:

```bash
# Reinstall dependencies
uv sync

# Or install specific missing dependency
uv add hypothesis
```

#### Frontmatter Parsing Errors

**Problem**: `Missing required 'title' field in blogs/post.md`

**Solution**:

- Ensure your markdown files have proper YAML frontmatter
- Check that the frontmatter is enclosed in `---` markers
- Verify required fields are present

```yaml
---
title: "Your Title Here"  # This field is required
slug: "your-slug"         # This field is required
domain: "your.domain"     # This field is required
---
```

#### Platform-Specific Issues

**dev.to Issues**:

- Ensure your API key has write permissions
- Check that your account is in good standing
- Verify article content meets dev.to guidelines

**Hashnode Issues**:

- Confirm both `HASHNODE_API_KEY` and `HASHNODE_USERNAME` are set
- Verify your Hashnode publication exists
- Check that your API token has publication permissions

#### Collaborative Blog Permission Issues

**Problem**: `User does not have the minimum required role in the publication`

**Solution**:

This occurs when you're a contributor on a Hashnode publication but don't have admin access. The system will automatically skip deletion for these articles and log a warning.

- **For your own publications**: You have full admin access and can delete articles
- **For collaborative publications**: Only admins can delete articles
- **Workaround**: Ask the publication admin to delete the article manually, or leave it published

The system will continue processing other articles normally. This is expected behavior for collaborative blogs.

### Debug Mode

Enable debug logging for more detailed output:

```bash
# Set log level to debug
export LOG_LEVEL="DEBUG"

# Run with debug output
uv run python -m src.main
```

### Getting Help

1. **Check the logs**: The system provides detailed logging for troubleshooting
2. **Verify configuration**: Use the built-in validation to check your setup
3. **Test individual platforms**: Temporarily disable platforms to isolate issues
4. **Check API documentation**: Refer to platform-specific API documentation

## Migration from requirements.txt

This project has been migrated from `requirements.txt` to `pyproject.toml` for modern Python packaging:

- **Preserved Dependencies**: All dependencies from `requirements.txt` are maintained
- **Development Dependencies**: Separated development and production dependencies
- **Tool Configuration**: Configured Black, isort, pylint, mypy, and pytest in `pyproject.toml`
- **Property-Based Testing**: Added Hypothesis for comprehensive testing
- **Lock File**: Uses `uv.lock` for reproducible builds

### Benefits of uv

- **Faster Installation**: Significantly faster dependency resolution and installation
- **Better Caching**: Improved caching for faster subsequent installs
- **Reproducible Builds**: Lock file ensures consistent environments
- **Modern Standards**: Follows latest Python packaging standards

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `uv run pytest`
5. Run code quality checks: `uv run black src tests && uv run pylint src`
6. Commit your changes: `git commit -am 'Add feature'`
7. Push to the branch: `git push origin feature-name`
8. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

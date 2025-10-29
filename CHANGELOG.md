# Changelog

All notable changes to WriteBot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive root README.md with project overview
- CONTRIBUTING.md guide for contributors
- QUICKSTART.md for rapid onboarding
- LICENSE file (MIT License)
- CHANGELOG.md to track project changes
- Enhanced documentation structure and navigation

### Changed
- Improved model/README.md with clearer training instructions
- Enhanced docs/README.md with comprehensive documentation guide
- Better organization of documentation files

### Documentation
- Added detailed installation instructions
- Improved API documentation navigation
- Added troubleshooting sections throughout
- Enhanced code examples and usage guides

## [1.0.0] - 2025-10-29

### Added
- Database migration system with 14 migrations
- Custom page size and template presets feature
- User authentication and authorization system
- Role-based access control (user and admin roles)
- Activity logging and audit trail
- Usage statistics tracking
- Admin dashboard with user management
- Batch processing via CSV upload
- Character override system for custom styling
- Advanced text processing with paragraph detection
- Smart word wrapping and pagination
- Multiple paragraph formatting styles
- Template preset selector in web interface
- Page size preset management
- Flask extensions for compression, caching, and minification

### Changed
- Refactored Flask application to modular structure
- Improved text processing with intelligent paragraph handling
- Enhanced word wrapping algorithm
- Better handling of empty lines and paragraphs
- Optimized database queries with indexes

### Fixed
- Empty lines no longer converted to periods
- Word wrapping respects word boundaries
- Improved character sanitization
- Better handling of long words

### Security
- Bcrypt password hashing
- CSRF protection on all forms
- Session security improvements
- Input validation and sanitization
- SQL injection prevention via SQLAlchemy ORM

## [0.9.0] - 2025-10-21

### Added
- Text processing improvements
- Integration layer between text processor and handwriting synthesis
- Demo scripts for text processing
- Comprehensive text processing guide

### Changed
- Webapp integration to use new text processing system
- Fallback mechanism for backward compatibility

### Documentation
- TEXT_PROCESSING_GUIDE.md with usage examples
- INTEGRATION_SUMMARY.md explaining the integration
- Updated inline documentation

## [0.8.0] - Earlier

### Added
- Basic handwriting synthesis functionality
- Flask web application
- REST API endpoints
- Multiple handwriting styles
- SVG output generation
- Basic text processing

### Documentation
- Initial documentation structure
- API documentation with Sphinx
- Basic README files

---

## Version History

### Version Numbering

WriteBot follows [Semantic Versioning](https://semver.org/):
- **MAJOR** version for incompatible API changes
- **MINOR** version for new functionality in a backward compatible manner
- **PATCH** version for backward compatible bug fixes

### Release Notes

For detailed release notes, see the [Releases](https://github.com/ariedotcodotnz/WriteBot/releases) page on GitHub.

## Categories

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security improvements
- **Documentation**: Documentation changes

## Contributing

To suggest changes or report issues, please:
1. Check existing [issues](https://github.com/ariedotcodotnz/WriteBot/issues)
2. Open a new issue with details
3. Follow the [Contributing Guide](CONTRIBUTING.md)

## Links

- [GitHub Repository](https://github.com/ariedotcodotnz/WriteBot)
- [Issue Tracker](https://github.com/ariedotcodotnz/WriteBot/issues)
- [Documentation](docs/README.md)

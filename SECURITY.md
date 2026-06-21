# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 3.x     | ✅ Yes             |
| < 3.0   | ❌ No              |

## Reporting a Vulnerability

If you discover a security vulnerability in XtreamRip, please report it responsibly:

1. **Do NOT** open a public issue
2. **Email** [mazenelhwarey@gmail.com](mailto:mazenelhwarey@gmail.com) with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
3. You will receive a response within **48 hours**

## Scope

XtreamRip is a CLI tool that connects to user-provided IPTV servers. The following are in scope:

- Credential storage security (local config files)
- API request handling (injection, SSRF)
- File path traversal in download paths
- Dependencies with known CVEs

## Out of Scope

- Security of the IPTV server itself
- Content legality
- Network interception (users are responsible for their own network security)

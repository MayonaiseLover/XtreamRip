# Contributing to XtreamRip

Thanks for your interest in contributing! Here's how to get started.

## 🚀 Quick Start

1. **Fork** the repo
2. **Clone** your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/XtreamRip.git
   cd XtreamRip
   ```
3. **Install** dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. **Create a branch** for your feature:
   ```bash
   git checkout -b feature/your-feature-name
   ```
5. **Make your changes**, test them, and commit:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```
6. **Push** and open a Pull Request:
   ```bash
   git push origin feature/your-feature-name
   ```

## 📝 Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | When to use |
|--------|-------------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `refactor:` | Code change that neither fixes a bug nor adds a feature |
| `style:` | Formatting, missing semicolons, etc. |
| `test:` | Adding tests |
| `chore:` | Maintenance tasks |

## 🎨 Code Style

- **Python 3.10+** — use type hints where possible
- **PEP 8** — standard Python style
- Keep functions focused and reasonably sized
- Add comments only where the logic isn't obvious
- Use `rich` for terminal output, `questionary` for interactive prompts

## 🧪 Testing

Before submitting a PR:
1. Run the tool end-to-end: `python iptv_dl.py`
2. Test on your platform (Linux, macOS, or Termux)
3. Verify FFmpeg integration if your changes touch encoding

## 🐛 Reporting Bugs

Use the [Bug Report template](https://github.com/MayonaiseLover/XtreamRip/issues/new?template=bug_report.md) and include:
- Steps to reproduce
- Expected vs. actual behavior
- Your environment (OS, Python version, FFmpeg version)

## 💡 Feature Requests

Use the [Feature Request template](https://github.com/MayonaiseLover/XtreamRip/issues/new?template=feature_request.md).

## 📜 License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).

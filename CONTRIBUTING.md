# Contributing to carvera-vision

Thank you for your interest in contributing! This project gives Claude Desktop
and Claude Code 3D awareness and screen vision for Carvera CNC users.

## Ways to Contribute

### 1. Testing and Bug Reports

- Test with different STEP exporters (Fusion 360, Plasticity, Shapr3D, etc.)
- Test window capture on different OS versions and display configurations
- Report issues with detailed reproduction steps

### 2. Tool Library Profiles

Contribute Makera CSV tool exports:
- Your validated Carvera tool configurations
- Community-tested feeds/speeds for specific materials
- Third-party end mills with Carvera-compatible holders

### 3. STEP Parser Improvements

- Better feature detection (pocket depth, hole classification)
- Support for additional STEP entity types
- Edge cases from specific CAD exporters

### 4. Platform Support

- macOS window detection improvements (Screen Recording permission flow)
- Linux: Wayland support (currently X11 only via wmctrl)
- Window alias additions for regional MakeraCam builds

### 5. Documentation

- Usage walkthroughs for specific workflows
- Material-specific machining guides
- Troubleshooting additions

## Development Setup

```bash
git clone https://github.com/3DCreationsByChad/carvera-vision
cd carvera-vision
uv sync
uv run carvera-vision  # start the MCP server
```

Test with MCP Inspector:
```bash
uv run mcp dev src/carvera_vision/server.py
```

## Code Style

- Python code follows PEP 8
- Type hints on all public functions
- Keep dependencies minimal — no heavy geometry kernels

## Submitting Changes

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make changes and test
3. Push and open a Pull Request

## Reporting Issues

Include:
- OS and Python version
- STEP file source (which CAD tool exported it)
- Steps to reproduce
- Expected vs actual behavior

## Code of Conduct

Be respectful, constructive, and focused on the technical merits.

Thank you for helping Carvera users work smarter!

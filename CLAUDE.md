# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run application
cd src && python main.py              # Normal mode
cd src && python main.py -dev         # Developer mode (extra GUI panel)
cd src && python main.py -dev -dwi    # Cross-platform dev (no Windows automation)

# Tests
pytest                                # Run all tests
pytest -v                             # Verbose
pytest -k test_name                   # Run specific test by name
pytest src/core/detection/tests/      # Run tests in a directory
pytest --cov                          # With coverage

# Build
python build.py                       # Create Windows executable via PyInstaller
```

## Context

Read these files for full project context:

- `.ai-context.md` — Patterns, conventions, testing requirements, extension points, gotchas, and post-implementation checklist
- `.ai-modules.md` — Module-by-module reference with responsibilities and dependencies
- `ARCHITECTURE.md` — Full system design documentation
- `CONTRIBUTING.md` — Development environment setup, commit conventions, and PR process
- `docs/RACING_CONCEPTS.md` — Racing domain terminology

## Documentation Updates

After implementing changes, **always review and update** the documentation files listed above (plus `README.md` and this file) when relevant. See the Post-Implementation Checklist in `.ai-context.md` for the full list and criteria. Skipping documentation updates causes knowledge drift.

## Planning Requirements

Every plan MUST include a final step: "Review and update documentation" referencing
the Post-Implementation Checklist in `.ai-context.md`. Do not skip this step.

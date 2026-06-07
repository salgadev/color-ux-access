# AGENTS.md - Agent Behavior Guidelines for Color-UX-Access

## Project Overview
This repository contains the Color-UX-Access project, a Gradio app that uses a 32B Vision Language Model (VLM) via Hugging Face Router API to perform automated accessibility audits for color vision deficiency (CVD) and WCAG compliance.

## Agent Behavior & Constraints

### General Principles
- **No hardcoding**: Avoid hardcoded field names, dates, URLs, or element labels. Write fixes in relative terms so they work on any unfamiliar site.
- **Prefer framework-level solutions**: Prioritize generic, reusable fixes over one-off patches for specific sites.
- **Test locally, think globally**: While testing may occur on the Parks Canada reservation site, solutions must generalize to any site.
- **Consolidate, don't delete**: When modifying files, prefer consolidation over deletion. Ask first if unsure.

### Environment & Tools
- **OS**: Windows (10/11). Use `python` (not `python3` to avoid Microsoft Store prompt). Unix tools available via Git-Bash/MSYS.
- **Paths**: Prefer project-local paths. Validate `HERMES_HOME` environment variable for Hermes-related paths.
  - Hermes config/data: `G:\AI\HERMES`
  - Hermes CLI: `C:\Users\socd0\AppData\Local\hermes\hermes-agent`
- **Python**: Use the project's virtual environment (`.venv`) when available.
- **Gradio ghost processes**: Be aware of and clean up Gradio ghost processes (see `hermes-ghost-processes` skill if needed).

### Communication & Reporting
- **Updates**: Prefer concise technical updates—direct confirmation of working systems over narrative explanations.
- **Primary channel**: Telegram for updates; cron pings are welcome.
- **Voice-over narration**: For test walkthroughs, prefer post-process voice-over narration generated from test logs over live TTS during execution.

### Development Practices
- **TDD**: Tests are enforced—write tests first. If setup is missing, ping for assistance.
- **Commits**: Make small, focused commits with clear messages.
- **Documentation**: Update README.md and other documentation as needed.
- **Secrets**: Never hardcode API keys, tokens, or passwords. Use environment variables or secure secret stores.
- **License**: The project is open source (see LICENSE file). Maintain compliance.

### Specific to This Repository
- **Model Size**: Total parameters across all models used must be ≤ 32 billion (HF Build Small Hackathon constraint).
- **Gradio Requirement**: The app must be a Gradio app (not Streamlit, FastAPI, etc.).
- **Deployment**: If deploying to Hugging Face Spaces, must be under the `build-small-hackathon` organization.
- **Badges**: Only enforce badge-specific rules if the badge is claimed (see `pr_compliance_checklist.yaml` for details).

### Agent-Specific Workflows
When operating as an agent (e.g., Hermes Agent) in this repository:
1. Load relevant skills before acting (e.g., `qodo-code-review`, `hermes-agent`, `software-development`).
2. Use the `
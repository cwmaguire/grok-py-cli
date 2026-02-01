# UV Best Practices for LLMs

## Overview
UV is a fast Python package installer and resolver, written in Rust. It manages virtual environments and dependencies efficiently. As an LLM, when running UV commands, follow these practices to avoid failures and ensure smooth execution.

## Key Commands
- `uv sync`: Sync dependencies from `pyproject.toml` or `uv.lock`.
- `uv run <command>`: Run a command in the project's virtual environment.
- `uv add <package>`: Add a package to dependencies.
- `uv remove <package>`: Remove a package.
- `uv lock`: Update the lockfile.
- `uv venv`: Create a virtual environment.

## Best Practices
1. **Always check if UV is installed**: Run `uv --version` first. If not installed, install it via `curl -LsSf https://astral.sh/uv/install.sh | sh`.

2. **Use `uv run` for commands**: Instead of activating venv manually, use `uv run pytest` or `uv run python script.py` to run in the project's venv.

3. **Handle failures gracefully**:
   - If `uv run pytest` fails with "Command failed", check the exit code. Pytest fails if tests fail, so inspect the output.
   - Common issues: Missing dependencies (run `uv sync`), wrong Python version (uv uses the project's Python), or syntax errors in code.

4. **Sync before running**: Always run `uv sync` after adding/removing dependencies or cloning the repo.

5. **Specify Python version if needed**: Use `uv venv --python 3.11` to create venv with specific Python.

6. **Avoid mixing with pip**: Don't use raw pip; uv manages everything.

7. **For testing**: Use `uv run pytest` with options like `-v` for verbose, `--tb=short` for traceback.

## Instructions for Future LLMs/AIs

When working on this Grok CLI Python project, follow these guidelines to ensure efficient and error-free development:

### Tool Usage
- Use `view_file` to read files before editing; always check current contents to avoid conflicts.
- Use `str_replace_editor` for all file modifications (never `create_file` for existing files).
- Call tools one at a time in separate responses to avoid parsing errors.
- For complex tasks, create a `todo_list` first to plan steps, prioritizing high-priority items.
- Update `todo_list` status as you progress (pending → in_progress → completed).

### Testing Tasks
- Prioritize fixing todos listed in `test_progress.md` before implementing new tests.
- For acceptance tests in `test_user_scenarios.py`, common fixes include:
  - Making tests async with `@pytest.mark.asyncio` and `await` for async tool calls.
  - Correcting patch paths (e.g., use `'grok_py.grok.client.GrokClient'` instead of `'grok_py.cli.GrokClient'`).
- Run tests with `uv run pytest <path> -v` to verify fixes.
- Ensure `uv sync` has been run to install all dependencies from `pyproject.toml` before running tests.
- Verify that pytest is included in the dev dependencies and properly installed.
- If `uv run` fails, try running pytest directly after activating the virtual environment (e.g., `uv run python -m pytest`).
- Check for any environment-specific issues, such as missing system packages or incorrect Python versions.
- After completing a task, add a descriptive line to the "completed" section in `test_progress.md` and remove from "todo" if applicable.

### General Best Practices
- Always use `uv run` for Python commands (e.g., `uv run pytest` instead of raw `pytest`).
- When encountering async/sync mismatches in tests, check if the tool inherits from `AsyncTool` (use `await tool.execute(...)`) or `SyncTool` (use `tool.execute_sync(...)`).
- If a test fails due to import or mock issues, verify patch paths match actual import statements in the code.
- Keep responses concise; explain actions briefly without unnecessary pleasantries.
- If user confirmation is required for operations (e.g., file edits), wait for approval before proceeding.

8. **Troubleshooting**:
   - If "spawn rg ENOENT", rg (ripgrep) isn't installed; install it or use alternatives.
   - For async issues, ensure pytest-asyncio is configured.
   - If patches fail in tests, check import paths for mocking.

9. **Performance**: UV is fast, but for large projects, sync once and reuse the venv.

10. **Documentation**: Refer to https://docs.astral.sh/uv/ for full docs.

By following these, LLMs can execute UV commands reliably.
"""CLI entry point for grok-py."""

import sys
from pathlib import Path

# Add the project root to Python path for development
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from grok_py.cli import main

if __name__ == "__main__":
    main()
"""Path setup for AI layer tests."""
import sys
from pathlib import Path

# Add .claude/tools to import path so tests can import chain_manager, second_opinion
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

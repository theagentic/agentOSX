"""
Test Command - Run test suites
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional

from agentosx.cli.utils import success, error, info, warning, find_agent_path
from rich.console import Console

console = Console()


def run_tests(agent: Optional[str], suite: str, coverage: bool, verbose: bool):
    """
    Run test suites.
    
    Args:
        agent: Agent to test (all if None)
        suite: Test suite type
        coverage: Generate coverage report
        verbose: Verbose output
    """
    # Build pytest command
    cmd = ["pytest"]
    
    # Add test path
    if agent:
        agent_path = find_agent_path(agent)
        if not agent_path:
            error(f"Agent not found: {agent}")
        
        test_path = agent_path / "tests"
        if not test_path.exists():
            warning(f"No tests directory found in {agent_path}")
            return
        
        cmd.append(str(test_path))
    else:
        cmd.append("tests/")
    
    # Add suite filter
    if suite != "all":
        if suite == "unit":
            cmd.extend(["-m", "unit"])
        elif suite == "integration":
            cmd.extend(["-m", "integration"])
        elif suite == "e2e":
            cmd.extend(["-m", "e2e"])
    
    # Add coverage
    if coverage:
        cmd.extend([
            "--cov=agentosx",
            "--cov-report=html",
            "--cov-report=term",
        ])
    
    # Add verbosity
    if verbose:
        cmd.append("-vv")
    else:
        cmd.append("-v")
    
    # Add other options
    cmd.extend([
        "--tb=short",
        "--color=yes",
    ])
    
    info(f"Running {suite} tests...")
    if coverage:
        info("Coverage reporting enabled")
    
    # Run pytest
    try:
        result = subprocess.run(cmd, check=False)
        
        if result.returncode == 0:
            success("All tests passed!")
            
            if coverage:
                info("Coverage report generated at htmlcov/index.html")
        else:
            error("Some tests failed", exit_code=0)
            sys.exit(result.returncode)
    
    except FileNotFoundError:
        error("pytest not found. Install with: pip install pytest pytest-cov pytest-asyncio")
    except Exception as e:
        error(f"Test execution failed: {e}")

"""
Test fixtures for AgentOSX tests.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def sample_agent_yaml():
    """Sample agent YAML definition."""
    return """
name: test-agent
version: 1.0.0
persona:
  instructions: |
    You are a helpful test agent.
llm:
  provider: openai
  model: gpt-4
  temperature: 0.7
tools:
  - name: test_tool
    description: A test tool
memory:
  type: sqlite
  config:
    path: ./memory.db
"""


@pytest.fixture
def sample_agent_py():
    """Sample agent Python code."""
    return '''
from agentosx.agents.base import Agent

class TestAgent(Agent):
    """A simple test agent."""
    
    async def process(self, input_text: str) -> str:
        """Process input and return response."""
        return f"Echo: {input_text}"
    
    async def stream(self, input_text: str):
        """Stream response."""
        words = input_text.split()
        for word in words:
            yield {"type": "text", "text": word + " "}
'''


@pytest.fixture
def temp_agent_dir(tmp_path, sample_agent_yaml, sample_agent_py):
    """Create a temporary agent directory with files."""
    agent_dir = tmp_path / "test-agent"
    agent_dir.mkdir()
    
    # Write YAML
    (agent_dir / "agent.yaml").write_text(sample_agent_yaml)
    
    # Write Python
    (agent_dir / "agent.py").write_text(sample_agent_py)
    
    return agent_dir


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider."""
    mock = AsyncMock()
    mock.generate.return_value = "Mocked response"
    mock.stream.return_value = [
        {"type": "text", "text": "Mocked "},
        {"type": "text", "text": "streaming "},
        {"type": "text", "text": "response"}
    ]
    return mock


@pytest.fixture
def mock_mcp_server():
    """Mock MCP server."""
    mock = MagicMock()
    mock.list_tools.return_value = [
        {"name": "test_tool", "description": "A test tool"}
    ]
    mock.call_tool.return_value = {"result": "success"}
    return mock


@pytest.fixture
def test_dataset():
    """Sample test dataset."""
    return [
        {
            "input": "Hello",
            "expected": "Hi there!",
            "category": "greeting"
        },
        {
            "input": "What is 2+2?",
            "expected": "4",
            "category": "math"
        },
        {
            "input": "Tell me a joke",
            "expected": None,  # No exact match expected
            "category": "entertainment"
        }
    ]


@pytest.fixture
async def started_agent(temp_agent_dir):
    """A started agent instance."""
    # TODO: Import actual agent class and start it
    # For now return mock
    mock = AsyncMock()
    mock.name = "test-agent"
    mock.status.value = "running"
    return mock

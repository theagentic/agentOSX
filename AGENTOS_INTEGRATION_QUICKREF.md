# AgentOS Integration Quick Reference

## Installation

```bash
pip install httpx python-socketio[client]
```

## 1. REST API Client

### Basic Usage
```python
from agentosx.integrations.agentos import AgentOSClient

async with AgentOSClient("http://localhost:5000", api_key="...") as client:
    # Execute command
    result = await client.execute_command("twitter post Hello!")
    
    # Check status
    status = await client.get_system_status()
    
    # Poll messages
    messages = await client.poll_messages()
```

### WebSocket Connection
```python
async def handle_log(data):
    print(f"[{data['agent']}] {data['message']}")

await client.connect_websocket(on_execution_log=handle_log)
```

## 2. State Synchronization

### Push/Pull State
```python
from agentosx.integrations.agentos import StateSynchronizer

sync = StateSynchronizer(client)

# Push
await sync.push_agent_state(agent_state)

# Pull
state = await sync.pull_agent_state("agent_id")

# Continuous sync (every 30s)
await sync.start_continuous_sync([agent_state], interval=30)
```

## 3. Deployment

### Deploy Agent
```python
from agentosx.integrations.agentos import DeploymentManager

deployer = DeploymentManager(client)

result = await deployer.deploy_agent(
    agent_dir="agents/my_agent",
    agent_id="my_agent",
    verify=True,
    rollback_on_failure=True,
)
```

### Check Status & Rollback
```python
# Status
status = await deployer.get_deployment_status("my_agent")

# Rollback
await deployer.rollback_deployment("my_agent")

# Undeploy
await deployer.undeploy_agent("my_agent")
```

## 4. Event Subscription

### Subscribe to Events
```python
from agentosx.integrations.agentos import EventSubscriber

subscriber = EventSubscriber(client)

@subscriber.on("execution_log")
async def handle_log(data):
    print(data)

await subscriber.start()
```

### Subscribe to Specific Agent
```python
await subscriber.subscribe_to_agent(
    "twitter_bot",
    handler=my_handler,
)
```

## 5. Built-in Tools

### AgentOS Operations
```python
from agentosx.tools.builtin.agentos import AgentOSTools

tools = AgentOSTools()

# List agents
agents = await tools.list_agents()

# Trigger agent
result = await tools.trigger_agent("twitter_bot", "post Hello!")

# Get logs
logs = await tools.get_execution_logs("twitter_bot", limit=50)

# Manage secrets
await tools.manage_secrets("set", "API_KEY", "value")
await tools.manage_secrets("get", "API_KEY")
await tools.manage_secrets("delete", "API_KEY")
await tools.manage_secrets("list", "")

# Search marketplace
agents = await tools.query_marketplace({"category": "social"})

# Install agent
await tools.install_agent("twitter_bot", version="1.2.0")
```

## 6. Marketplace

### Search & Discovery
```python
from agentosx.marketplace import RegistryClient

registry = RegistryClient("https://marketplace.agentos.dev")

# Search
results = await registry.search(
    query="automation",
    category="productivity",
    tags=["scheduling"],
    limit=20,
)

# Get agent details
agent = await registry.get_agent("twitter_bot")

# Get versions
versions = await registry.get_agent_versions("twitter_bot")

# Featured agents
featured = await registry.get_featured_agents(limit=10)

# Check compatibility
compat = await registry.check_compatibility("twitter_bot", "0.1.0")
```

### Publishing
```python
from agentosx.marketplace import AgentPublisher

publisher = AgentPublisher(
    registry_url="https://marketplace.agentos.dev",
    api_key="your_api_key",
)

# Dry run (validation only)
result = await publisher.publish_agent(
    agent_dir="agents/my_agent",
    version="1.0.0",
    dry_run=True,
)

# Publish
result = await publisher.publish_agent(
    agent_dir="agents/my_agent",
    version="1.0.0",
)
```

### Installation
```python
from agentosx.marketplace import AgentInstaller
from pathlib import Path

installer = AgentInstaller(agents_dir=Path("agents"))

# Install
result = await installer.install_agent(
    "twitter_bot",
    version="1.2.0",
    install_dependencies=True,
)

# Update
result = await installer.update_agent("twitter_bot")

# Uninstall
result = await installer.uninstall_agent("twitter_bot")

# List installed
installed = await installer.list_installed()
```

## 7. Version Management

### Version Comparison
```python
from agentosx.marketplace import Version, VersionManager

v1 = Version("1.2.3")
v2 = Version("1.2.4")

assert v2 > v1
assert v1.is_compatible_with(v2)
assert v1.bump_patch() == Version("1.2.4")
```

### Version Resolution
```python
manager = VersionManager()

versions = ["1.0.0", "1.1.0", "1.2.0", "2.0.0"]

# Latest
latest = manager.find_latest(versions)  # "2.0.0"

# Latest compatible with 1.0.0
compat = manager.find_latest_compatible("1.0.0", versions)  # "1.2.0"

# Upgrade path
path = manager.get_upgrade_path("1.0.0", "2.0.0", versions)
# ["1.1.0", "1.2.0", "2.0.0"]

# Sort
sorted_versions = manager.sort_versions(versions, reverse=True)
```

## 8. Error Handling

### Retry Logic
```python
client = AgentOSClient(
    max_retries=5,          # 5 retry attempts
    retry_delay=2.0,        # 2s initial delay
    timeout=60.0,           # 60s timeout
)
```

### Conflict Resolution
```python
sync = StateSynchronizer(
    client,
    conflict_resolution="last_write_wins",  # or "merge", "manual"
)

try:
    await sync.push_agent_state(agent_state)
except SyncConflictError as e:
    # Handle conflict
    resolved = await sync.resolve_conflict(
        agent_id,
        local_state,
        remote_state,
    )
```

## 9. AgentOS API Endpoints

### REST Endpoints
```
POST   /command                           - Execute command
GET    /debug/status                      - System status
GET    /<agent>/status                    - Agent status
POST   /register                          - Register client
GET    /poll                              - Poll messages
GET    /stream_updates                    - Stream updates
GET    /api/natural_language/model_info   - NLP config
POST   /api/natural_language/set_provider - Set provider
POST   /api/natural_language/set_model    - Set model
GET    /api/natural_language/health_check - Health check
```

### WebSocket Events
```
connect         - Connection established
disconnect      - Connection lost
execution_log   - Execution logs
message         - Generic messages
```

## 10. Configuration

### Environment Variables
```bash
# AgentOS Backend
AGENTOS_URL=http://localhost:5000
AGENTOS_API_KEY=your_api_key

# Marketplace
MARKETPLACE_URL=https://marketplace.agentos.dev
MARKETPLACE_API_KEY=your_api_key

# Deployment
DEPLOYMENT_DIR=~/.agentosx/deployments
AGENTS_DIR=./agents
```

### Client Configuration
```python
client = AgentOSClient(
    base_url="http://localhost:5000",
    api_key="your_api_key",
    client_id="custom_client_id",
    max_retries=3,
    retry_delay=1.0,
    timeout=30.0,
)
```

## Complete Example

```python
import asyncio
from pathlib import Path
from agentosx.integrations.agentos import (
    AgentOSClient,
    DeploymentManager,
    EventSubscriber,
)
from agentosx.marketplace import AgentInstaller

async def main():
    # Initialize client
    async with AgentOSClient("http://localhost:5000") as client:
        # Deploy agent
        deployer = DeploymentManager(client)
        await deployer.deploy_agent(
            agent_dir="agents/twitter_bot",
            agent_id="twitter_bot",
        )
        
        # Subscribe to events
        subscriber = EventSubscriber(client)
        
        @subscriber.on("execution_log")
        async def handle_log(data):
            print(f"[{data['agent']}] {data['message']}")
        
        await subscriber.start()
        
        # Install from marketplace
        installer = AgentInstaller(agents_dir=Path("agents"))
        await installer.install_agent("autoblog", version="1.0.0")
        
        # Keep running
        await asyncio.sleep(3600)  # Run for 1 hour

if __name__ == "__main__":
    asyncio.run(main())
```

## Troubleshooting

### Connection Issues
```python
# Check agentOS is running
import httpx
response = await httpx.get("http://localhost:5000/debug/status")
print(response.json())

# Test WebSocket
await client.connect_websocket()
print(client.is_websocket_connected)  # Should be True
```

### Deployment Failures
```python
# Check deployment status
status = await deployer.get_deployment_status("agent_id")
print(status["health"])

# View deployment history
deployments = await deployer.list_deployments()
print(deployments)

# Manual rollback
await deployer.rollback_deployment("agent_id")
```

### Marketplace Issues
```python
# Verify package
is_valid = await installer.verify_package(
    package_path,
    expected_checksum,
)

# Check compatibility
compat = await registry.check_compatibility("agent_id", "0.1.0")
print(compat["compatible"])
```

## Best Practices

1. **Always use async context managers:**
   ```python
   async with AgentOSClient(...) as client:
       # Your code
   ```

2. **Handle conflicts gracefully:**
   ```python
   try:
       await sync.push_agent_state(state)
   except SyncConflictError:
       # Resolve conflict
   ```

3. **Verify deployments:**
   ```python
   await deployer.deploy_agent(..., verify=True, rollback_on_failure=True)
   ```

4. **Use continuous sync for long-running agents:**
   ```python
   await sync.start_continuous_sync([agent_state], interval=30)
   ```

5. **Clean up resources:**
   ```python
   await sync.stop_continuous_sync()
   await subscriber.stop()
   await client.close()
   ```

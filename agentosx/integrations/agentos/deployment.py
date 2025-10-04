"""
AgentOS Deployment Manager

Provides one-click deployment workflow for deploying agentOSX agents
to the agentOS platform.
"""

import asyncio
import io
import json
import logging
import os
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from .client import AgentOSClient

logger = logging.getLogger(__name__)


class DeploymentError(Exception):
    """Raised when deployment fails."""
    pass


class DeploymentManager:
    """
    One-click deployment to agentOS platform.
    
    Handles complete deployment workflow:
    1. Bundle agent code + dependencies
    2. Upload to agentOS
    3. Health check verification
    4. Rollback support on failure
    
    Example:
        ```python
        client = AgentOSClient("http://localhost:5000")
        deployer = DeploymentManager(client)
        
        # Deploy agent
        result = await deployer.deploy_agent(
            agent_dir="agents/my_agent",
            agent_id="my_agent",
        )
        
        # Check deployment status
        status = await deployer.get_deployment_status("my_agent")
        
        # Rollback if needed
        if status["health"] != "healthy":
            await deployer.rollback_deployment("my_agent")
        ```
    """
    
    def __init__(
        self,
        client: AgentOSClient,
        deployments_dir: Optional[Path] = None,
    ):
        """
        Initialize deployment manager.
        
        Args:
            client: AgentOS client for API communication
            deployments_dir: Directory to store deployment artifacts
                             (default: ~/.agentosx/deployments)
        """
        self.client = client
        self.deployments_dir = deployments_dir or (
            Path.home() / ".agentosx" / "deployments"
        )
        self.deployments_dir.mkdir(parents=True, exist_ok=True)
        
        # Track deployments
        self._deployments: Dict[str, Dict[str, Any]] = {}
        self._load_deployment_history()
        
        logger.info(f"Initialized DeploymentManager (deployments_dir={self.deployments_dir})")
    
    def _load_deployment_history(self) -> None:
        """Load deployment history from disk."""
        history_file = self.deployments_dir / "history.json"
        if history_file.exists():
            try:
                with open(history_file, "r") as f:
                    self._deployments = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load deployment history: {e}")
    
    def _save_deployment_history(self) -> None:
        """Save deployment history to disk."""
        history_file = self.deployments_dir / "history.json"
        try:
            with open(history_file, "w") as f:
                json.dump(self._deployments, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save deployment history: {e}")
    
    async def bundle_agent(
        self,
        agent_dir: Path,
        agent_id: str,
        include_dependencies: bool = True,
    ) -> Path:
        """
        Bundle agent code and dependencies into a tar.gz archive.
        
        Args:
            agent_dir: Path to agent directory
            agent_id: Agent ID
            include_dependencies: Include requirements.txt dependencies
            
        Returns:
            Path to bundle archive
            
        Raises:
            DeploymentError: If bundling fails
        """
        agent_dir = Path(agent_dir)
        if not agent_dir.exists():
            raise DeploymentError(f"Agent directory not found: {agent_dir}")
        
        # Create bundle directory
        bundle_dir = self.deployments_dir / agent_id / "bundle"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy agent files
        agent_bundle = bundle_dir / "agent"
        if agent_bundle.exists():
            shutil.rmtree(agent_bundle)
        shutil.copytree(agent_dir, agent_bundle)
        
        # Create manifest
        manifest = {
            "agent_id": agent_id,
            "version": "1.0.0",  # TODO: Get from agent metadata
            "entry_point": "agent.py",
            "required_files": [
                "agent.py",
                "agent.yaml",
            ],
        }
        
        manifest_file = bundle_dir / "manifest.json"
        with open(manifest_file, "w") as f:
            json.dump(manifest, f, indent=2)
        
        # Bundle dependencies if requested
        if include_dependencies:
            requirements_file = agent_dir / "requirements.txt"
            if requirements_file.exists():
                shutil.copy(requirements_file, bundle_dir / "requirements.txt")
        
        # Create tar.gz archive
        bundle_path = self.deployments_dir / agent_id / f"{agent_id}.tar.gz"
        with tarfile.open(bundle_path, "w:gz") as tar:
            tar.add(bundle_dir, arcname=agent_id)
        
        logger.info(f"Created bundle for {agent_id}: {bundle_path}")
        return bundle_path
    
    async def upload_bundle(
        self,
        agent_id: str,
        bundle_path: Path,
    ) -> Dict[str, Any]:
        """
        Upload agent bundle to agentOS.
        
        Args:
            agent_id: Agent ID
            bundle_path: Path to bundle archive
            
        Returns:
            Upload response dict
            
        Raises:
            DeploymentError: If upload fails
        """
        if not bundle_path.exists():
            raise DeploymentError(f"Bundle not found: {bundle_path}")
        
        # Read bundle
        with open(bundle_path, "rb") as f:
            bundle_data = f.read()
        
        # Encode as base64 for JSON transport
        import base64
        bundle_b64 = base64.b64encode(bundle_data).decode()
        
        # Upload via command
        command = f"agentosx deploy {agent_id} {bundle_b64}"
        response = await self.client.execute_command(command)
        
        if response.get("status") != "success":
            raise DeploymentError(f"Upload failed: {response.get('message')}")
        
        logger.info(f"Uploaded bundle for {agent_id}")
        return response
    
    async def verify_deployment(
        self,
        agent_id: str,
        timeout: int = 30,
    ) -> bool:
        """
        Verify deployment with health checks.
        
        Args:
            agent_id: Agent ID
            timeout: Health check timeout in seconds
            
        Returns:
            True if deployment is healthy
        """
        try:
            # Wait for agent to start
            await asyncio.sleep(2)
            
            # Check agent status
            status = await self.client.get_agent_status(agent_id)
            
            if status.get("health") == "healthy":
                logger.info(f"Deployment verification passed for {agent_id}")
                return True
            else:
                logger.error(f"Deployment verification failed for {agent_id}: {status}")
                return False
        
        except Exception as e:
            logger.error(f"Deployment verification error for {agent_id}: {e}")
            return False
    
    async def deploy_agent(
        self,
        agent_dir: Path,
        agent_id: str,
        verify: bool = True,
        rollback_on_failure: bool = True,
    ) -> Dict[str, Any]:
        """
        Deploy agent to agentOS (complete workflow).
        
        Steps:
        1. Bundle agent code and dependencies
        2. Upload bundle to agentOS
        3. Verify deployment with health checks
        4. Rollback on failure (optional)
        
        Args:
            agent_dir: Path to agent directory
            agent_id: Agent ID
            verify: Verify deployment with health checks
            rollback_on_failure: Rollback on verification failure
            
        Returns:
            Deployment result dict
            
        Raises:
            DeploymentError: If deployment fails
        """
        logger.info(f"Starting deployment for {agent_id}")
        
        try:
            # Step 1: Bundle agent
            bundle_path = await self.bundle_agent(agent_dir, agent_id)
            
            # Step 2: Upload bundle
            upload_response = await self.upload_bundle(agent_id, bundle_path)
            
            # Step 3: Verify deployment
            if verify:
                healthy = await self.verify_deployment(agent_id)
                
                if not healthy:
                    if rollback_on_failure:
                        logger.warning(f"Deployment verification failed, rolling back {agent_id}")
                        await self.rollback_deployment(agent_id)
                        raise DeploymentError("Deployment verification failed, rolled back")
                    else:
                        raise DeploymentError("Deployment verification failed")
            
            # Record deployment
            self._deployments[agent_id] = {
                "agent_id": agent_id,
                "bundle_path": str(bundle_path),
                "deployed_at": asyncio.get_event_loop().time(),
                "status": "deployed",
            }
            self._save_deployment_history()
            
            logger.info(f"Successfully deployed {agent_id}")
            return {
                "status": "success",
                "agent_id": agent_id,
                "message": "Deployment successful",
            }
        
        except Exception as e:
            logger.error(f"Deployment failed for {agent_id}: {e}")
            raise DeploymentError(f"Deployment failed: {e}")
    
    async def get_deployment_status(
        self,
        agent_id: str,
    ) -> Dict[str, Any]:
        """
        Get deployment status for an agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Status dict with health, version, and metadata
        """
        try:
            status = await self.client.get_agent_status(agent_id)
            return status
        except Exception as e:
            logger.error(f"Failed to get deployment status for {agent_id}: {e}")
            return {
                "status": "error",
                "error": str(e),
            }
    
    async def rollback_deployment(
        self,
        agent_id: str,
        to_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Rollback deployment to previous version.
        
        Args:
            agent_id: Agent ID
            to_version: Version to rollback to (default: previous)
            
        Returns:
            Rollback result dict
        """
        logger.info(f"Rolling back deployment for {agent_id}")
        
        # Send rollback command
        command = f"agentosx rollback {agent_id}"
        if to_version:
            command += f" --version {to_version}"
        
        response = await self.client.execute_command(command)
        
        if response.get("status") == "success":
            logger.info(f"Rolled back deployment for {agent_id}")
        else:
            logger.error(f"Rollback failed for {agent_id}: {response}")
        
        return response
    
    async def list_deployments(self) -> List[Dict[str, Any]]:
        """
        List all deployed agents.
        
        Returns:
            List of deployment dicts
        """
        return list(self._deployments.values())
    
    async def undeploy_agent(
        self,
        agent_id: str,
    ) -> Dict[str, Any]:
        """
        Undeploy (remove) agent from agentOS.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Undeploy result dict
        """
        logger.info(f"Undeploying {agent_id}")
        
        # Send undeploy command
        command = f"agentosx undeploy {agent_id}"
        response = await self.client.execute_command(command)
        
        if response.get("status") == "success":
            # Remove from deployment history
            if agent_id in self._deployments:
                del self._deployments[agent_id]
                self._save_deployment_history()
            
            logger.info(f"Undeployed {agent_id}")
        else:
            logger.error(f"Undeploy failed for {agent_id}: {response}")
        
        return response

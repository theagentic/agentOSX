"""
Agent Installer

Downloads and installs agents from the marketplace.
"""

import hashlib
import json
import logging
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from .registry import RegistryClient

logger = logging.getLogger(__name__)


class InstallError(Exception):
    """Raised when installation fails."""
    pass


class AgentInstaller:
    """
    Installer for marketplace agents.
    
    Handles:
    - Downloading agent packages
    - Verifying checksums
    - Resolving dependencies
    - Local installation
    - Post-install configuration
    
    Example:
        ```python
        installer = AgentInstaller(
            agents_dir=Path("agents"),
            registry_url="https://marketplace.agentos.dev",
        )
        
        # Install agent
        result = await installer.install_agent("twitter_bot", version="1.2.0")
        
        # Install with dependencies
        result = await installer.install_agent(
            "autoblog",
            install_dependencies=True,
        )
        ```
    """
    
    def __init__(
        self,
        agents_dir: Path,
        registry_url: str = "https://marketplace.agentos.dev",
        timeout: float = 60.0,
    ):
        """
        Initialize agent installer.
        
        Args:
            agents_dir: Directory to install agents to
            registry_url: Marketplace registry URL
            timeout: Download timeout in seconds
        """
        self.agents_dir = Path(agents_dir)
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        
        self.registry = RegistryClient(registry_url, timeout)
        self.http_client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))
        
        # Track installed agents
        self._installed = self._load_installed_agents()
        
        logger.info(f"Initialized AgentInstaller (agents_dir={agents_dir})")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self):
        """Close connections."""
        await self.registry.close()
        await self.http_client.aclose()
    
    def _load_installed_agents(self) -> Dict[str, Dict[str, Any]]:
        """Load installed agents registry."""
        registry_file = self.agents_dir / ".installed.json"
        if registry_file.exists():
            try:
                with open(registry_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load installed agents registry: {e}")
        return {}
    
    def _save_installed_agents(self) -> None:
        """Save installed agents registry."""
        registry_file = self.agents_dir / ".installed.json"
        try:
            with open(registry_file, "w") as f:
                json.dump(self._installed, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save installed agents registry: {e}")
    
    async def download_package(
        self,
        agent_id: str,
        version: Optional[str] = None,
    ) -> Path:
        """
        Download agent package from registry.
        
        Args:
            agent_id: Agent ID
            version: Specific version (optional, defaults to latest)
            
        Returns:
            Path to downloaded package
            
        Raises:
            InstallError: If download fails
        """
        # Get download URL
        download_url = await self.registry.get_download_url(agent_id, version)
        if not download_url:
            raise InstallError(f"Failed to get download URL for {agent_id}")
        
        # Download package
        logger.info(f"Downloading {agent_id} from {download_url}")
        
        try:
            response = await self.http_client.get(download_url)
            response.raise_for_status()
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(
                mode="wb", delete=False, suffix=".tar.gz"
            ) as f:
                f.write(response.content)
                package_path = Path(f.name)
            
            logger.info(f"Downloaded {agent_id} to {package_path}")
            return package_path
        
        except Exception as e:
            raise InstallError(f"Failed to download {agent_id}: {e}")
    
    async def verify_package(
        self,
        package_path: Path,
        expected_checksum: Optional[str] = None,
    ) -> bool:
        """
        Verify package integrity with checksums.
        
        Args:
            package_path: Path to package file
            expected_checksum: Expected SHA256 checksum (optional)
            
        Returns:
            True if package is valid
        """
        if not expected_checksum:
            logger.warning("No checksum provided, skipping verification")
            return True
        
        # Compute SHA256 checksum
        with open(package_path, "rb") as f:
            sha256_hash = hashlib.sha256(f.read()).hexdigest()
        
        if sha256_hash != expected_checksum:
            logger.error(
                f"Checksum mismatch: expected {expected_checksum}, got {sha256_hash}"
            )
            return False
        
        logger.info("Package checksum verified")
        return True
    
    async def extract_package(
        self,
        package_path: Path,
        extract_dir: Path,
    ) -> Path:
        """
        Extract agent package.
        
        Args:
            package_path: Path to package archive
            extract_dir: Directory to extract to
            
        Returns:
            Path to extracted agent directory
        """
        extract_dir = Path(extract_dir)
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract tar.gz
        with tarfile.open(package_path, "r:gz") as tar:
            tar.extractall(extract_dir)
        
        # Find agent directory (should be single top-level directory)
        extracted_items = list(extract_dir.iterdir())
        if len(extracted_items) == 1 and extracted_items[0].is_dir():
            agent_dir = extracted_items[0]
        else:
            # If multiple items, assume extract_dir is the agent directory
            agent_dir = extract_dir
        
        logger.info(f"Extracted package to {agent_dir}")
        return agent_dir
    
    async def install_dependencies(
        self,
        agent_dir: Path,
    ) -> bool:
        """
        Install agent dependencies from requirements.txt.
        
        Args:
            agent_dir: Path to agent directory
            
        Returns:
            True if dependencies installed successfully
        """
        requirements_file = agent_dir / "requirements.txt"
        if not requirements_file.exists():
            logger.info("No requirements.txt found, skipping dependencies")
            return True
        
        logger.info(f"Installing dependencies from {requirements_file}")
        
        try:
            import subprocess
            
            subprocess.run(
                ["pip", "install", "-r", str(requirements_file)],
                check=True,
                capture_output=True,
            )
            logger.info("Dependencies installed successfully")
            return True
        
        except Exception as e:
            logger.error(f"Failed to install dependencies: {e}")
            return False
    
    async def install_agent(
        self,
        agent_id: str,
        version: Optional[str] = None,
        install_dependencies: bool = True,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Install agent from marketplace.
        
        Complete installation workflow.
        
        Args:
            agent_id: Agent ID to install
            version: Specific version (optional, defaults to latest)
            install_dependencies: Install requirements.txt dependencies
            force: Force reinstall if already installed
            
        Returns:
            Installation result dict
            
        Raises:
            InstallError: If installation fails
        """
        logger.info(f"Installing {agent_id} (version={version or 'latest'})")
        
        # Check if already installed
        if agent_id in self._installed and not force:
            installed_version = self._installed[agent_id]["version"]
            raise InstallError(
                f"{agent_id} is already installed (version {installed_version}). "
                "Use force=True to reinstall."
            )
        
        # Get agent metadata
        agent_meta = await self.registry.get_agent(agent_id)
        if not agent_meta:
            raise InstallError(f"Agent not found: {agent_id}")
        
        # Use specified version or latest
        if not version:
            version = agent_meta.get("version", "latest")
        
        try:
            # Step 1: Download package
            package_path = await self.download_package(agent_id, version)
            
            # Step 2: Verify package
            expected_checksum = agent_meta.get("checksum")
            if not await self.verify_package(package_path, expected_checksum):
                raise InstallError("Package verification failed")
            
            # Step 3: Extract package
            with tempfile.TemporaryDirectory() as temp_dir:
                agent_dir = await self.extract_package(package_path, Path(temp_dir))
                
                # Step 4: Install dependencies
                if install_dependencies:
                    if not await self.install_dependencies(agent_dir):
                        logger.warning("Failed to install dependencies, continuing anyway")
                
                # Step 5: Copy to agents directory
                target_dir = self.agents_dir / agent_id
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                
                shutil.copytree(agent_dir, target_dir)
            
            # Clean up downloaded package
            package_path.unlink()
            
            # Step 6: Record installation
            self._installed[agent_id] = {
                "agent_id": agent_id,
                "version": version,
                "installed_at": str(Path.cwd()),
                "metadata": agent_meta,
            }
            self._save_installed_agents()
            
            logger.info(f"Successfully installed {agent_id} v{version}")
            return {
                "status": "success",
                "agent_id": agent_id,
                "version": version,
                "path": str(target_dir),
            }
        
        except Exception as e:
            logger.error(f"Installation failed: {e}")
            raise InstallError(f"Installation failed: {e}")
    
    async def uninstall_agent(
        self,
        agent_id: str,
    ) -> Dict[str, Any]:
        """
        Uninstall agent.
        
        Args:
            agent_id: Agent ID to uninstall
            
        Returns:
            Uninstallation result dict
        """
        if agent_id not in self._installed:
            raise InstallError(f"Agent not installed: {agent_id}")
        
        logger.info(f"Uninstalling {agent_id}")
        
        # Remove agent directory
        agent_dir = self.agents_dir / agent_id
        if agent_dir.exists():
            shutil.rmtree(agent_dir)
        
        # Remove from installed registry
        del self._installed[agent_id]
        self._save_installed_agents()
        
        logger.info(f"Successfully uninstalled {agent_id}")
        return {
            "status": "success",
            "agent_id": agent_id,
        }
    
    async def list_installed(self) -> List[Dict[str, Any]]:
        """
        List installed agents.
        
        Returns:
            List of installed agent dicts
        """
        return list(self._installed.values())
    
    async def update_agent(
        self,
        agent_id: str,
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update agent to newer version.
        
        Args:
            agent_id: Agent ID to update
            version: Target version (optional, defaults to latest)
            
        Returns:
            Update result dict
        """
        if agent_id not in self._installed:
            raise InstallError(f"Agent not installed: {agent_id}")
        
        current_version = self._installed[agent_id]["version"]
        logger.info(f"Updating {agent_id} from {current_version} to {version or 'latest'}")
        
        # Install new version (force=True to overwrite)
        return await self.install_agent(agent_id, version, force=True)

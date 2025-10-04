"""
Agent Publisher

Handles validation and publishing of agents to the marketplace.
"""

import hashlib
import json
import logging
import tarfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import yaml

logger = logging.getLogger(__name__)


class PublishError(Exception):
    """Raised when publishing fails."""
    pass


class AgentPublisher:
    """
    Publisher for agentOS marketplace.
    
    Provides validation pipeline and publishing workflow for agents.
    
    Steps:
    1. Validate agent structure and metadata
    2. Run security checks
    3. Package agent with checksums
    4. Upload to marketplace registry
    5. Generate documentation
    
    Example:
        ```python
        publisher = AgentPublisher(
            registry_url="https://marketplace.agentos.dev",
            api_key="your_api_key",
        )
        
        result = await publisher.publish_agent(
            agent_dir="agents/my_agent",
            version="1.0.0",
        )
        ```
    """
    
    def __init__(
        self,
        registry_url: str = "https://marketplace.agentos.dev",
        api_key: Optional[str] = None,
        timeout: float = 60.0,
    ):
        """
        Initialize agent publisher.
        
        Args:
            registry_url: Marketplace registry URL
            api_key: API key for authentication
            timeout: Request timeout in seconds
        """
        self.registry_url = registry_url.rstrip("/")
        self.api_key = api_key
        self.http_client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))
        
        logger.info(f"Initialized AgentPublisher for {registry_url}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers with authentication."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    async def validate_agent_structure(
        self,
        agent_dir: Path,
    ) -> Dict[str, Any]:
        """
        Validate agent directory structure.
        
        Checks for required files and valid structure.
        
        Args:
            agent_dir: Path to agent directory
            
        Returns:
            Validation result dict with is_valid and errors list
        """
        agent_dir = Path(agent_dir)
        errors = []
        warnings = []
        
        # Check required files
        required_files = ["agent.py", "agent.yaml"]
        for file in required_files:
            file_path = agent_dir / file
            if not file_path.exists():
                errors.append(f"Missing required file: {file}")
        
        # Check agent.yaml structure
        agent_yaml = agent_dir / "agent.yaml"
        if agent_yaml.exists():
            try:
                with open(agent_yaml, "r") as f:
                    config = yaml.safe_load(f)
                
                # Validate required fields
                required_fields = ["name", "version", "description"]
                for field in required_fields:
                    if field not in config:
                        errors.append(f"Missing required field in agent.yaml: {field}")
            
            except Exception as e:
                errors.append(f"Invalid agent.yaml: {e}")
        
        # Check for README
        readme_path = agent_dir / "README.md"
        if not readme_path.exists():
            warnings.append("Missing README.md (recommended)")
        
        # Check for LICENSE
        license_path = agent_dir / "LICENSE"
        if not license_path.exists():
            warnings.append("Missing LICENSE file (recommended)")
        
        is_valid = len(errors) == 0
        
        return {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
        }
    
    async def validate_metadata(
        self,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate agent metadata.
        
        Args:
            metadata: Agent metadata dict
            
        Returns:
            Validation result dict
        """
        errors = []
        warnings = []
        
        # Required fields
        required_fields = [
            "name",
            "version",
            "description",
            "author",
            "license",
        ]
        
        for field in required_fields:
            if field not in metadata:
                errors.append(f"Missing required metadata field: {field}")
        
        # Validate version format (semantic versioning)
        if "version" in metadata:
            version = metadata["version"]
            parts = version.split(".")
            if len(parts) != 3:
                errors.append(f"Invalid version format: {version}. Expected: X.Y.Z")
            else:
                try:
                    [int(p) for p in parts]
                except ValueError:
                    errors.append(f"Invalid version format: {version}. Expected integers")
        
        # Validate description length
        if "description" in metadata:
            if len(metadata["description"]) < 10:
                warnings.append("Description is too short (< 10 characters)")
            elif len(metadata["description"]) > 500:
                warnings.append("Description is too long (> 500 characters)")
        
        # Validate tags
        if "tags" in metadata:
            if not isinstance(metadata["tags"], list):
                errors.append("Tags must be a list")
            elif len(metadata["tags"]) > 10:
                warnings.append("Too many tags (max 10 recommended)")
        
        is_valid = len(errors) == 0
        
        return {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
        }
    
    async def run_security_checks(
        self,
        agent_dir: Path,
    ) -> Dict[str, Any]:
        """
        Run security checks on agent code.
        
        Args:
            agent_dir: Path to agent directory
            
        Returns:
            Security check result dict
        """
        issues = []
        warnings = []
        
        # Check for common security issues
        agent_py = agent_dir / "agent.py"
        if agent_py.exists():
            with open(agent_py, "r") as f:
                code = f.read()
            
            # Check for hardcoded secrets
            import re
            
            secret_patterns = [
                r'api_key\s*=\s*["\'][\w-]{20,}["\']',
                r'password\s*=\s*["\'][\w-]+["\']',
                r'token\s*=\s*["\'][\w-]{20,}["\']',
            ]
            
            for pattern in secret_patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    issues.append(
                        "Possible hardcoded secret detected. Use environment variables."
                    )
                    break
            
            # Check for eval/exec usage
            if "eval(" in code or "exec(" in code:
                warnings.append(
                    "Usage of eval() or exec() detected. This may be a security risk."
                )
            
            # Check for subprocess calls
            if "subprocess" in code:
                warnings.append(
                    "Subprocess usage detected. Ensure proper input validation."
                )
        
        is_secure = len(issues) == 0
        
        return {
            "is_secure": is_secure,
            "issues": issues,
            "warnings": warnings,
        }
    
    async def create_package(
        self,
        agent_dir: Path,
        output_dir: Path,
    ) -> Path:
        """
        Create agent package with checksums.
        
        Args:
            agent_dir: Path to agent directory
            output_dir: Output directory for package
            
        Returns:
            Path to package archive
        """
        agent_dir = Path(agent_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load metadata
        agent_yaml = agent_dir / "agent.yaml"
        with open(agent_yaml, "r") as f:
            metadata = yaml.safe_load(f)
        
        agent_id = metadata.get("name", "agent")
        version = metadata.get("version", "1.0.0")
        
        # Create package archive
        package_name = f"{agent_id}-{version}.tar.gz"
        package_path = output_dir / package_name
        
        with tarfile.open(package_path, "w:gz") as tar:
            tar.add(agent_dir, arcname=agent_id)
        
        # Compute checksums
        checksums = {}
        
        # SHA256 checksum
        with open(package_path, "rb") as f:
            sha256_hash = hashlib.sha256(f.read()).hexdigest()
            checksums["sha256"] = sha256_hash
        
        # MD5 checksum (for backward compatibility)
        with open(package_path, "rb") as f:
            md5_hash = hashlib.md5(f.read()).hexdigest()
            checksums["md5"] = md5_hash
        
        # Save checksums
        checksums_path = output_dir / f"{package_name}.checksums.json"
        with open(checksums_path, "w") as f:
            json.dump(checksums, f, indent=2)
        
        logger.info(f"Created package: {package_path}")
        return package_path
    
    async def publish_agent(
        self,
        agent_dir: Path,
        version: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Publish agent to marketplace.
        
        Complete publishing workflow with validation.
        
        Args:
            agent_dir: Path to agent directory
            version: Override version from agent.yaml (optional)
            dry_run: Validate only, don't publish
            
        Returns:
            Publish result dict
            
        Raises:
            PublishError: If publishing fails
        """
        agent_dir = Path(agent_dir)
        
        logger.info(f"Publishing agent from {agent_dir}")
        
        # Step 1: Validate structure
        structure_result = await self.validate_agent_structure(agent_dir)
        if not structure_result["is_valid"]:
            raise PublishError(
                f"Agent structure validation failed: {structure_result['errors']}"
            )
        
        # Step 2: Load and validate metadata
        agent_yaml = agent_dir / "agent.yaml"
        with open(agent_yaml, "r") as f:
            metadata = yaml.safe_load(f)
        
        if version:
            metadata["version"] = version
        
        metadata_result = await self.validate_metadata(metadata)
        if not metadata_result["is_valid"]:
            raise PublishError(
                f"Metadata validation failed: {metadata_result['errors']}"
            )
        
        # Step 3: Run security checks
        security_result = await self.run_security_checks(agent_dir)
        if not security_result["is_secure"]:
            raise PublishError(
                f"Security checks failed: {security_result['issues']}"
            )
        
        # Log warnings
        all_warnings = (
            structure_result.get("warnings", [])
            + metadata_result.get("warnings", [])
            + security_result.get("warnings", [])
        )
        for warning in all_warnings:
            logger.warning(warning)
        
        if dry_run:
            return {
                "status": "dry_run",
                "message": "Validation passed. Agent is ready to publish.",
                "validation": {
                    "structure": structure_result,
                    "metadata": metadata_result,
                    "security": security_result,
                },
            }
        
        # Step 4: Create package
        import tempfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            package_path = await self.create_package(agent_dir, Path(temp_dir))
            
            # Step 5: Upload to registry
            with open(package_path, "rb") as f:
                files = {"package": f}
                data = {"metadata": json.dumps(metadata)}
                
                response = await self.http_client.post(
                    f"{self.registry_url}/api/agents/publish",
                    files=files,
                    data=data,
                    headers={"Authorization": f"Bearer {self.api_key}"}
                    if self.api_key
                    else {},
                )
                response.raise_for_status()
                result = response.json()
        
        logger.info(f"Successfully published {metadata['name']} v{metadata['version']}")
        return result

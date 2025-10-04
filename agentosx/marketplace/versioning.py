"""
Version Management

Provides semantic versioning support for agent marketplace.
"""

import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class Version:
    """
    Semantic version representation.
    
    Follows semantic versioning spec (semver.org):
    - MAJOR.MINOR.PATCH format
    - Optional pre-release and build metadata
    
    Example:
        ```python
        v1 = Version("1.2.3")
        v2 = Version("1.2.4")
        
        assert v2 > v1
        assert v1.is_compatible_with(v2)
        ```
    """
    
    def __init__(self, version_str: str):
        """
        Initialize version from string.
        
        Args:
            version_str: Version string (e.g., "1.2.3", "2.0.0-beta.1")
        """
        self.original = version_str
        self.major, self.minor, self.patch, self.pre_release, self.build = (
            self._parse(version_str)
        )
    
    @staticmethod
    def _parse(version_str: str) -> Tuple[int, int, int, str, str]:
        """Parse version string into components."""
        # Remove 'v' prefix if present
        if version_str.startswith("v"):
            version_str = version_str[1:]
        
        # Split by '+' for build metadata
        parts = version_str.split("+")
        version_part = parts[0]
        build = parts[1] if len(parts) > 1 else ""
        
        # Split by '-' for pre-release
        parts = version_part.split("-")
        core_version = parts[0]
        pre_release = parts[1] if len(parts) > 1 else ""
        
        # Parse major.minor.patch
        version_numbers = core_version.split(".")
        if len(version_numbers) != 3:
            raise ValueError(f"Invalid version format: {version_str}. Expected: X.Y.Z")
        
        try:
            major = int(version_numbers[0])
            minor = int(version_numbers[1])
            patch = int(version_numbers[2])
        except ValueError:
            raise ValueError(f"Invalid version format: {version_str}. Expected integers")
        
        return major, minor, patch, pre_release, build
    
    def __str__(self) -> str:
        """String representation."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.pre_release:
            version += f"-{self.pre_release}"
        if self.build:
            version += f"+{self.build}"
        return version
    
    def __repr__(self) -> str:
        """Debug representation."""
        return f"Version('{self}')"
    
    def __eq__(self, other) -> bool:
        """Equality comparison."""
        if not isinstance(other, Version):
            other = Version(str(other))
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.pre_release == other.pre_release
        )
    
    def __lt__(self, other) -> bool:
        """Less than comparison."""
        if not isinstance(other, Version):
            other = Version(str(other))
        
        # Compare major.minor.patch
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.patch != other.patch:
            return self.patch < other.patch
        
        # Pre-release versions have lower precedence
        if self.pre_release and not other.pre_release:
            return True
        if not self.pre_release and other.pre_release:
            return False
        
        # Compare pre-release versions lexicographically
        if self.pre_release and other.pre_release:
            return self.pre_release < other.pre_release
        
        return False
    
    def __le__(self, other) -> bool:
        """Less than or equal comparison."""
        return self < other or self == other
    
    def __gt__(self, other) -> bool:
        """Greater than comparison."""
        return not self <= other
    
    def __ge__(self, other) -> bool:
        """Greater than or equal comparison."""
        return not self < other
    
    def is_compatible_with(self, other: "Version") -> bool:
        """
        Check if this version is compatible with another version.
        
        Compatible means same major version (unless major is 0).
        
        Args:
            other: Other version
            
        Returns:
            True if compatible
        """
        if self.major == 0 or other.major == 0:
            # Pre-1.0 versions: require exact match
            return self.major == other.major and self.minor == other.minor
        else:
            # Post-1.0 versions: same major version
            return self.major == other.major
    
    def bump_major(self) -> "Version":
        """Create new version with major bumped."""
        return Version(f"{self.major + 1}.0.0")
    
    def bump_minor(self) -> "Version":
        """Create new version with minor bumped."""
        return Version(f"{self.major}.{self.minor + 1}.0")
    
    def bump_patch(self) -> "Version":
        """Create new version with patch bumped."""
        return Version(f"{self.major}.{self.minor}.{self.patch + 1}")


class VersionManager:
    """
    Manages version resolution and compatibility checking.
    
    Example:
        ```python
        manager = VersionManager()
        
        # Find latest compatible version
        versions = ["1.0.0", "1.1.0", "1.2.0", "2.0.0"]
        latest = manager.find_latest_compatible("1.0.0", versions)
        # Returns: "1.2.0"
        
        # Check compatibility
        compatible = manager.is_compatible("1.0.0", "1.5.0")
        # Returns: True
        ```
    """
    
    @staticmethod
    def parse_version(version_str: str) -> Version:
        """
        Parse version string.
        
        Args:
            version_str: Version string
            
        Returns:
            Version object
        """
        return Version(version_str)
    
    @staticmethod
    def find_latest(versions: List[str]) -> Optional[str]:
        """
        Find latest version from list.
        
        Args:
            versions: List of version strings
            
        Returns:
            Latest version string or None if list is empty
        """
        if not versions:
            return None
        
        version_objs = [Version(v) for v in versions]
        latest = max(version_objs)
        return str(latest)
    
    @staticmethod
    def find_latest_compatible(
        base_version: str,
        versions: List[str],
    ) -> Optional[str]:
        """
        Find latest version compatible with base version.
        
        Args:
            base_version: Base version string
            versions: List of available version strings
            
        Returns:
            Latest compatible version or None
        """
        if not versions:
            return None
        
        base = Version(base_version)
        compatible_versions = [
            Version(v) for v in versions if base.is_compatible_with(Version(v))
        ]
        
        if not compatible_versions:
            return None
        
        latest = max(compatible_versions)
        return str(latest)
    
    @staticmethod
    def is_compatible(version1: str, version2: str) -> bool:
        """
        Check if two versions are compatible.
        
        Args:
            version1: First version string
            version2: Second version string
            
        Returns:
            True if compatible
        """
        v1 = Version(version1)
        v2 = Version(version2)
        return v1.is_compatible_with(v2)
    
    @staticmethod
    def sort_versions(versions: List[str], reverse: bool = False) -> List[str]:
        """
        Sort versions in ascending or descending order.
        
        Args:
            versions: List of version strings
            reverse: Sort in descending order
            
        Returns:
            Sorted list of version strings
        """
        version_objs = [Version(v) for v in versions]
        sorted_objs = sorted(version_objs, reverse=reverse)
        return [str(v) for v in sorted_objs]
    
    @staticmethod
    def get_upgrade_path(
        from_version: str,
        to_version: str,
        available_versions: List[str],
    ) -> List[str]:
        """
        Get upgrade path between two versions.
        
        Returns intermediate versions that should be installed
        for safe migration.
        
        Args:
            from_version: Starting version
            to_version: Target version
            available_versions: All available versions
            
        Returns:
            List of versions in upgrade path (including target)
        """
        from_ver = Version(from_version)
        to_ver = Version(to_version)
        
        if from_ver >= to_ver:
            return []  # Already at or beyond target version
        
        # Get all versions between from and to
        all_versions = [Version(v) for v in available_versions]
        intermediate = [
            v for v in all_versions if from_ver < v <= to_ver
        ]
        
        # Sort in ascending order
        intermediate.sort()
        
        return [str(v) for v in intermediate]

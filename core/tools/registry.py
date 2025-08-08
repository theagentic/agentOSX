"""
Plugin registry for agentOS.
- Manifest schema inspired by elizaOS: name, version, capabilities, permissions,
  entrypoint, env_required, compatibility, settings schema
- Load from local directory or git URL (git URL stubbed)
- Hot-reload in dev (file mtime check)
- Permission gating at call time
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from ...settings import settings


@dataclass
class PluginManifest:
    name: str
    version: str
    capabilities: List[str]
    permissions: List[str]
    entrypoint: str  # module:attr or module:function
    env_required: List[str] = field(default_factory=list)
    compatibility: Dict[str, str] = field(default_factory=lambda: {"api_version": "0.1"})
    settings_schema: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "PluginManifest":
        return cls(
            name=data["name"],
            version=data["version"],
            capabilities=data.get("capabilities", []),
            permissions=data.get("permissions", []),
            entrypoint=data["entrypoint"],
            env_required=data.get("env_required", []),
            compatibility=data.get("compatibility", {"api_version": "0.1"}),
            settings_schema=data.get("settings", {}),
        )


@dataclass
class Plugin:
    manifest: PluginManifest
    module: types.ModuleType
    exported: Any


class PermissionError(Exception):
    pass


class PluginRegistry:
    """Load and manage plugins, enforce permissions."""

    def __init__(self, plugins_dir: Optional[str] = None):
        self.plugins_dir = Path(plugins_dir or settings.plugin_dir)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self._plugins: Dict[str, Plugin] = {}
        self._mtimes: Dict[str, float] = {}

    def load_local(self, path: str) -> Plugin:
        """Load plugin from a local directory containing manifest.json."""
        p = Path(path)
        manifest_path = p / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"manifest.json not found in {p}")
        manifest = PluginManifest.from_json(json.loads(manifest_path.read_text()))
        self._check_env(manifest)
        module, exported = self._load_entrypoint(p, manifest.entrypoint)
        plugin = Plugin(manifest=manifest, module=module, exported=exported)
        self._plugins[manifest.name] = plugin
        self._mtimes[manifest.name] = manifest_path.stat().st_mtime
        return plugin

    def load_git(self, git_url: str, ref: Optional[str] = None) -> Plugin:
        """Load plugin from a git URL. Stub: instruct user to clone locally for now."""
        raise NotImplementedError(
            "Git plugin loading not implemented yet. Clone the repository locally and use load_local()."
        )

    def _check_env(self, manifest: PluginManifest):
        missing = [k for k in manifest.env_required if not (k in sys.modules.get('os').environ if 'os' in sys.modules else False)]
        # best-effort; real check done by reading os.environ directly to avoid sys.modules hack
        import os
        missing = [k for k in manifest.env_required if not os.getenv(k)]
        if missing:
            raise EnvironmentError(f"Missing required environment variables for plugin {manifest.name}: {missing}")

    def _load_entrypoint(self, base_dir: Path, entrypoint: str):
        """Load module and export from entrypoint 'module:attr'."""
        if ":" not in entrypoint:
            raise ValueError("entrypoint must be 'module:attr'")
        module_name, attr_name = entrypoint.split(":", 1)
        module_path = base_dir / (module_name.replace(".", "/") + ".py")
        if not module_path.exists():
            raise FileNotFoundError(f"Module {module_path} not found for plugin entrypoint")

        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)  # type: ignore
        assert spec and spec.loader
        sys.modules[module_name] = module
        spec.loader.exec_module(module)  # type: ignore
        exported = getattr(module, attr_name)
        return module, exported

    def call(self, plugin_name: str, capability: str, permission: str, *args, **kwargs):
        """Call plugin exported callable enforcing permissions and capabilities."""
        plugin = self._plugins.get(plugin_name)
        if not plugin:
            raise KeyError(f"Plugin {plugin_name} not loaded")
        if capability not in plugin.manifest.capabilities:
            raise PermissionError(f"Plugin {plugin_name} does not declare capability {capability}")
        if permission not in plugin.manifest.permissions:
            raise PermissionError(f"Plugin {plugin_name} missing permission {permission}")
        if not callable(plugin.exported):
            raise TypeError(f"Plugin {plugin_name} exported object is not callable")
        return plugin.exported(*args, **kwargs)

    def hot_reload(self):
        """Hot reload plugins if manifest changed (dev only)."""
        if settings.environment != "development":
            return
        for name, plugin in list(self._plugins.items()):
            manifest_path = Path(plugin.module.__file__).parent / "manifest.json"  # type: ignore
            if manifest_path.exists():
                mtime = manifest_path.stat().st_mtime
                if mtime > self._mtimes.get(name, 0):
                    # Reload
                    self.load_local(str(manifest_path.parent))

    def list_plugins(self) -> List[str]:
        return list(self._plugins.keys())


# Singleton registry
registry = PluginRegistry()

"""Configuration manager for dynamic sites."""

from pathlib import Path

import yaml

from .schema import SiteConfig

CONFIG_DIR = Path.home() / ".config" / "turok"
SITES_FILE = CONFIG_DIR / "sites.yaml"


class ConfigManager:
    """Manages reading and writing site configurations."""

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or SITES_FILE

    def _ensure_dir(self) -> None:
        """Ensure config directory exists."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def load_all(self) -> dict[str, SiteConfig]:
        """Load all site configurations."""
        if not self.config_path.exists():
            return {}

        with open(self.config_path) as f:
            data = yaml.safe_load(f) or {}

        sites = {}
        for key, site_data in data.get("sites", {}).items():
            try:
                sites[key] = SiteConfig.from_dict(key, site_data)
            except (KeyError, TypeError):
                continue  # Skip invalid configs

        return sites

    def load_enabled(self) -> dict[str, SiteConfig]:
        """Load only enabled site configurations."""
        return {k: v for k, v in self.load_all().items() if v.enabled}

    def save(self, key: str, config: SiteConfig) -> None:
        """Save a site configuration."""
        self._ensure_dir()

        # Load existing data
        if self.config_path.exists():
            with open(self.config_path) as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}

        # Ensure structure
        if "version" not in data:
            data["version"] = 1
        if "sites" not in data:
            data["sites"] = {}

        # Add/update site
        data["sites"][key] = config.to_dict()

        # Write back
        with open(self.config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def remove(self, key: str) -> bool:
        """Remove a site configuration. Returns True if removed."""
        if not self.config_path.exists():
            return False

        with open(self.config_path) as f:
            data = yaml.safe_load(f) or {}

        sites = data.get("sites", {})
        if key not in sites:
            return False

        del sites[key]

        with open(self.config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        return True

    def set_enabled(self, key: str, enabled: bool) -> bool:
        """Enable or disable a site. Returns True if found."""
        if not self.config_path.exists():
            return False

        with open(self.config_path) as f:
            data = yaml.safe_load(f) or {}

        sites = data.get("sites", {})
        if key not in sites:
            return False

        sites[key]["enabled"] = enabled

        with open(self.config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        return True

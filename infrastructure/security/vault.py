import json
import os
from typing import Optional
from config.loader import ConfigLoader


class SecurityVault:
    def __init__(self, vault_path: str = None):
        if vault_path is None:
            vault_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "config", "vault.json.enc"
            )
        self.vault_path = vault_path
        self._cache = {}
        self._load_env()

    def _load_env(self):
        env = ConfigLoader.load_env()
        for key, value in env.items():
            if "KEY" in key or "TOKEN" in key or "SECRET" in key:
                self._cache[key] = value

    def get(self, key: str) -> Optional[str]:
        return self._cache.get(key) or os.environ.get(key)

    def set(self, key: str, value: str) -> None:
        self._cache[key] = value

    def validate(self) -> dict:
        required = ["TELEGRAM_BOT_TOKEN"]
        missing = [k for k in required if not self.get(k)]
        available = [k for k in self._cache.keys()]
        return {
            "available_keys": available,
            "missing": missing,
            "secure": len(missing) == 0,
        }

    def get_available_providers(self) -> list:
        providers = ["ollama"]
        if self.get("OPENROUTER_API_KEY") or self.get("TELEGRAM_BOT_TOKEN"):
            pass
        if self.get("ANTHROPIC_API_KEY"):
            providers.append("claude")
        if self.get("GEMINI_API_KEY"):
            providers.append("gemini")
        return providers

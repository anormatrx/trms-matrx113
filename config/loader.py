import json
import os


class ConfigLoader:
    CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")

    @staticmethod
    def load_env(env_file: str = ".env.comm") -> dict:
        path = os.path.join(os.path.dirname(ConfigLoader.CONFIG_DIR), "Tools", env_file)
        secrets = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and "=" in line and not line.startswith("#"):
                        key, value = line.split("=", 1)
                        secrets[key.strip()] = value.strip()
        return secrets

    @staticmethod
    def load_config() -> dict:
        config = {
            "app_name": "DevCenter",
            "version": "2.0.0",
            "environment": os.environ.get("ENV", "development"),
        }

        # Database
        db_path = os.environ.get(
            "DB_PATH",
            os.path.join(ConfigLoader.CONFIG_DIR, "..", "Database", "tasks.db"),
        )
        config["database"] = {
            "path": os.path.abspath(db_path),
            "pool_size": int(os.environ.get("DB_POOL", "5")),
            "timeout": int(os.environ.get("DB_TIMEOUT", "30")),
        }

        # Server
        config["server"] = {
            "host": os.environ.get("HOST", "127.0.0.1"),
            "port": int(os.environ.get("PORT", "5000")),
            "workers": int(os.environ.get("WORKERS", "4")),
            "max_concurrent": int(os.environ.get("MAX_CONCURRENT", "10000")),
        }

        # Security
        config["security"] = {
            "rate_limit": int(os.environ.get("RATE_LIMIT", "100")),
            "rate_window": int(os.environ.get("RATE_WINDOW", "60")),
            "max_retries": int(os.environ.get("MAX_RETRIES", "3")),
            "encryption_key": os.environ.get("ENCRYPTION_KEY", ""),
        }

        # AI Providers
        config["ai"] = {
            "default_model": os.environ.get("AI_MODEL", "ollama/llama3.2:3b"),
            "fallback_model": os.environ.get("AI_FALLBACK", "openrouter/free"),
            "timeout": int(os.environ.get("AI_TIMEOUT", "30")),
            "max_tokens": int(os.environ.get("AI_MAX_TOKENS", "2000")),
        }

        return config

    @staticmethod
    def validate():
        config = ConfigLoader.load_config()
        env = ConfigLoader.load_env()
        warnings = []

        required_keys = ["TELEGRAM_BOT_TOKEN"]
        for key in required_keys:
            if key not in env or not env[key]:
                warnings.append(f"⚠️ {key} غير موجود في .env.comm")

        db_dir = os.path.dirname(config["database"]["path"])
        if not os.path.exists(db_dir):
            warnings.append(f"⚠️ مسار قاعدة البيانات غير موجود: {db_dir}")

        return {"config": config, "env_keys": list(env.keys()), "warnings": warnings}

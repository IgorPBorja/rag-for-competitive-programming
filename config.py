from dynaconf import Dynaconf
from pathlib import Path

production_config_files = ["settings.toml", ".secrets.toml"]
dev_config_files = ["settings.local.toml", ".secrets.local.toml"]

settings = Dynaconf(
    settings_files=[str(Path(__file__).parent / fpath) for fpath in production_config_files + dev_config_files]
)

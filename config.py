from dynaconf import settings
from pathlib import Path

production_config_files = ["settings.toml", ".secrets.toml"]
dev_config_files = ["settings.local.toml", ".secrets.local.toml"]

settings.load_file(
    [Path(__file__).parent / fpath for fpath in production_config_files + dev_config_files],
)

CONFIG = settings  # alias for importing loaded configs

import tomllib
from pathlib import Path

import tomli_w

from dto import AvitoConfig


def load_avito_config(path: str = "config.toml") -> AvitoConfig:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return AvitoConfig(**data["avito"])


def save_avito_config(config: dict):
    with Path("config.toml").open("wb") as f:
        tomli_w.dump(config, f)

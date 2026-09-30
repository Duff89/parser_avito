import tomllib
from dataclasses import fields
from pathlib import Path

import tomli_w

from dto import AvitoConfig


def load_avito_config(path: str = "config.toml") -> AvitoConfig:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    known_fields = {field.name for field in fields(AvitoConfig)}
    config = {
        key: value
        for key, value in data["avito"].items()
        if key in known_fields
    }
    return AvitoConfig(**config)


def save_avito_config(config: dict):
    with Path("config.toml").open("wb") as f:
        tomli_w.dump(config, f)

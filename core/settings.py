from pathlib import Path

from pydantic import AnyUrl, BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource,
)


class AvitoSettings(BaseModel):
    url: list[AnyUrl] = Field(default_factory=list)
    chat_ids: list[str] = Field(default_factory=list)
    tg_token: str = ""
    num_ads: int
    freq: int = 60
    keys: list[str] = Field(default_factory=list)
    max_price: int = 2**32
    min_price: int = 0
    geo: str = ""
    proxy: str = ""
    proxy_change_ip: str = ""
    need_more_info: int = False
    debug_mode: bool = True
    max_view: int | None = None
    black_keyword_input: list[str] = Field(default_factory=list)
    fast_speed: bool = False


class ParserSettings(BaseSettings):
    avito: AvitoSettings = Field(init=False)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (YamlConfigSettingsSource(settings_cls, Path("settings.yaml")),)

from dto import AvitoConfig

from parser.export.naming.single_file import SingleFileNamingStrategy
from parser.export.naming.per_link import PerLinkNamingStrategy

def build_naming_strategy(config: AvitoConfig):
    """Строит стратегию именования результатов на основе конфига"""
    if config.one_file_for_link:
        return PerLinkNamingStrategy(base_dir=str(config.output_dir))
    return SingleFileNamingStrategy(path=str(config.output_dir / "result.xlsx"))


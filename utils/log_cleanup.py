"""
Утилита для управления ротацией и автоматической очисткой старых лог-файлов.
Решает проблему накопления логов на диске (Issue #274).
"""
import time
from pathlib import Path
from loguru import logger


def clean_old_logs(
    log_dir: Path | str = "logs",
    max_age_days: int = 5,
    max_files: int = 10,
) -> list[Path]:
    """
    Удаляет устаревшие и избыточные лог-файлы из директории логов.

    :param log_dir: путь к папке с логами (по умолчанию 'logs')
    :param max_age_days: максимальный возраст файлов в днях (файлы старше удаляются)
    :param max_files: максимальное количество сохраняемых файлов логов
    :return: список путей успешно удаленных файлов
    """
    log_path = Path(log_dir)
    if not log_path.exists() or not log_path.is_dir():
        return []

    removed_files: list[Path] = []
    now = time.time()
    max_age_seconds = max_age_days * 86400

    # Находим все файлы логов и их архивы (.log, .zip, .gz, .tar и т.д.)
    log_files = [
        f for f in log_path.iterdir()
        if f.is_file() and (".log" in f.name or f.suffix in {".log", ".zip", ".gz"})
    ]

    # 1. Удаляем файлы, превысившие максимальный возраст
    remaining_files: list[Path] = []
    for file in log_files:
        try:
            file_mtime = file.stat().st_mtime
            if (now - file_mtime) > max_age_seconds:
                file.unlink(missing_ok=True)
                removed_files.append(file)
                logger.debug(f"Удален устаревший лог-файл: {file.name}")
            else:
                remaining_files.append(file)
        except OSError as err:
            logger.warning(f"Не удалось проверить/удалить лог-файл {file.name}: {err}")
            remaining_files.append(file)

    # 2. Если оставшихся файлов больше max_files, удаляем самые старые
    if len(remaining_files) > max_files:
        remaining_files.sort(key=lambda f: f.stat().st_mtime if f.exists() else 0)
        excess_count = len(remaining_files) - max_files
        for file in remaining_files[:excess_count]:
            try:
                file.unlink(missing_ok=True)
                removed_files.append(file)
                logger.debug(f"Удален избыточный лог-файл по лимиту: {file.name}")
            except OSError as err:
                logger.warning(f"Не удалось удалить лог-файл {file.name}: {err}")

    if removed_files:
        logger.info(f"Очистка логов: удалено {len(removed_files)} старых/избыточных файлов")

    return removed_files

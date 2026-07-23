import os

from astrbot.core.config import AstrBotConfig
from astrbot.core.config.default import DB_PATH
from astrbot.core.db.sqlite import SQLiteDatabase
from astrbot.core.file_token_service import FileTokenService
from astrbot.core.utils.pip_installer import (
    DependencyConflictError as DependencyConflictError,
)
from astrbot.core.utils.pip_installer import (
    PipInstaller,
)
from astrbot.core.utils.requirements_utils import (
    RequirementsPrecheckFailed as RequirementsPrecheckFailed,
)
from astrbot.core.utils.requirements_utils import (
    find_missing_requirements as find_missing_requirements,
)
from astrbot.core.utils.requirements_utils import (
    find_missing_requirements_or_raise as find_missing_requirements_or_raise,
)
from astrbot.core.utils.shared_preferences import SharedPreferences
from astrbot.core.utils.t2i.renderer import HtmlRenderer

from .log import LogBroker, LogManager  # noqa
from .utils.astrbot_path import get_astrbot_data_path

# Initialize data folder
os.makedirs(get_astrbot_data_path(), exist_ok=True)

DEMO_MODE = os.getenv("DEMO_MODE", "False").strip().lower() in ("true", "1", "t")

astrbot_config = AstrBotConfig()
t2i_base_url = astrbot_config.get("t2i_endpoint", "https://t2i.soulter.top/text2img")
html_renderer = HtmlRenderer(t2i_base_url)
logger = LogManager.GetLogger(log_name="astrbot")
LogManager.configure_logger(logger, astrbot_config)
LogManager.configure_trace_logger(astrbot_config)

# === Database initialization: use DATABASE_URL (Postgres) if provided, otherwise fallback to bundled SQLite.
from astrbot.core.db.driver import AsyncDatabase  # lightweight async driver wrapper

database_url = os.getenv("DATABASE_URL", "").strip()
if database_url and not database_url.startswith("sqlite"):
    # Use AsyncDatabase when a remote database is configured (Postgres, etc.)
    db_helper = AsyncDatabase(database_url)
else:
    # Fallback to local SQLiteDatabase
    db_helper = SQLiteDatabase(DB_PATH)

# Simple preference store
sp = SharedPreferences(db_helper=db_helper)
# File token service
file_token_service = FileTokenService()
pip_installer = PipInstaller(
    astrbot_config.get("pip_install_arg", ""),
    astrbot_config.get("pypi_index_url", None),
)

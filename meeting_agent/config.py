import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv(override=True)


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"缺少 {name}，请检查 .env 文件。")
    return value


def _get_env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _get_float_env(name: str, default: str) -> float:
    return float(_get_env(name, default))


def _get_int_env(name: str, default: str) -> int:
    return int(_get_env(name, default))


@dataclass
class Settings:
    openai_api_key: str
    openai_base_url: str
    model_name: str
    temperature: float = 0.2
    WECOM_CORP_ID: str = ""
    WECOM_CORP_SECRET: str = ""
    WECOM_AGENT_ID: int = 0


def get_settings() -> Settings:
    return Settings(
        openai_api_key=_get_required_env("OPENAI_API_KEY"),
        openai_base_url=_get_required_env("OPENAI_BASE_URL"),
        model_name=_get_required_env("MODEL_NAME"),
        temperature=_get_float_env("TEMPERATURE", "0.2"),
        WECOM_CORP_ID=_get_env("WECOM_CORP_ID", ""),
        WECOM_CORP_SECRET=_get_env("WECOM_CORP_SECRET", ""),
        WECOM_AGENT_ID=_get_int_env("WECOM_AGENT_ID", "0"),
    )

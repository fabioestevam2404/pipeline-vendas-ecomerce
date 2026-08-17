"""Configuração central do pipeline, carregada a partir de variáveis de ambiente.

Nenhuma credencial deve ser hardcoded aqui — ver docs/ai/security-rules.md.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Configuração imutável do pipeline, resolvida uma única vez no processo."""

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int
    raw_data_dir: Path
    landing_zone_dir: Path
    quarantine_dir: Path

    @property
    def postgres_dsn(self) -> str:
        """Monta a DSN de conexão. Nunca logar o retorno desta property."""
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


def load_settings() -> Settings:
    """Lê e valida as variáveis de ambiente necessárias para rodar o pipeline.

    Levanta ValueError com mensagem clara se alguma variável obrigatória faltar,
    em vez de falhar silenciosamente mais adiante com um erro de conexão confuso.
    """
    required = ["POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise ValueError(
            f"Variáveis de ambiente obrigatórias ausentes: {', '.join(missing)}. "
            "Verifique se o arquivo .env foi criado a partir de .env.example."
        )

    return Settings(
        postgres_user=os.environ["POSTGRES_USER"],
        postgres_password=os.environ["POSTGRES_PASSWORD"],
        postgres_db=os.environ["POSTGRES_DB"],
        postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
        postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
        raw_data_dir=Path(os.getenv("RAW_DATA_DIR", "./data/raw")),
        landing_zone_dir=Path(os.getenv("LANDING_ZONE_DIR", "./data/landing")),
        quarantine_dir=Path(os.getenv("QUARANTINE_DIR", "./data/quarantine")),
    )

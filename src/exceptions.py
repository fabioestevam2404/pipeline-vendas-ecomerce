"""Exceções compartilhadas entre os módulos do pipeline.

Distinção deliberada (ver docs/ai/coding-rules.md):
- SchemaValidationError / IngestionError: erro de infraestrutura/contrato, fatal
  para o arquivo em questão, mas não deve interromper o processamento dos demais.
- QualityRejectionError: usada apenas para sinalizar internamente que uma LINHA
  (não o arquivo) falhou uma regra de qualidade — nunca deve escapar para o
  orquestrador; a linha é roteada para quarentena, não tratada como exceção fatal.
"""

from __future__ import annotations


class PipelineError(Exception):
    """Classe-base para erros deste pipeline."""


class SchemaValidationError(PipelineError):
    """Levantada quando um arquivo não atende ao contrato de schema esperado."""


class IngestionError(PipelineError):
    """Levantada quando um arquivo não pode ser lido (corrompido, ausente, etc.)."""

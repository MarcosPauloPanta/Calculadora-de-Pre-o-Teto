"""Hierarquia de exceções específicas do projeto.

Cada camada captura apenas o que sabe tratar; nada de ``except Exception``.
"""
from __future__ import annotations


class PrecoTetoError(Exception):
    """Raiz de todas as falhas previstas pelo sistema."""


class TickerInvalidoError(PrecoTetoError, ValueError):
    """O texto informado não tem formato de ticker da B3 (ex.: PETR4)."""


class TickerNaoEncontradoError(PrecoTetoError):
    """O provedor de dados não conhece o ticker."""


class ProvedorIndisponivelError(PrecoTetoError):
    """Falha de rede, biblioteca ausente, limite de uso ou token exigido."""


class DadosInvalidosError(PrecoTetoError, ValueError):
    """Dados recebidos/armazenados violam as regras de domínio."""


class DadosInsuficientesError(PrecoTetoError):
    """Faltam dados (ou eles não são positivos) para aplicar um método."""


class MetodoNaoAplicavelError(PrecoTetoError):
    """O tipo de ativo não possui método de preço teto (ex.: ETF)."""


class ParametroInvalidoError(PrecoTetoError, ValueError):
    """Parâmetro de configuração de método fora do intervalo válido."""


class PersistenciaError(PrecoTetoError):
    """Falha ao ler ou gravar o histórico de resultados."""

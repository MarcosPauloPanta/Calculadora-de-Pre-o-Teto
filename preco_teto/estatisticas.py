"""Resumo estatístico de uma série anual e recomendação de medida central.

O usuário pode sempre escolher a medida (``media``, ``mediana``, ``aparada``,
``ultimo``); com ``auto`` vale a recomendação, que é explicada em texto.

Regra de recomendação (simples e auditável):
* menos de 4 pontos -> média (não dá para avaliar outliers);
* algum outlier -> mediana. Outlier = fora de [Q1-1,5 IQR, Q3+1,5 IQR] (Tukey) E afastado da
  mediana em mais de 20% (evita marcar desvios irrelevantes em séries muito estáveis);
* coeficiente de variação > 50% -> mediana;
* caso contrário -> média.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Optional, Sequence

from preco_teto.exceptions import DadosInsuficientesError, ParametroInvalidoError

MEDIDAS = ("media", "mediana", "aparada", "ultimo")
ESCOLHAS = ("auto",) + MEDIDAS
MATERIALIDADE = 0.20  # desvio mínimo relativo à mediana para um ponto contar como outlier


@dataclass(frozen=True)
class ResumoEstatistico:
    variavel: str
    n: int
    media: float
    mediana: float
    aparada: float
    desvio: float
    cv: Optional[float]
    ultimo: float
    anos_outliers: tuple[int, ...]
    recomendada: str
    motivo: str
    escolhida: str  # medida efetivamente usada (nunca "auto")
    valor: float


def _outliers(serie: Sequence[tuple[int, float]]) -> tuple[int, ...]:
    if len(serie) < 4:
        return ()
    q1, _, q3 = statistics.quantiles([v for _, v in serie], n=4, method="inclusive")
    iqr = q3 - q1
    baixo, alto = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    mediana = statistics.median(v for _, v in serie)
    return tuple(
        a for a, v in serie
        if (v < baixo or v > alto) and abs(v - mediana) > MATERIALIDADE * abs(mediana)
    )


def _aparada(valores: list[float], corte: float) -> float:
    ordenados = sorted(valores)
    k = int(len(ordenados) * corte)
    miolo = ordenados[k : len(ordenados) - k] or ordenados
    return statistics.fmean(miolo)


def resumir(
    variavel: str,
    serie: Sequence[tuple[int, float]],
    escolha: str = "auto",
    corte: float = 0.1,
) -> ResumoEstatistico:
    """``serie`` = pares (ano, valor) em ordem cronológica."""
    if escolha not in ESCOLHAS:
        raise ParametroInvalidoError(f"Medida '{escolha}' inválida; use uma de {ESCOLHAS}.")
    if not 0 <= corte < 0.5:
        raise ParametroInvalidoError("corte da média aparada deve estar em [0, 0,5).")
    if not serie:
        raise DadosInsuficientesError(f"Série vazia para {variavel}.")

    valores = [v for _, v in serie]
    media = statistics.fmean(valores)
    desvio = statistics.stdev(valores) if len(valores) > 1 else 0.0
    cv = desvio / abs(media) if media != 0 else None
    outliers = _outliers(serie)

    if len(valores) < 4:
        recomendada, motivo = "media", f"amostra pequena (n={len(valores)}): outliers não avaliáveis"
    elif outliers:
        recomendada, motivo = "mediana", f"outliers em {', '.join(map(str, outliers))}"
    elif cv is not None and cv > 0.5:
        recomendada, motivo = "mediana", f"alta dispersão (CV={cv:.0%})"
    else:
        recomendada, motivo = "media", "série estável, sem outliers"

    medidas = {
        "media": media,
        "mediana": statistics.median(valores),
        "aparada": _aparada(valores, corte),
        "ultimo": valores[-1],
    }
    escolhida = recomendada if escolha == "auto" else escolha
    return ResumoEstatistico(
        variavel=variavel,
        n=len(valores),
        media=medidas["media"],
        mediana=medidas["mediana"],
        aparada=medidas["aparada"],
        desvio=desvio,
        cv=cv,
        ultimo=medidas["ultimo"],
        anos_outliers=outliers,
        recomendada=recomendada,
        motivo=motivo,
        escolhida=escolhida,
        valor=medidas[escolhida],
    )

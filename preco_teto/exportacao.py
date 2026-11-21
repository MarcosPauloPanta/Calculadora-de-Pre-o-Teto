"""Exportação das tabelas de cálculo para CSV (auditoria no Excel/Sheets)."""
from __future__ import annotations

import csv
from pathlib import Path

from preco_teto.analise import AnaliseHistorica
from preco_teto.exceptions import PersistenciaError

_COLUNAS_TABELA = ["ano", "lucro_liquido", "patrimonio_liquido", "lpa", "dpa", "roe", "payout", "obs"]
_COLUNAS_STATS = ["variavel", "n", "media", "mediana", "aparada", "ultimo", "desvio", "cv",
                  "anos_outliers", "recomendada", "motivo", "escolhida", "valor"]


def exportar_csv(analise: AnaliseHistorica, pasta: Path | str) -> list[Path]:
    pasta = Path(pasta)
    destino_tabela = pasta / f"{analise.ticker}_tabela_anual.csv"
    destino_stats = pasta / f"{analise.ticker}_estatisticas.csv"
    try:
        pasta.mkdir(parents=True, exist_ok=True)
        with destino_tabela.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(_COLUNAS_TABELA)
            for l in analise.linhas:
                w.writerow([l.ano, l.lucro_liquido, l.patrimonio_liquido, l.lpa, l.dpa,
                            "" if l.roe is None else l.roe, "" if l.payout is None else l.payout, l.obs])
        with destino_stats.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(_COLUNAS_STATS)
            for r in analise.resumos:
                w.writerow([r.variavel, r.n, r.media, r.mediana, r.aparada, r.ultimo, r.desvio,
                            "" if r.cv is None else r.cv, " ".join(map(str, r.anos_outliers)),
                            r.recomendada, r.motivo, r.escolhida, r.valor])
    except OSError as exc:
        raise PersistenciaError(f"Não foi possível exportar para {pasta}: {exc}") from exc
    return [destino_tabela, destino_stats]

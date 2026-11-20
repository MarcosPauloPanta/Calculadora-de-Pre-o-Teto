"""Persistência do histórico de resultados em um arquivo JSON.

A gravação é atômica (arquivo temporário + ``os.replace``): se algo falhar no
meio, o histórico anterior permanece intacto.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Optional

from preco_teto.exceptions import DadosInvalidosError, PersistenciaError
from preco_teto.models import ResultadoTeto


class RepositorioResultados:
    def __init__(self, caminho: Path | str) -> None:
        self._caminho = Path(caminho)

    def listar(self) -> list[ResultadoTeto]:
        if not self._caminho.exists():
            return []
        try:
            with self._caminho.open("r", encoding="utf-8") as f:
                bruto = json.load(f)
            return [ResultadoTeto.from_dict(d) for d in bruto]
        except (OSError, json.JSONDecodeError, TypeError, DadosInvalidosError) as exc:
            raise PersistenciaError(f"Histórico ilegível em {self._caminho}: {exc}") from exc

    def salvar(self, resultado: ResultadoTeto) -> None:
        historico = self.listar()
        historico.append(resultado)
        self._gravar(historico)

    def ultimo(self, ticker: str) -> Optional[ResultadoTeto]:
        do_ticker = [r for r in self.listar() if r.ticker == ticker.upper()]
        return do_ticker[-1] if do_ticker else None

    def _gravar(self, historico: list[ResultadoTeto]) -> None:
        pasta = self._caminho.parent
        tmp_nome = None
        try:
            pasta.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=pasta, suffix=".tmp", delete=False
            ) as tmp:
                tmp_nome = tmp.name
                json.dump([r.to_dict() for r in historico], tmp, ensure_ascii=False, indent=2)
            os.replace(tmp_nome, self._caminho)
        except OSError as exc:
            if tmp_nome and os.path.exists(tmp_nome):
                os.unlink(tmp_nome)
            raise PersistenciaError(f"Não foi possível gravar {self._caminho}: {exc}") from exc

"""Coleta e normalização inicial de demonstrações financeiras da CVM.

Fonte oficial: dados.cvm.gov.br. O módulo baixa FCA (ticker -> companhia/CNPJ)
e DFP (demonstrações anuais), mantém ZIPs em cache e preserva a trilha de
origem de cada conta. Não calcula preço teto: preço de mercado, ações em
circulação, LPA e proventos precisam de fontes/tratamentos próprios.
"""
from __future__ import annotations

import csv
import io
import re
import time
import unicodedata
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from preco_teto.exceptions import (
    DadosInvalidosError,
    ProvedorIndisponivelError,
    TickerNaoEncontradoError,
)
from preco_teto.ticker import Ticker

_BASE = "https://dados.cvm.gov.br/dados/CIA_ABERTA"
_USER_AGENT = "CalculadoraPrecoTeto/0.3 (open-source educational project)"
_TIPOS_DFP = ("DRE", "BPA", "BPP", "DFC_MI")
_TIPOS_ITR = ("DRE", "BPA", "BPP", "DFC_MI", "DFC_MD", "DMPL", "DRA", "DVA")


def _normalizar_coluna(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]", "", texto.upper())


def _campo(linha: dict[str, str], *nomes: str) -> str:
    mapa = {_normalizar_coluna(k): (v or "").strip() for k, v in linha.items()}
    for nome in nomes:
        valor = mapa.get(_normalizar_coluna(nome), "")
        if valor:
            return valor
    return ""


def _numero(texto: str) -> Optional[float]:
    if texto is None:
        return None
    valor = str(texto).strip()
    if not valor or valor.upper() in {"N/A", "NA", "NULL", "NAN"}:
        return None
    valor = valor.replace(" ", "")
    if "," in valor and "." in valor:
        valor = valor.replace(".", "").replace(",", ".")
    else:
        valor = valor.replace(",", ".")
    try:
        return float(valor)
    except ValueError:
        return None


def _data(texto: str) -> Optional[date]:
    try:
        return date.fromisoformat((texto or "")[:10])
    except ValueError:
        return None


@dataclass(frozen=True)
class CompanhiaCVM:
    ticker: str
    cd_cvm: str
    cnpj: str
    nome: str
    ano_fca: int


@dataclass(frozen=True)
class ContaContabilCVM:
    demonstracao: str
    data_referencia: date
    data_fim_exercicio: Optional[date]
    grupo: str
    ordem_exercicio: str
    codigo: str
    descricao: str
    valor_original: float
    escala_moeda: str
    moeda: str
    versao: str
    data_recebimento: Optional[date]
    conta_fixa: str
    arquivo_origem: str
    data_inicio_periodo: Optional[date] = None

    @property
    def valor(self) -> float:
        """Valor convertido para unidade monetária, preservando valor/escala originais."""
        escala = _normalizar_coluna(self.escala_moeda)
        fator = {"UNIDADE": 1.0, "MIL": 1_000.0, "MILHAR": 1_000.0,
                 "MILHAO": 1_000_000.0, "BILHAO": 1_000_000_000.0}.get(escala, 1.0)
        return self.valor_original * fator


@dataclass(frozen=True)
class RelatorioCVM:
    companhia: CompanhiaCVM
    contas: tuple[ContaContabilCVM, ...]
    anos_solicitados: int

    @property
    def anos_disponiveis(self) -> tuple[int, ...]:
        return tuple(sorted({c.data_referencia.year for c in self.contas}))


class ClienteCVM:
    """Cliente CVM com cache local e resolução explícita ticker -> CNPJ/CD_CVM.

    O FCA é pesquisado do ano corrente para trás, pois reapresentações podem
    atualizar os dados de negociação. Os arquivos DFP são anuais e públicos.
    """

    def __init__(
        self,
        cache_dir: str | Path = ".cache/cvm",
        timeout: float = 40.0,
        ttl_segundos: int = 24 * 60 * 60,
        abrir_url: Optional[Callable[..., Any]] = None,
        ano_atual: Optional[int] = None,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.timeout = timeout
        self.ttl_segundos = ttl_segundos
        self._abrir = abrir_url or urllib.request.urlopen
        self.ano_atual = ano_atual or date.today().year

    def _baixar_zip(self, url: str, destino: Path) -> bytes:
        destino.parent.mkdir(parents=True, exist_ok=True)
        if destino.exists() and time.time() - destino.stat().st_mtime < self.ttl_segundos:
            conteudo = destino.read_bytes()
            if zipfile.is_zipfile(io.BytesIO(conteudo)):
                return conteudo
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        try:
            with self._abrir(req, timeout=self.timeout) as resposta:
                conteudo = resposta.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ProvedorIndisponivelError(f"Falha ao baixar dados da CVM ({url}): {exc}") from exc
        if not zipfile.is_zipfile(io.BytesIO(conteudo)):
            raise DadosInvalidosError(f"A CVM não devolveu um ZIP válido: {url}")
        temporario = destino.with_suffix(destino.suffix + ".tmp")
        temporario.write_bytes(conteudo)
        temporario.replace(destino)
        return conteudo

    @staticmethod
    def _linhas_csv(zip_bytes: bytes, trecho_nome: str) -> Iterable[tuple[str, dict[str, str]]]:
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as arquivo:
                nomes = [n for n in arquivo.namelist()
                         if trecho_nome.lower() in Path(n).name.lower() and n.lower().endswith(".csv")]
                for nome in nomes:
                    with arquivo.open(nome) as bruto:
                        texto = io.TextIOWrapper(bruto, encoding="latin-1", newline="")
                        amostra = texto.read(4096)
                        texto.seek(0)
                        try:
                            dialeto = csv.Sniffer().sniff(amostra, delimiters=";,\t")
                        except csv.Error:
                            dialeto = csv.excel
                            dialeto.delimiter = ";"
                        for linha in csv.DictReader(texto, dialect=dialeto):
                            yield nome, linha
        except (zipfile.BadZipFile, OSError, UnicodeError) as exc:
            raise DadosInvalidosError(f"Não foi possível ler arquivo CSV da CVM: {exc}") from exc

    def buscar_companhia(self, ticker_texto: str | Ticker) -> CompanhiaCVM:
        ticker = ticker_texto if isinstance(ticker_texto, Ticker) else Ticker(ticker_texto)
        for ano in range(self.ano_atual, max(2017, self.ano_atual - 9), -1):
            url = f"{_BASE}/DOC/FCA/DADOS/fca_cia_aberta_{ano}.zip"
            cache = self.cache_dir / "fca" / f"fca_cia_aberta_{ano}.zip"
            try:
                pacote = self._baixar_zip(url, cache)
            except ProvedorIndisponivelError:
                if ano == self.ano_atual:
                    continue
                raise
            gerais: dict[str, dict[str, str]] = {}
            valores: list[dict[str, str]] = []
            for nome, linha in self._linhas_csv(pacote, "fca_cia_aberta_"):
                base = Path(nome).name.lower()
                if "valor_mobiliario" in base:
                    valores.append(linha)
                elif "geral" in base:
                    chave = _campo(linha, "CNPJ_CIA", "CNPJ")
                    if chave:
                        gerais[chave] = linha
            for linha in valores:
                codigos = {
                    _campo(linha, "CODIGO_NEGOCIACAO", "CD_NEGOCIACAO", "COD_NEGOCIACAO").upper(),
                }
                if ticker.simbolo not in codigos:
                    continue
                cnpj = _campo(linha, "CNPJ_CIA", "CNPJ")
                geral = gerais.get(cnpj, {})
                cd_cvm = _campo(linha, "CD_CVM") or _campo(geral, "CD_CVM")
                nome = (_campo(linha, "DENOM_CIA", "DENOMINACAO_SOCIAL")
                        or _campo(geral, "DENOM_CIA", "DENOMINACAO_SOCIAL"))
                if cnpj and cd_cvm:
                    return CompanhiaCVM(ticker.simbolo, cd_cvm, cnpj, nome or ticker.simbolo, ano)
        raise TickerNaoEncontradoError(
            f"{ticker}: código de negociação não localizado nos Formulários Cadastrais (FCA) da CVM. "
            "Verifique se o ticker é de companhia aberta e se consta no cadastro."
        )

    def obter_relatorio_anual(
        self, ticker_texto: str | Ticker, anos: int = 10
    ) -> RelatorioCVM:
        if not isinstance(anos, int) or not 1 <= anos <= 17:
            raise DadosInvalidosError("A janela DFP deve ser um inteiro entre 1 e 17 anos.")
        companhia = self.buscar_companhia(ticker_texto)
        contas: list[ContaContabilCVM] = []
        primeiro_ano = max(2010, self.ano_atual - anos + 1)
        for ano in range(primeiro_ano, self.ano_atual + 1):
            url = f"{_BASE}/DOC/DFP/DADOS/dfp_cia_aberta_{ano}.zip"
            cache = self.cache_dir / "dfp" / f"dfp_cia_aberta_{ano}.zip"
            try:
                pacote = self._baixar_zip(url, cache)
            except ProvedorIndisponivelError:
                # O ano corrente pode ainda não ter DFP publicada.
                if ano == self.ano_atual:
                    continue
                raise
            for tipo in _TIPOS_DFP:
                trecho = f"_{tipo.lower()}_"
                for nome, linha in self._linhas_csv(pacote, trecho):
                    cnpj = _campo(linha, "CNPJ_CIA", "CNPJ")
                    cd_cvm = _campo(linha, "CD_CVM")
                    if cnpj != companhia.cnpj and cd_cvm != companhia.cd_cvm:
                        continue
                    data_ref = _data(_campo(linha, "DT_REFER"))
                    valor = _numero(_campo(linha, "VL_CONTA"))
                    if data_ref is None or valor is None:
                        continue
                    contas.append(ContaContabilCVM(
                        demonstracao=tipo,
                        data_referencia=data_ref,
                        data_fim_exercicio=_data(_campo(linha, "DT_FIM_EXERC")),
                        grupo=_campo(linha, "GRUPO_DFP"),
                        ordem_exercicio=_campo(linha, "ORDEM_EXERC"),
                        codigo=_campo(linha, "CD_CONTA"),
                        descricao=_campo(linha, "DS_CONTA"),
                        valor_original=valor,
                        escala_moeda=_campo(linha, "ESCALA_MOEDA"),
                        moeda=_campo(linha, "MOEDA"),
                        versao=_campo(linha, "VERSAO"),
                        data_recebimento=_data(_campo(linha, "DT_RECEB")),
                        conta_fixa=_campo(linha, "ST_CONTA_FIXA"),
                        arquivo_origem=Path(nome).name,
                    ))
        if not contas:
            raise DadosInvalidosError(
                f"{companhia.ticker}: a CVM identificou a companhia, mas não retornou contas DFP "
                f"na janela de {anos} ano(s)."
            )
        contas = self._deduplicar(contas)
        return RelatorioCVM(companhia, tuple(contas), anos)


    def obter_relatorio_trimestral(
        self, ticker_texto: str | Ticker, anos: int = 5
    ) -> RelatorioCVM:
        """Baixa ITR e preserva o início/fim de cada período.

        DRE/DFC podem vir acumuladas desde o início do exercício. Use
        cvm_periodos.trimestres_isolados para derivar trimestres isolados.
        """
        if not isinstance(anos, int) or not 1 <= anos <= 10:
            raise DadosInvalidosError("A janela ITR deve ser um inteiro entre 1 e 10 anos.")
        companhia = self.buscar_companhia(ticker_texto)
        contas: list[ContaContabilCVM] = []
        primeiro_ano = max(2011, self.ano_atual - anos + 1)
        for ano in range(primeiro_ano, self.ano_atual + 1):
            url = f"{_BASE}/DOC/ITR/DADOS/itr_cia_aberta_{ano}.zip"
            cache = self.cache_dir / "itr" / f"itr_cia_aberta_{ano}.zip"
            try:
                pacote = self._baixar_zip(url, cache)
            except ProvedorIndisponivelError:
                if ano == self.ano_atual:
                    continue
                raise
            for tipo in _TIPOS_ITR:
                trecho = f"_{tipo.lower()}_"
                for nome, linha in self._linhas_csv(pacote, trecho):
                    cnpj = _campo(linha, "CNPJ_CIA", "CNPJ")
                    cd_cvm = _campo(linha, "CD_CVM")
                    if cnpj != companhia.cnpj and cd_cvm != companhia.cd_cvm:
                        continue
                    data_ref = _data(_campo(linha, "DT_REFER"))
                    valor = _numero(_campo(linha, "VL_CONTA"))
                    if data_ref is None or valor is None:
                        continue
                    contas.append(ContaContabilCVM(
                        demonstracao=tipo,
                        data_referencia=data_ref,
                        data_fim_exercicio=_data(_campo(linha, "DT_FIM_EXERC")),
                        grupo=_campo(linha, "GRUPO_DFP"),
                        ordem_exercicio=_campo(linha, "ORDEM_EXERC"),
                        codigo=_campo(linha, "CD_CONTA"),
                        descricao=_campo(linha, "DS_CONTA"),
                        valor_original=valor,
                        escala_moeda=_campo(linha, "ESCALA_MOEDA"),
                        moeda=_campo(linha, "MOEDA"),
                        versao=_campo(linha, "VERSAO"),
                        data_recebimento=_data(_campo(linha, "DT_RECEB")),
                        conta_fixa=_campo(linha, "ST_CONTA_FIXA"),
                        arquivo_origem=Path(nome).name,
                        data_inicio_periodo=_data(_campo(linha, "DT_INI_EXERC")),
                    ))
        if not contas:
            raise DadosInvalidosError(
                f"{companhia.ticker}: a CVM não retornou contas ITR na janela de {anos} ano(s)."
            )
        return RelatorioCVM(companhia, tuple(self._deduplicar(contas)), anos)

    @staticmethod
    def _deduplicar(contas: list[ContaContabilCVM]) -> list[ContaContabilCVM]:
        """Mantém a versão mais recente por demonstração/período/grupo/conta."""
        escolhidas: dict[tuple[str, date, str, str, str], ContaContabilCVM] = {}
        for conta in contas:
            chave = (conta.demonstracao, conta.data_referencia, conta.grupo,
                     conta.ordem_exercicio, conta.codigo)
            atual = escolhidas.get(chave)
            versao_nova = _numero(conta.versao) or 0
            versao_atual = (_numero(atual.versao) or 0) if atual else -1
            data_nova = conta.data_recebimento or date.min
            data_atual = (atual.data_recebimento or date.min) if atual else date.min
            if atual is None or (versao_nova, data_nova) >= (versao_atual, data_atual):
                escolhidas[chave] = conta
        return sorted(escolhidas.values(), key=lambda c: (
            c.data_referencia, c.demonstracao, c.grupo, c.codigo, c.ordem_exercicio
        ))

import io
import json
import tempfile
import unittest
import urllib.error
from datetime import date, datetime
from pathlib import Path

from preco_teto.exceptions import (
    DadosInvalidosError, PrecoTetoError, ProvedorIndisponivelError, TickerNaoEncontradoError,
)
from preco_teto.provedores import (
    ProvedorArquivoJson, ProvedorBrapi, ProvedorComFallback, ProvedorDados, ProvedorYFinance,
)
from preco_teto.ticker import Ticker

EXEMPLOS = Path(__file__).resolve().parent.parent / "data" / "exemplos"


class TestArquivo(unittest.TestCase):
    def test_le_exemplo(self):
        d = ProvedorArquivoJson(EXEMPLOS).obter(Ticker("PETR4"))
        self.assertEqual(d.ticker, "PETR4")
        self.assertEqual(len(d.proventos), 5)

    def test_ausente(self):
        with self.assertRaises(TickerNaoEncontradoError):
            ProvedorArquivoJson(EXEMPLOS).obter(Ticker("ZZZZ3"))

    def test_json_corrompido_e_campos_faltando(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "AAAA3.json").write_text("{nao eh json", encoding="utf-8")
            Path(tmp, "BBBB3.json").write_text(json.dumps({"nome": "x"}), encoding="utf-8")
            prov = ProvedorArquivoJson(tmp)
            for t in ("AAAA3", "BBBB3"):
                with self.subTest(t=t), self.assertRaises(DadosInvalidosError):
                    prov.obter(Ticker(t))


class FakeYF:
    def __init__(self, info, dividends):
        self.info, self.dividends = info, dividends


class SerieFalsa:
    def __init__(self, itens):
        self._i = itens

    def items(self):
        return self._i


class TestYFinance(unittest.TestCase):
    def test_converte(self):
        serie = SerieFalsa([(datetime(2026, 5, 1), 1.5)])
        fake = FakeYF({"currentPrice": 38.5, "trailingEps": 6.2, "bookValue": 28.0, "longName": "Petro"}, serie)
        usado = []
        prov = ProvedorYFinance(lambda s: usado.append(s) or fake)
        d = prov.obter(Ticker("PETR4"))
        self.assertEqual(usado, ["PETR4.SA"])
        self.assertEqual((d.preco_atual, d.lpa, d.vpa), (38.5, 6.2, 28.0))
        self.assertEqual(d.proventos[0].data, date(2026, 5, 1))

    def test_sem_preco_nao_encontrado(self):
        prov = ProvedorYFinance(lambda s: FakeYF({}, SerieFalsa([])))
        with self.assertRaises(TickerNaoEncontradoError):
            prov.obter(Ticker("PETR4"))

    def test_erro_de_rede_vira_indisponivel(self):
        class Quebrado:
            @property
            def info(self):
                raise OSError("sem rede")
        with self.assertRaises(ProvedorIndisponivelError):
            ProvedorYFinance(lambda s: Quebrado()).obter(Ticker("PETR4"))


class RespostaFalsa(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def abrir_ok(payload):
    return lambda req, timeout: RespostaFalsa(json.dumps(payload).encode())


def abrir_http(code):
    def f(req, timeout):
        raise urllib.error.HTTPError(req.full_url, code, "x", {}, None)
    return f


class TestBrapi(unittest.TestCase):
    PAYLOAD = {"results": [{
        "symbol": "PETR4", "longName": "Petrobras", "regularMarketPrice": 38.5, "earningsPerShare": 6.2,
        "defaultKeyStatistics": {"bookValue": 28.0},
        "dividendsData": {"cashDividends": [
            {"paymentDate": "2026-05-20T00:00:00.000Z", "rate": 1.1},
            {"paymentDate": None, "rate": 0.9},
        ]}}]}

    def test_converte_e_ignora_nao_pagos(self):
        d = ProvedorBrapi(abrir_url=abrir_ok(self.PAYLOAD)).obter(Ticker("PETR4"))
        self.assertEqual((d.preco_atual, d.lpa, d.vpa), (38.5, 6.2, 28.0))
        self.assertEqual(len(d.proventos), 1)

    def test_token_enviado_no_header(self):
        vistos = []
        def abrir(req, timeout):
            vistos.append(req.get_header("Authorization"))
            return RespostaFalsa(json.dumps(self.PAYLOAD).encode())
        ProvedorBrapi(token="abc", abrir_url=abrir).obter(Ticker("PETR4"))
        self.assertEqual(vistos, ["Bearer abc"])

    def test_erros_http(self):
        casos = {404: TickerNaoEncontradoError, 401: ProvedorIndisponivelError,
                 429: ProvedorIndisponivelError, 500: ProvedorIndisponivelError}
        for code, exc in casos.items():
            with self.subTest(code=code), self.assertRaises(exc):
                ProvedorBrapi(abrir_url=abrir_http(code)).obter(Ticker("PETR4"))

    def test_sem_resultados_e_formato_ruim(self):
        with self.assertRaises(TickerNaoEncontradoError):
            ProvedorBrapi(abrir_url=abrir_ok({"results": []})).obter(Ticker("PETR4"))
        with self.assertRaises(DadosInvalidosError):
            ProvedorBrapi(abrir_url=abrir_ok({"results": [{"symbol": "PETR4"}]})).obter(Ticker("PETR4"))

    def test_sem_conexao(self):
        def f(req, timeout):
            raise urllib.error.URLError("dns")
        with self.assertRaises(ProvedorIndisponivelError):
            ProvedorBrapi(abrir_url=f).obter(Ticker("PETR4"))


class TestFallback(unittest.TestCase):
    def test_usa_o_segundo_quando_o_primeiro_cai(self):
        quebrado = ProvedorYFinance(lambda s: (_ for _ in ()).throw(ProvedorIndisponivelError("off")))
        ok = ProvedorArquivoJson(EXEMPLOS)
        d = ProvedorComFallback([quebrado, ok]).obter(Ticker("PETR4"))
        self.assertEqual(d.ticker, "PETR4")

    def test_todos_falham(self):
        with self.assertRaises(PrecoTetoError):
            ProvedorComFallback([ProvedorArquivoJson(EXEMPLOS)]).obter(Ticker("ZZZZ3"))

    def test_eh_um_provedor(self):
        self.assertIsInstance(ProvedorComFallback([ProvedorArquivoJson(EXEMPLOS)]), ProvedorDados)


if __name__ == "__main__":
    unittest.main()

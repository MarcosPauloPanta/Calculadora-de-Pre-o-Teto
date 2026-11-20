import unittest

from preco_teto.classificador import ClassificadorAtivo, TipoAtivo
from preco_teto.exceptions import TickerInvalidoError
from preco_teto.models import DadosMercado
from preco_teto.ticker import Ticker


class TestTicker(unittest.TestCase):
    def test_normaliza_minusculas_espacos_e_sufixo_sa(self):
        self.assertEqual(Ticker(" petr4.sa ").simbolo, "PETR4")

    def test_partes(self):
        t = Ticker("TAEE11")
        self.assertEqual((t.raiz, t.sufixo), ("TAEE", 11))

    def test_invalidos(self):
        for ruim in ["", "PETR", "12345", "PETRO4X", "PE TR4", "PETR444"]:
            with self.subTest(ruim=ruim), self.assertRaises(TickerInvalidoError):
                Ticker(ruim)

    def test_tipo_nao_texto(self):
        with self.assertRaises(TickerInvalidoError):
            Ticker(None)  # type: ignore[arg-type]


class TestClassificador(unittest.TestCase):
    def setUp(self):
        self.c = ClassificadorAtivo()

    def test_por_sufixo(self):
        casos = {"VALE3": TipoAtivo.ACAO, "PETR4": TipoAtivo.ACAO, "AAPL34": TipoAtivo.BDR,
                 "BOVA11": TipoAtivo.ETF, "TAEE11": TipoAtivo.UNIT, "HGLG11": TipoAtivo.FII}
        for simbolo, esperado in casos.items():
            with self.subTest(simbolo=simbolo):
                self.assertEqual(self.c.classificar(Ticker(simbolo)), esperado)

    def test_nome_com_pista_de_etf(self):
        dados = DadosMercado("XPTO11", "ISHARES ALGO ETF", 10.0)
        self.assertEqual(self.c.classificar(Ticker("XPTO11"), dados), TipoAtivo.ETF)

    def test_sufixo_11_desconhecido_vira_fii(self):
        self.assertEqual(self.c.classificar(Ticker("ABCD11")), TipoAtivo.FII)


if __name__ == "__main__":
    unittest.main()

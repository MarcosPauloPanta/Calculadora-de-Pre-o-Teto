import unittest
from datetime import date

from preco_teto.analise import ParametrosValuation
from preco_teto.ativos import Acao, Bdr, Etf, FabricaAtivos, FundoImobiliario
from preco_teto.classificador import TipoAtivo
from preco_teto.exceptions import (
    DadosInsuficientesError, DadosInvalidosError, MetodoNaoAplicavelError, ParametroInvalidoError,
)
from preco_teto.metodos import MetodoGordon, MetodoPrecoTeto, MetodoPVPJustificado
from preco_teto.models import DadosMercado, RegistroAnual, ResultadoMetodo
from preco_teto.ticker import Ticker

HOJE = date(2026, 11, 20)
T = Ticker("PETR4")
K12 = ParametrosValuation(k=0.12)


class MetodoFixo(MetodoPrecoTeto):
    """Implementação controlada do contrato (substituição polimórfica)."""

    def __init__(self, valor):
        self._v = valor

    @property
    def nome(self):
        return f"Fixo{self._v}"

    def calcular(self, dados, hoje):
        return ResultadoMetodo(self.nome, self._v, "fixo")


def dados(n=6, dpa=1.0, preco=38.5, ticker="PETR4"):
    hist = tuple(RegistroAnual(2016 + i, 20.0, 100.0, 2.0, dpa) for i in range(n))
    return DadosMercado(ticker, "Petro", preco, vpa=20.0, historico=hist)


class TestAtivo(unittest.TestCase):
    def test_acao_consolida_pelo_menor_teto(self):
        r = Acao(T, dados(), params=K12).calcular_preco_teto(HOJE)   # PVP 100 ; Gordon 55
        self.assertEqual(r.metodo_decisivo, "Gordon")
        self.assertAlmostEqual(r.preco_teto, 55.0)
        self.assertEqual([m.metodo for m in r.resultados], ["P/VP justificado", "Gordon"])
        self.assertEqual(r.veredito, "ABAIXO DO TETO")

    def test_acao_exige_k(self):
        with self.assertRaises(ParametroInvalidoError):
            Acao(T, dados())

    def test_polimorfismo_ativo_aceita_qualquer_metodo(self):
        r = Acao(T, dados(), metodos=[MetodoFixo(100.0), MetodoFixo(40.0)]).calcular_preco_teto(HOJE)
        self.assertEqual((r.preco_teto, r.metodo_decisivo), (40.0, "Fixo40.0"))

    def test_falha_parcial_vira_aviso(self):
        # k=10% == g -> ambos divergem; com Fixo ao lado, o resultado sai e os avisos registram as falhas
        k10 = ParametrosValuation(k=0.10)
        metodos = [MetodoPVPJustificado(k10), MetodoGordon(k10), MetodoFixo(70.0)]
        r = Acao(T, dados(), metodos=metodos).calcular_preco_teto(HOJE)
        self.assertEqual(r.metodo_decisivo, "Fixo70.0")
        self.assertEqual(len(r.avisos), 2)

    def test_todos_falham(self):
        with self.assertRaises(DadosInsuficientesError):
            Acao(T, dados(n=2), params=K12).calcular_preco_teto(HOJE)

    def test_etf_e_bdr_sem_metodo(self):
        for cls, t in ((Etf, "BOVA11"), (Bdr, "AAPL34")):
            with self.subTest(t=t), self.assertRaises(MetodoNaoAplicavelError):
                cls(Ticker(t), DadosMercado(t, "x", 10.0)).calcular_preco_teto(HOJE)

    def test_dados_de_outro_ticker_recusados(self):
        with self.assertRaises(DadosInvalidosError):
            Acao(Ticker("VALE3"), dados(), params=K12)

    def test_acima_do_teto(self):
        r = Acao(T, dados(preco=200.0), metodos=[MetodoFixo(100.0)]).calcular_preco_teto(HOJE)
        self.assertEqual(r.veredito, "ACIMA DO TETO")
        self.assertLess(r.margem_seguranca, 0)

    def test_fabrica(self):
        self.assertIsInstance(FabricaAtivos.criar(TipoAtivo.UNIT, T, dados(), params=K12), Acao)
        d = DadosMercado("HGLG11", "x", 150.0)
        self.assertIsInstance(FabricaAtivos.criar(TipoAtivo.FII, Ticker("HGLG11"), d), FundoImobiliario)


if __name__ == "__main__":
    unittest.main()

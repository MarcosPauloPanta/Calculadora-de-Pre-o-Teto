import unittest
from datetime import date

from preco_teto.ativos import Acao, Etf, FabricaAtivos, FundoImobiliario
from preco_teto.classificador import TipoAtivo
from preco_teto.exceptions import DadosInsuficientesError, DadosInvalidosError, MetodoNaoAplicavelError
from preco_teto.metodos import MetodoBazin, MetodoPrecoTeto
from preco_teto.models import DadosMercado, Provento, ResultadoMetodo
from preco_teto.ticker import Ticker

HOJE = date(2026, 11, 20)
T = Ticker("PETR4")


class MetodoFixo(MetodoPrecoTeto):
    """Implementação controlada do contrato (substituição polimórfica)."""

    def __init__(self, valor):
        self._v = valor

    @property
    def nome(self):
        return f"Fixo{self._v}"

    def calcular(self, dados, hoje):
        return ResultadoMetodo(self.nome, self._v, "fixo")


class MetodoQuePerde(MetodoFixo):
    def calcular(self, dados, hoje):
        raise DadosInsuficientesError("sem dados")


def dados(lpa=6.2, vpa=28.0, provs=((date(2026, 5, 1), 4.2),)):
    return DadosMercado("PETR4", "Petro", 38.5, lpa, vpa, tuple(Provento(d, v) for d, v in provs))


class TestAtivo(unittest.TestCase):
    def test_acao_consolida_pelo_menor_teto(self):
        r = Acao(T, dados()).calcular_preco_teto(HOJE)
        self.assertEqual(r.metodo_decisivo, "Graham")
        self.assertAlmostEqual(r.preco_teto, 62.498, places=2)
        self.assertEqual(len(r.resultados), 2)
        self.assertEqual(r.veredito, "ABAIXO DO TETO")

    def test_polimorfismo_ativo_aceita_qualquer_metodo(self):
        r = Acao(T, dados(), metodos=[MetodoFixo(100.0), MetodoFixo(40.0)]).calcular_preco_teto(HOJE)
        self.assertEqual((r.preco_teto, r.metodo_decisivo), (40.0, "Fixo40.0"))

    def test_falha_parcial_vira_aviso(self):
        r = Acao(T, dados(lpa=-1.0)).calcular_preco_teto(HOJE)  # Graham falha, Bazin ok
        self.assertEqual(r.metodo_decisivo, "Bazin")
        self.assertEqual(len(r.avisos), 1)

    def test_todos_falham(self):
        with self.assertRaises(DadosInsuficientesError):
            Acao(T, dados(lpa=-1.0, provs=())).calcular_preco_teto(HOJE)

    def test_etf_sem_metodo(self):
        d = DadosMercado("BOVA11", "ETF", 130.0)
        with self.assertRaises(MetodoNaoAplicavelError):
            Etf(Ticker("BOVA11"), d).calcular_preco_teto(HOJE)

    def test_dados_de_outro_ticker_recusados(self):
        with self.assertRaises(DadosInvalidosError):
            Acao(Ticker("VALE3"), dados())

    def test_acima_do_teto(self):
        d = DadosMercado("PETR4", "x", 200.0)
        r = Acao(T, d, metodos=[MetodoFixo(100.0)]).calcular_preco_teto(HOJE)
        self.assertEqual(r.veredito, "ACIMA DO TETO")
        self.assertLess(r.margem_seguranca, 0)

    def test_fabrica(self):
        self.assertIsInstance(FabricaAtivos.criar(TipoAtivo.UNIT, T, dados()), Acao)
        d = DadosMercado("HGLG11", "x", 150.0)
        self.assertIsInstance(FabricaAtivos.criar(TipoAtivo.FII, Ticker("HGLG11"), d), FundoImobiliario)

    def test_metodos_padrao_por_tipo(self):
        self.assertEqual([type(m) for m in Acao.metodos_padrao()][0], MetodoBazin)
        self.assertEqual(Etf.metodos_padrao(), [])


if __name__ == "__main__":
    unittest.main()

import math
import unittest
from datetime import date

from preco_teto.exceptions import DadosInsuficientesError, DadosInvalidosError, ParametroInvalidoError
from preco_teto.metodos import MetodoBazin, MetodoDYFii, MetodoGraham
from preco_teto.models import DadosMercado, Provento

HOJE = date(2026, 11, 20)


def dados(lpa=None, vpa=None, provs=()):
    return DadosMercado("PETR4", "X", 10.0, lpa, vpa, tuple(Provento(d, v) for d, v in provs))


class TestBazin(unittest.TestCase):
    def test_calculo(self):
        d = dados(provs=[(date(2026, 3, 1), 1.0), (date(2026, 9, 1), 0.5)])
        r = MetodoBazin().calcular(d, HOJE)
        self.assertAlmostEqual(r.preco_teto, 1.5 / 0.06)

    def test_limite_da_janela(self):
        # exatamente 12 meses atrás fica FORA; um dia depois fica DENTRO
        fora = dados(provs=[(date(2025, 11, 20), 9.0), (date(2025, 11, 21), 1.0)])
        self.assertAlmostEqual(MetodoBazin().calcular(fora, HOJE).preco_teto, 1.0 / 0.06)

    def test_janela_de_24_meses_anualiza(self):
        d = dados(provs=[(date(2025, 1, 10), 2.0), (date(2026, 1, 10), 2.0)])
        r = MetodoBazin(janela_meses=24).calcular(d, HOJE)
        self.assertAlmostEqual(r.preco_teto, 2.0 / 0.06)

    def test_sem_proventos(self):
        with self.assertRaises(DadosInsuficientesError):
            MetodoBazin().calcular(dados(), HOJE)

    def test_provento_futuro_ignorado(self):
        with self.assertRaises(DadosInsuficientesError):
            MetodoBazin().calcular(dados(provs=[(date(2026, 12, 1), 1.0)]), HOJE)

    def test_parametros_invalidos(self):
        for y in (0, -0.1, 1.5):
            with self.subTest(y=y), self.assertRaises(ParametroInvalidoError):
                MetodoBazin(yield_alvo=y)
        with self.assertRaises(ParametroInvalidoError):
            MetodoBazin(janela_meses=0)

    def test_fii_usa_yield_proprio(self):
        d = dados(provs=[(date(2026, 1, 5), 12.0)])
        self.assertAlmostEqual(MetodoDYFii().calcular(d, HOJE).preco_teto, 12.0 / 0.08)


class TestGraham(unittest.TestCase):
    def test_calculo(self):
        r = MetodoGraham().calcular(dados(lpa=6.2, vpa=28.0), HOJE)
        self.assertAlmostEqual(r.preco_teto, math.sqrt(22.5 * 6.2 * 28.0))

    def test_lpa_negativo_zero_ou_ausente(self):
        for lpa, vpa in [(-1.0, 5.0), (0.0, 5.0), (2.0, 0.0), (None, 5.0), (2.0, None)]:
            with self.subTest(lpa=lpa, vpa=vpa), self.assertRaises(DadosInsuficientesError):
                MetodoGraham().calcular(dados(lpa=lpa, vpa=vpa), HOJE)

    def test_multiplicador_invalido(self):
        with self.assertRaises(ParametroInvalidoError):
            MetodoGraham(multiplicador=0)


class TestValidacaoModelos(unittest.TestCase):
    def test_preco_invalido(self):
        for p in (0, -1, float("nan"), float("inf")):
            with self.subTest(p=p), self.assertRaises(DadosInvalidosError):
                DadosMercado("PETR4", "X", p)

    def test_provento_negativo(self):
        with self.assertRaises(DadosInvalidosError):
            Provento(date(2026, 1, 1), -0.1)


if __name__ == "__main__":
    unittest.main()

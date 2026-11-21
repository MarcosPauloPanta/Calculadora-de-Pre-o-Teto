import unittest
from datetime import date

from preco_teto.analise import ParametrosValuation
from preco_teto.exceptions import DadosInsuficientesError, DadosInvalidosError, ParametroInvalidoError
from preco_teto.metodos import MetodoDYFii, MetodoGordon, MetodoPVPJustificado
from preco_teto.models import DadosMercado, Provento, RegistroAnual

HOJE = date(2026, 11, 20)


def dados(lucro=20.0, pl=100.0, lpa=2.0, dpa=1.0, vpa=20.0, n=6, provs=()):
    hist = tuple(RegistroAnual(2016 + i, lucro, pl, lpa, dpa) for i in range(n))
    return DadosMercado("PETR4", "X", 10.0, vpa=vpa, historico=hist,
                        proventos=tuple(Provento(d, v) for d, v in provs))


def params(k=0.12, **kw):
    return ParametrosValuation(k=k, **kw)


class TestPVPJustificado(unittest.TestCase):
    def test_calculo_manual(self):
        # ROE=20%, payout=50% -> g=10%; P/VP=(0,20-0,10)/(0,12-0,10)=5; x VPA 20 = 100
        r = MetodoPVPJustificado(params()).calcular(dados(), HOJE)
        self.assertAlmostEqual(r.preco_teto, 100.0)
        self.assertIsNotNone(r.analise)

    def test_k_menor_ou_igual_a_g_diverge(self):
        for k in (0.10, 0.08):
            with self.subTest(k=k), self.assertRaisesRegex(DadosInsuficientesError, "diverge"):
                MetodoPVPJustificado(params(k=k)).calcular(dados(), HOJE)

    def test_exige_k_do_usuario(self):
        with self.assertRaisesRegex(ParametroInvalidoError, "retorno exigido"):
            MetodoPVPJustificado(ParametrosValuation())

    def test_sem_vpa(self):
        with self.assertRaises(DadosInsuficientesError):
            MetodoPVPJustificado(params()).calcular(dados(vpa=None), HOJE)

    def test_roe_negativo_e_payout_zero(self):
        with self.assertRaises(DadosInsuficientesError):
            MetodoPVPJustificado(params()).calcular(dados(lucro=-10.0, lpa=2.0), HOJE)
        with self.assertRaises(DadosInsuficientesError):
            MetodoPVPJustificado(params()).calcular(dados(dpa=0.0), HOJE)

    def test_medida_escolhida_muda_o_resultado(self):
        hist = tuple(RegistroAnual(2016 + i, 10.0, 100.0, 1.0, 0.5) for i in range(5)) + (
            RegistroAnual(2021, 90.0, 100.0, 9.0, 4.5),)  # ROE 10% x5 e 90% (outlier)
        d = DadosMercado("PETR4", "X", 10.0, vpa=20.0, historico=hist)
        mediana = MetodoPVPJustificado(params(k=0.2)).calcular(d, HOJE)            # auto -> mediana
        media = MetodoPVPJustificado(params(k=0.2, estat_roe="media")).calcular(d, HOJE)
        self.assertNotAlmostEqual(mediana.preco_teto, media.preco_teto)
        self.assertEqual(mediana.analise.roe.escolhida, "mediana")


class TestGordon(unittest.TestCase):
    def test_calculo_manual(self):
        # g=10%; D=1,0; VF = 1,0 x 1,10 / (0,12-0,10) = 55
        self.assertAlmostEqual(MetodoGordon(params()).calcular(dados(), HOJE).preco_teto, 55.0)

    def test_sem_dividendos(self):
        with self.assertRaises(DadosInsuficientesError):
            MetodoGordon(params()).calcular(dados(dpa=0.0), HOJE)

    def test_k_maior_reduz_valor(self):
        a = MetodoGordon(params(k=0.12)).calcular(dados(), HOJE).preco_teto
        b = MetodoGordon(params(k=0.15)).calcular(dados(), HOJE).preco_teto
        self.assertGreater(a, b)


class TestDYFii(unittest.TestCase):
    def test_calculo(self):
        d = dados(provs=[(date(2026, 1, 5), 12.0)])
        self.assertAlmostEqual(MetodoDYFii().calcular(d, HOJE).preco_teto, 12.0 / 0.08)

    def test_sem_proventos(self):
        with self.assertRaises(DadosInsuficientesError):
            MetodoDYFii().calcular(dados(), HOJE)


class TestValidacaoModelos(unittest.TestCase):
    def test_preco_invalido(self):
        for p in (0, -1, float("nan"), float("inf")):
            with self.subTest(p=p), self.assertRaises(DadosInvalidosError):
                DadosMercado("PETR4", "X", p)

    def test_provento_negativo(self):
        with self.assertRaises(DadosInvalidosError):
            Provento(date(2026, 1, 1), -0.1)

    def test_historico_com_ano_repetido(self):
        with self.assertRaises(DadosInvalidosError):
            DadosMercado("PETR4", "X", 10.0, historico=(RegistroAnual(2020, 1, 1, 1, 0), RegistroAnual(2020, 1, 1, 1, 0)))


if __name__ == "__main__":
    unittest.main()

import unittest

from preco_teto.analise import AnalisadorHistorico, ParametrosValuation
from preco_teto.estatisticas import resumir
from preco_teto.exceptions import DadosInsuficientesError, ParametroInvalidoError
from preco_teto.models import DadosMercado, RegistroAnual


def serie(valores, ano0=2016):
    return [(ano0 + i, v) for i, v in enumerate(valores)]


class TestResumir(unittest.TestCase):
    def test_serie_constante(self):
        r = resumir("ROE", serie([0.2] * 6))
        self.assertAlmostEqual(r.media, 0.2)
        self.assertAlmostEqual(r.mediana, 0.2)
        self.assertEqual(r.desvio, 0.0)
        self.assertEqual(r.recomendada, "media")

    def test_outlier_recomenda_mediana(self):
        r = resumir("ROE", serie([0.1] * 5 + [0.9]))
        self.assertEqual(r.recomendada, "mediana")
        self.assertEqual(r.anos_outliers, (2021,))
        self.assertAlmostEqual(r.valor, 0.1)           # auto -> mediana
        self.assertAlmostEqual(r.media, 1.4 / 6)

    def test_usuario_sobrescreve_auto(self):
        r = resumir("ROE", serie([0.1] * 5 + [0.9]), escolha="media")
        self.assertEqual((r.escolhida, r.recomendada), ("media", "mediana"))
        self.assertAlmostEqual(r.valor, 1.4 / 6)
        self.assertAlmostEqual(resumir("X", serie([1, 2, 9]), "ultimo").valor, 9)

    def test_amostra_pequena_usa_media(self):
        r = resumir("X", serie([1.0, 2.0, 30.0]))
        self.assertEqual(r.recomendada, "media")

    def test_serie_estavel_nao_marca_outlier_irrelevante(self):
        r = resumir("Payout", serie([0.88, 1.0, 0.92, 0.9, 0.95, 0.85, 0.9, 0.93, 0.91, 0.9]))
        self.assertEqual(r.anos_outliers, ())
        self.assertEqual(r.recomendada, "media")

    def test_aparada_descarta_extremos(self):
        r = resumir("X", serie([1, 2, 3, 4, 5, 6, 7, 8, 9, 100]))  # corte 10% -> tira 1 de cada ponta
        self.assertAlmostEqual(r.aparada, sum(range(2, 10)) / 8)

    def test_invalidos(self):
        with self.assertRaises(ParametroInvalidoError):
            resumir("X", serie([1.0]), escolha="moda")
        with self.assertRaises(DadosInsuficientesError):
            resumir("X", [])


def reg(ano, lucro=20.0, pl=100.0, lpa=2.0, dpa=1.0):
    return RegistroAnual(ano, lucro, pl, lpa, dpa)


def dados(registros):
    return DadosMercado("PETR4", "X", 10.0, vpa=20.0, historico=tuple(registros))


class TestAnalisador(unittest.TestCase):
    def test_roe_payout_e_g(self):
        a = AnalisadorHistorico().analisar(dados(reg(2016 + i) for i in range(6)), ParametrosValuation())
        self.assertAlmostEqual(a.roe.valor, 0.2)
        self.assertAlmostEqual(a.payout.valor, 0.5)
        self.assertAlmostEqual(a.dpa.valor, 1.0)
        self.assertAlmostEqual(a.g, 0.1)
        self.assertEqual(len(a.linhas), 6)

    def test_janela_usa_os_anos_mais_recentes(self):
        regs = [reg(2010 + i) for i in range(12)]
        a = AnalisadorHistorico().analisar(dados(regs), ParametrosValuation(janela_anos=8, min_anos=5))
        self.assertEqual([l.ano for l in a.linhas], list(range(2014, 2022)))

    def test_exclusoes_com_motivo(self):
        regs = [reg(2016 + i) for i in range(6)] + [reg(2022, lucro=-5, lpa=-0.5, dpa=0.1), reg(2023, pl=-1)]
        a = AnalisadorHistorico().analisar(dados(regs), ParametrosValuation())
        por_ano = {l.ano: l for l in a.linhas}
        self.assertIn("sem payout", por_ano[2022].obs)
        self.assertIsNone(por_ano[2022].payout)
        self.assertIn("sem ROE", por_ano[2023].obs)
        self.assertEqual(a.roe.n, 7)    # 2023 sem ROE
        self.assertEqual(a.payout.n, 7)  # 2022 sem payout

    def test_payout_acima_de_100_limitado_nas_estatisticas(self):
        regs = [reg(2016 + i) for i in range(5)] + [reg(2021, lpa=1.0, dpa=3.0)]
        a = AnalisadorHistorico().analisar(dados(regs), ParametrosValuation(estat_payout="ultimo"))
        self.assertEqual(a.payout.valor, 1.0)
        self.assertEqual(a.linhas[-1].payout, 3.0)  # bruto preservado na tabela

    def test_poucos_anos_validos(self):
        with self.assertRaisesRegex(DadosInsuficientesError, "mínimo 5"):
            AnalisadorHistorico().analisar(dados(reg(2016 + i) for i in range(3)), ParametrosValuation())

    def test_sem_historico(self):
        with self.assertRaises(DadosInsuficientesError):
            AnalisadorHistorico().analisar(dados([]), ParametrosValuation())

    def test_aviso_quando_historico_menor_que_janela(self):
        a = AnalisadorHistorico().analisar(dados(reg(2016 + i) for i in range(6)), ParametrosValuation())
        self.assertEqual(len(a.avisos), 1)


class TestParametros(unittest.TestCase):
    def test_invalidos(self):
        for kw in ({"k": 0}, {"k": 1.2}, {"k": -0.1}, {"janela_anos": 0}, {"min_anos": 11},
                   {"estat_roe": "moda"}):
            with self.subTest(kw=kw), self.assertRaises(ParametroInvalidoError):
                ParametrosValuation(**kw)


if __name__ == "__main__":
    unittest.main()

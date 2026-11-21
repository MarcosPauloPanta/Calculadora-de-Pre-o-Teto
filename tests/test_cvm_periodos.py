import unittest
from datetime import date

from preco_teto.provedores.cvm import ContaContabilCVM
from preco_teto.provedores.cvm_periodos import trimestres_isolados


def conta(mes, valor, ano=2025, demonstracao="DRE", grupo="DF Consolidado", codigo="3.11"):
    dia = 31 if mes in (3, 12) else 30
    return ContaContabilCVM(
        demonstracao, date(ano, mes, dia),
        date(ano, 12, 31), grupo, "ÚLTIMO", codigo, "Lucro líquido",
        valor, "MIL", "REAL", "1", date(ano + 1, 3, 1), "S",
        f"itr_{mes}.csv", date(ano, 1, 1),
    )


class TestTrimestresIsolados(unittest.TestCase):
    def test_converte_acumulados_e_quarto_trimestre(self):
        itr = [conta(3, 100), conta(6, 250), conta(9, 420)]
        dfp = [conta(12, 600, demonstracao="DRE")]
        resultado = trimestres_isolados(itr, dfp)
        self.assertEqual([x.valor for x in resultado], [100, 150, 170, 180])
        self.assertEqual([x.trimestre for x in resultado], [1, 2, 3, 4])

    def test_nao_inventa_q4_sem_dfp(self):
        resultado = trimestres_isolados([conta(3, 10), conta(6, 30), conta(9, 60)])
        self.assertEqual([x.trimestre for x in resultado], [1, 2, 3])

    def test_nao_separa_q3_sem_q2(self):
        resultado = trimestres_isolados([conta(3, 10), conta(9, 60)])
        self.assertEqual([x.trimestre for x in resultado], [1])

    def test_ignora_saldos_de_balanco(self):
        balanco = [conta(3, 100, demonstracao="BPA"), conta(6, 140, demonstracao="BPA")]
        self.assertEqual(trimestres_isolados(balanco), ())

    def test_nao_mistura_grupos(self):
        itr = [
            conta(3, 10, grupo="DF Consolidado"),
            conta(6, 30, grupo="DF Consolidado"),
            conta(3, 4, grupo="DF Individual"),
            conta(6, 9, grupo="DF Individual"),
        ]
        resultado = trimestres_isolados(itr)
        self.assertEqual([x.valor for x in resultado], [10, 4, 20, 5])


if __name__ == "__main__":
    unittest.main()

import contextlib
import io
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from preco_teto.analise import ParametrosValuation
from preco_teto.cli import main
from preco_teto.exceptions import ParametroInvalidoError, PersistenciaError, TickerInvalidoError, TickerNaoEncontradoError
from preco_teto.provedores import ProvedorArquivoJson
from preco_teto.repositorio import RepositorioResultados
from preco_teto.servico import CalculadoraPrecoTeto

EXEMPLOS = Path(__file__).resolve().parent.parent / "data" / "exemplos"
HOJE = date(2026, 11, 20)
K12 = ParametrosValuation(k=0.12)


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.hist = Path(self._tmp.name) / "hist.json"
        self.repo = RepositorioResultados(self.hist)
        self.calc = CalculadoraPrecoTeto(ProvedorArquivoJson(EXEMPLOS), repositorio=self.repo)


class TestIntegracao(Base):
    """Execução integrada: provedor real (arquivo) -> classificador -> ativo -> repositório."""

    def test_valores_esperados_por_tipo(self):
        # valores conferidos com um cálculo independente (statistics + json, sem usar o pacote)
        esperado = {"PETR4": ("ACAO", 49.69, "Gordon"), "TAEE11": ("ACAO", 15.49, "Gordon"),
                    "HGLG11": ("FII", 165.00, "DY alvo (FII)")}
        for t, (tipo, teto, metodo) in esperado.items():
            with self.subTest(t=t):
                r = self.calc.calcular(t, HOJE, K12)
                self.assertAlmostEqual(r.preco_teto, teto, places=2)
                self.assertEqual((r.metodo_decisivo, r.tipo), (metodo, tipo))

    def test_acao_sem_k_e_recusada_e_nada_e_gravado(self):
        with self.assertRaises(ParametroInvalidoError):
            self.calc.calcular("PETR4", HOJE)
        self.assertEqual(self.repo.listar(), [])

    def test_medida_do_usuario_altera_o_teto(self):
        auto = self.calc.calcular("PETR4", HOJE, K12).preco_teto
        media = self.calc.calcular("PETR4", HOJE, ParametrosValuation(k=0.12, estat_roe="media", estat_dpa="media")).preco_teto
        self.assertNotAlmostEqual(auto, media, places=2)

    def test_analisar_nao_exige_k(self):
        a = self.calc.analisar("PETR4")
        self.assertEqual(len(a.linhas), 10)
        self.assertEqual(a.roe.escolhida, "mediana")

    def test_persistencia_entre_instancias(self):
        self.calc.calcular("PETR4", HOJE, K12)
        outro = RepositorioResultados(self.hist)  # "nova execução"
        r = outro.ultimo("petr4")
        self.assertIsNotNone(r)
        self.assertAlmostEqual(r.preco_teto, 49.69, places=2)
        self.assertEqual(r.data_referencia, HOJE)

    def test_falha_nao_altera_historico(self):
        self.calc.calcular("PETR4", HOJE, K12)
        antes = self.hist.read_text(encoding="utf-8")
        for t, exc in [("ZZZZ3", TickerNaoEncontradoError), ("lixo", TickerInvalidoError)]:
            with self.assertRaises(exc):
                self.calc.calcular(t, HOJE, K12)
        self.assertEqual(self.hist.read_text(encoding="utf-8"), antes)

    def test_lote_isola_erros(self):
        ok, erros = self.calc.calcular_varios(["PETR4", "BOVA11", "MGLU3", "ZZZZ3", "HGLG11"], HOJE, K12)
        self.assertEqual([r.ticker for r in ok], ["PETR4", "HGLG11"])
        self.assertEqual(set(erros), {"BOVA11", "MGLU3", "ZZZZ3"})
        self.assertEqual(len(self.repo.listar()), 2)  # só os bem-sucedidos foram gravados


class TestRepositorio(Base):
    def test_vazio(self):
        self.assertEqual(self.repo.listar(), [])
        self.assertIsNone(self.repo.ultimo("PETR4"))

    def test_arquivo_corrompido(self):
        self.hist.write_text("{{{", encoding="utf-8")
        with self.assertRaises(PersistenciaError):
            self.repo.listar()

    def test_gravacao_atomica_preserva_anterior(self):
        self.calc.calcular("PETR4", HOJE, K12)
        antes = self.hist.read_text(encoding="utf-8")
        resultado = RepositorioResultados(self.hist).listar()[0]
        with mock.patch("preco_teto.repositorio.os.replace", side_effect=OSError("disco cheio")):
            with self.assertRaises(PersistenciaError):
                self.repo.salvar(resultado)
        self.assertEqual(self.hist.read_text(encoding="utf-8"), antes)
        self.assertEqual([p.name for p in self.hist.parent.glob("*.tmp")], [])


class TestCli(Base):
    def rodar(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(args))
        return code, out.getvalue(), err.getvalue()

    def base(self, *tickers, k="12%"):
        extra = ["--k", k] if k else []
        return ["calcular", *tickers, "--fonte", "arquivo", "--pasta-dados", str(EXEMPLOS), *extra,
                "--data-referencia", "2026-11-20", "--historico", str(self.hist)]

    def test_cenario_completo(self):
        code, out, err = self.rodar(*self.base("PETR4", "HGLG11"))
        self.assertEqual((code, err), (0, ""))
        self.assertIn("49,69", out)
        self.assertIn("165,00", out)
        code, out, _ = self.rodar("historico", "--historico", str(self.hist))
        self.assertEqual(code, 0)
        self.assertIn("PETR4", out)

    def test_acao_sem_k_da_erro_claro(self):
        code, out, err = self.rodar(*self.base("PETR4", k=None))
        self.assertEqual(code, 1)
        self.assertIn("retorno exigido k", err)
        self.assertNotIn("salvos", out)

    def test_k_aceita_percentual_ou_decimal(self):
        for k in ("0.12", "12", "12%"):
            with self.subTest(k=k):
                code, out, _ = self.rodar(*self.base("PETR4", k=k), "--sem-salvar")
                self.assertEqual(code, 0)
                self.assertIn("49,69", out)

    def test_tabelas_e_exportacao_csv(self):
        pasta = Path(self._tmp.name) / "csv"
        code, out, _ = self.rodar(*self.base("PETR4"), "--tabelas", "--exportar-csv", str(pasta))
        self.assertEqual(code, 0)
        self.assertIn("Tabela anual - PETR4", out)
        tabela = (pasta / "PETR4_tabela_anual.csv").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(tabela), 11)  # cabeçalho + 10 anos
        stats = (pasta / "PETR4_estatisticas.csv").read_text(encoding="utf-8")
        self.assertIn("ROE", stats)

    def test_analisar_sem_k(self):
        code, out, err = self.rodar("analisar", "TAEE11", "--fonte", "arquivo", "--pasta-dados", str(EXEMPLOS),
                                    "--estat-roe", "mediana")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("g = ROE x (1 - payout)", out)
        self.assertFalse(self.hist.exists())  # analisar não grava histórico

    def test_erro_retorna_codigo_1_e_mensagem_clara(self):
        code, out, err = self.rodar(*self.base("BOVA11"))
        self.assertEqual(code, 1)
        self.assertIn("ERRO [BOVA11]", err)
        self.assertNotIn("salvos", out)  # sem mensagem de sucesso falsa

    def test_parametro_invalido_retorna_2(self):
        code, _, err = self.rodar(*self.base("PETR4", k="0"))
        self.assertEqual(code, 2)
        self.assertIn("ERRO", err)

    def test_historico_corrompido(self):
        self.hist.write_text("[", encoding="utf-8")
        code, _, err = self.rodar("historico", "--historico", str(self.hist))
        self.assertEqual(code, 2)
        self.assertIn("ERRO", err)


if __name__ == "__main__":
    unittest.main()

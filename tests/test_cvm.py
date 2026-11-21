import io
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path

from preco_teto.exceptions import DadosInvalidosError, ProvedorIndisponivelError
from preco_teto.provedores.cvm import (
    ClienteCVM, CompanhiaCVM, ContaContabilCVM, _numero, _normalizar_coluna,
)


def zip_csv(entries):
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as z:
        for nome, conteudo in entries.items():
            z.writestr(nome, conteudo.encode("latin-1"))
    return memoria.getvalue()


class Resposta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class TestNormalizacao(unittest.TestCase):
    def test_normaliza_cabecalho(self):
        self.assertEqual(_normalizar_coluna("Código de Negociação"), "CODIGODENEGOCIACAO")

    def test_numero_brasileiro(self):
        self.assertEqual(_numero("1.234,56"), 1234.56)
        self.assertEqual(_numero("1234.56"), 1234.56)
        self.assertIsNone(_numero(""))

    def test_escala_monetaria(self):
        c = ContaContabilCVM(
            "DRE", date(2025, 12, 31), None, "DF Consolidado", "ÚLTIMO",
            "3.11", "Lucro", 12.5, "MIL", "REAL", "1", None, "S", "arquivo.csv"
        )
        self.assertEqual(c.valor, 12500.0)


class TestClienteCVM(unittest.TestCase):
    def test_resolve_ticker_por_fca(self):
        fca = zip_csv({
            "fca_cia_aberta_valor_mobiliario.csv":
                "CD_CVM;CNPJ_CIA;CODIGO_NEGOCIACAO\n5410;84.429.695/0001-11;WEGE3\n",
            "fca_cia_aberta_geral.csv":
                "CD_CVM;CNPJ_CIA;DENOM_CIA\n5410;84.429.695/0001-11;WEG S.A.\n",
        })
        cliente = ClienteCVM(
            cache_dir=tempfile.mkdtemp(), ano_atual=2026,
            abrir_url=lambda req, timeout: Resposta(fca),
        )
        companhia = cliente.buscar_companhia("wege3")
        self.assertEqual(companhia, CompanhiaCVM(
            "WEGE3", "5410", "84.429.695/0001-11", "WEG S.A.", 2026
        ))

    def test_rejeita_zip_invalido(self):
        cliente = ClienteCVM(
            cache_dir=tempfile.mkdtemp(), ano_atual=2026,
            abrir_url=lambda req, timeout: Resposta(b"nao e zip"),
        )
        with self.assertRaises(DadosInvalidosError):
            cliente._baixar_zip("https://exemplo.invalid/dados.zip", Path(tempfile.mkdtemp()) / "x.zip")

    def test_erro_de_rede(self):
        def falha(req, timeout):
            raise OSError("offline")
        cliente = ClienteCVM(cache_dir=tempfile.mkdtemp(), abrir_url=falha, ano_atual=2026)
        with self.assertRaises(ProvedorIndisponivelError):
            cliente._baixar_zip("https://exemplo.invalid/dados.zip", Path(tempfile.mkdtemp()) / "x.zip")

    def test_dedup_usa_versao_e_data_de_recebimento(self):
        def conta(versao, recebimento, valor):
            return ContaContabilCVM(
                "DRE", date(2025, 12, 31), date(2025, 12, 31), "DF Consolidado",
                "ÚLTIMO", "3.11", "Lucro", valor, "MIL", "REAL", versao,
                recebimento, "S", "dfp.csv"
            )
        resultado = ClienteCVM._deduplicar([
            conta("1", date(2026, 3, 1), 100),
            conta("2", date(2026, 4, 1), 120),
        ])
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0].valor_original, 120)


if __name__ == "__main__":
    unittest.main()

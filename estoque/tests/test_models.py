"""
Testes unitários dos modelos de estoque.

Cobrem as propriedades calculadas de Produto (estoque_baixo, status_validade,
dias_para_vencer) que sustentam os alertas do dashboard, os badges da lista
de produtos e os filtros.
"""
from datetime import date, timedelta

from django.test import TestCase

from estoque.models import Categoria, Produto, Medicamento, DIAS_AVISO_VENCIMENTO


class ProdutoEstoqueBaixoTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nome='Analgésicos')

    def _criar_produto(self, quantidade, estoque_minimo=10):
        return Produto.objects.create(
            nome='Dipirona',
            categoria=self.categoria,
            quantidade=quantidade,
            estoque_minimo=estoque_minimo,
        )

    def test_estoque_abaixo_do_minimo_e_considerado_baixo(self):
        produto = self._criar_produto(quantidade=5, estoque_minimo=10)
        self.assertTrue(produto.estoque_baixo)

    def test_estoque_igual_ao_minimo_e_considerado_baixo(self):
        # A regra é "<=", não só "<" — exatamente no limite já deve alertar.
        produto = self._criar_produto(quantidade=10, estoque_minimo=10)
        self.assertTrue(produto.estoque_baixo)

    def test_estoque_acima_do_minimo_nao_e_considerado_baixo(self):
        produto = self._criar_produto(quantidade=50, estoque_minimo=10)
        self.assertFalse(produto.estoque_baixo)

    def test_produto_sem_quantidade_definida_nao_e_considerado_baixo(self):
        # quantidade=None não deve comparar com o mínimo e quebrar o template.
        produto = self._criar_produto(quantidade=None)
        self.assertFalse(produto.estoque_baixo)


class ProdutoStatusValidadeTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nome='Vitaminas')
        self.hoje = date.today()

    def _criar_produto(self, data_validade):
        return Produto.objects.create(
            nome='Vitamina C',
            categoria=self.categoria,
            quantidade=20,
            data_validade=data_validade,
        )

    def test_sem_data_validade_status_e_none(self):
        produto = self._criar_produto(data_validade=None)
        self.assertIsNone(produto.status_validade)
        self.assertFalse(produto.esta_vencido)
        self.assertFalse(produto.vencimento_proximo)

    def test_validade_distante_e_normal(self):
        produto = self._criar_produto(self.hoje + timedelta(days=DIAS_AVISO_VENCIMENTO + 10))
        self.assertEqual(produto.status_validade, 'normal')

    def test_validade_dentro_da_janela_de_aviso_e_vencimento_proximo(self):
        produto = self._criar_produto(self.hoje + timedelta(days=DIAS_AVISO_VENCIMENTO - 1))
        self.assertEqual(produto.status_validade, 'aviso')
        self.assertTrue(produto.vencimento_proximo)
        self.assertFalse(produto.esta_vencido)

    def test_validade_no_limite_exato_da_janela_ainda_e_aviso(self):
        produto = self._criar_produto(self.hoje + timedelta(days=DIAS_AVISO_VENCIMENTO))
        self.assertEqual(produto.status_validade, 'aviso')

    def test_validade_no_passado_e_vencido(self):
        produto = self._criar_produto(self.hoje - timedelta(days=1))
        self.assertEqual(produto.status_validade, 'vencido')
        self.assertTrue(produto.esta_vencido)

    def test_validade_hoje_ainda_nao_e_vencido(self):
        produto = self._criar_produto(self.hoje)
        self.assertEqual(produto.status_validade, 'aviso')

    def test_dias_para_vencer_calcula_diferenca_correta(self):
        produto = self._criar_produto(self.hoje + timedelta(days=7))
        self.assertEqual(produto.dias_para_vencer, 7)

    def test_dias_para_vencer_negativo_quando_ja_venceu(self):
        produto = self._criar_produto(self.hoje - timedelta(days=3))
        self.assertEqual(produto.dias_para_vencer, -3)


class MedicamentoHerdaDeProdutoTests(TestCase):
    def test_medicamento_tem_os_campos_de_produto_e_os_proprios(self):
        categoria = Categoria.objects.create(nome='Antibióticos')
        medicamento = Medicamento.objects.create(
            nome='Amoxicilina',
            dosagem='500mg',
            categoria=categoria,
            quantidade=30,
            estoque_minimo=15,
        )
        # Herda a lógica de Produto (multi-table inheritance) sem reescrevê-la.
        self.assertFalse(medicamento.estoque_baixo)
        medicamento.quantidade = 5
        self.assertTrue(medicamento.estoque_baixo)
        self.assertEqual(str(medicamento), 'Amoxicilina - 500mg')


class CategoriaTests(TestCase):
    def test_str_retorna_o_nome(self):
        categoria = Categoria.objects.create(nome='Higiene')
        self.assertEqual(str(categoria), 'Higiene')

    def test_nome_e_unico(self):
        Categoria.objects.create(nome='Higiene')
        with self.assertRaises(Exception):
            Categoria.objects.create(nome='Higiene')

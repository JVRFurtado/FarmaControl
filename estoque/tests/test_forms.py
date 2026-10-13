"""
Testes das regras de validação dos formulários, (campos obrigatórios, datas não
podem estar vencidas, quantidades não podem ser negativas).
"""
from datetime import date, timedelta

from django.test import TestCase

from estoque.models import Categoria
from estoque.forms import ProdutoForm, MedicamentoForm, CategoriaForm, EntregaForm


class ProdutoFormTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nome='Analgésicos')

    def _dados_validos(self, **overrides):
        dados = {
            'nome': 'Paracetamol',
            'categoria': self.categoria.id,
            'quantidade': 10,
            'estoque_minimo': 5,
            'data_validade': (date.today() + timedelta(days=90)).isoformat(),
            'ultima_compra': date.today().isoformat(),
        }
        dados.update(overrides)
        return dados

    def test_formulario_valido_com_todos_os_campos_obrigatorios(self):
        form = ProdutoForm(data=self._dados_validos())
        self.assertTrue(form.is_valid(), form.errors)

    def test_nome_em_branco_e_invalido(self):
        form = ProdutoForm(data=self._dados_validos(nome=''))
        self.assertFalse(form.is_valid())
        self.assertIn('nome', form.errors)

    def test_categoria_em_branco_e_invalida(self):
        form = ProdutoForm(data=self._dados_validos(categoria=''))
        self.assertFalse(form.is_valid())
        self.assertIn('categoria', form.errors)

    def test_campos_opcionais_podem_ficar_em_branco(self):
        dados = self._dados_validos(quantidade='', altura='', largura='', comprimento='')
        form = ProdutoForm(data=dados)
        self.assertTrue(form.is_valid(), form.errors)

    def test_quantidade_negativa_e_invalida(self):
        form = ProdutoForm(data=self._dados_validos(quantidade=-5))
        self.assertFalse(form.is_valid())
        self.assertIn('quantidade', form.errors)

    def test_data_validade_no_passado_e_invalida(self):
        ontem = (date.today() - timedelta(days=1)).isoformat()
        form = ProdutoForm(data=self._dados_validos(data_validade=ontem))
        self.assertFalse(form.is_valid())
        self.assertIn('data_validade', form.errors)

    def test_data_validade_hoje_e_valida(self):
        form = ProdutoForm(data=self._dados_validos(data_validade=date.today().isoformat()))
        self.assertTrue(form.is_valid(), form.errors)

    def test_altura_negativa_e_invalida(self):
        form = ProdutoForm(data=self._dados_validos(altura=-1))
        self.assertFalse(form.is_valid())
        self.assertIn('altura', form.errors)


class MedicamentoFormTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nome='Antibióticos')

    def _dados_validos(self, **overrides):
        dados = {
            'nome': 'Amoxicilina',
            'dosagem': '500mg',
            'categoria': self.categoria.id,
            'quantidade': 20,
            'estoque_minimo': 5,
            'data_validade': (date.today() + timedelta(days=60)).isoformat(),
            'ultima_compra': date.today().isoformat(),
        }
        dados.update(overrides)
        return dados

    def test_formulario_valido(self):
        form = MedicamentoForm(data=self._dados_validos())
        self.assertTrue(form.is_valid(), form.errors)

    def test_dosagem_em_branco_e_invalida(self):
        form = MedicamentoForm(data=self._dados_validos(dosagem=''))
        self.assertFalse(form.is_valid())
        self.assertIn('dosagem', form.errors)

    def test_data_validade_vencida_e_invalida(self):
        ontem = (date.today() - timedelta(days=1)).isoformat()
        form = MedicamentoForm(data=self._dados_validos(data_validade=ontem))
        self.assertFalse(form.is_valid())


class CategoriaFormTests(TestCase):
    def test_nome_obrigatorio(self):
        form = CategoriaForm(data={'nome': ''})
        self.assertFalse(form.is_valid())

    def test_nome_duplicado_e_invalido(self):
        Categoria.objects.create(nome='Higiene')
        form = CategoriaForm(data={'nome': 'Higiene'})
        self.assertFalse(form.is_valid())


class EntregaFormTests(TestCase):
    def test_formulario_valido(self):
        form = EntregaForm(data={
            'paciente': 'Maria Silva',
            'data_entrega': date.today().isoformat(),
            'quantidade': 2,
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_quantidade_zero_e_invalida(self):
        # min_value=1 no campo: zero ou negativo não é uma entrega válida.
        form = EntregaForm(data={
            'paciente': 'Maria Silva',
            'data_entrega': date.today().isoformat(),
            'quantidade': 0,
        })
        self.assertFalse(form.is_valid())

    def test_paciente_em_branco_e_invalido(self):
        form = EntregaForm(data={
            'paciente': '',
            'data_entrega': date.today().isoformat(),
            'quantidade': 1,
        })
        self.assertFalse(form.is_valid())

"""
O ProdutoQuerySet (filtros no banco) tem que dar exatamente o mesmo
resultado que as propriedades calculadas de Produto (regra em Python).
Estes testes montam produtos em cada situação possível e comparam as duas
formas.
"""
from datetime import date, timedelta

from django.test import TestCase

from estoque.models import DIAS_AVISO_VENCIMENTO, Categoria, Produto


class ProdutoQuerySetTests(TestCase):
    def setUp(self):
        categoria = Categoria.objects.create(nome='Teste')
        hoje = date.today()
        cenarios = [
            # (nome, quantidade, minimo, validade)
            ('baixo-sem-validade', 2, 10, None),
            ('no-limite-do-minimo', 10, 10, hoje + timedelta(days=200)),
            ('acima-do-minimo', 50, 10, hoje + timedelta(days=200)),
            ('quantidade-nula', None, 10, None),
            ('vencido-ontem', 20, 10, hoje - timedelta(days=1)),
            ('vence-hoje', 20, 10, hoje),
            ('limite-da-janela', 20, 10, hoje + timedelta(days=DIAS_AVISO_VENCIMENTO)),
            ('logo-apos-a-janela', 20, 10, hoje + timedelta(days=DIAS_AVISO_VENCIMENTO + 1)),
        ]
        for nome, qtd, minimo, validade in cenarios:
            Produto.objects.create(
                nome=nome, categoria=categoria, quantidade=qtd,
                estoque_minimo=minimo, data_validade=validade,
            )

    def _nomes(self, queryset):
        return sorted(p.nome for p in queryset)

    def _nomes_por_propriedade(self, predicado):
        return sorted(p.nome for p in Produto.objects.all() if predicado(p))

    def test_estoque_baixo_bate_com_a_propriedade(self):
        self.assertEqual(
            self._nomes(Produto.objects.estoque_baixo()),
            self._nomes_por_propriedade(lambda p: p.estoque_baixo),
        )

    def test_vencidos_bate_com_a_propriedade(self):
        self.assertEqual(
            self._nomes(Produto.objects.vencidos()),
            self._nomes_por_propriedade(lambda p: p.esta_vencido),
        )

    def test_vencendo_bate_com_a_propriedade(self):
        self.assertEqual(
            self._nomes(Produto.objects.vencendo()),
            self._nomes_por_propriedade(lambda p: p.vencimento_proximo),
        )

    def test_validade_normal_bate_com_a_propriedade(self):
        self.assertEqual(
            self._nomes(Produto.objects.validade_normal()),
            self._nomes_por_propriedade(lambda p: p.status_validade == 'normal'),
        )

    def test_resultados_concretos_nos_limites(self):
        self.assertEqual(self._nomes(Produto.objects.vencidos()), ['vencido-ontem'])
        self.assertEqual(
            self._nomes(Produto.objects.vencendo()),
            ['limite-da-janela', 'vence-hoje'],
        )
        self.assertIn('no-limite-do-minimo', self._nomes(Produto.objects.estoque_baixo()))
        self.assertNotIn('quantidade-nula', self._nomes(Produto.objects.estoque_baixo()))

    def test_por_filtro_despacha_pelo_nome(self):
        self.assertEqual(
            self._nomes(Produto.objects.por_filtro('vencidos')),
            self._nomes(Produto.objects.vencidos()),
        )

    def test_por_filtro_desconhecido_ou_vazio_nao_filtra(self):
        total = Produto.objects.count()
        self.assertEqual(Produto.objects.por_filtro('').count(), total)
        self.assertEqual(Produto.objects.por_filtro('qualquer-coisa').count(), total)

    def test_filtros_encadeiam_com_outros_filtros(self):
        resultado = Produto.objects.filter(nome__startswith='vence').vencendo()
        self.assertEqual(self._nomes(resultado), ['vence-hoje'])

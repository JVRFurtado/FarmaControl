"""
Testes de integração das views de estoque: login + requisição real via
Client, cobrindo permissões (quem pode fazer o quê), o fluxo completo de
cadastro/entrega/exclusão de produto, e o histórico de movimentações que
essas ações devem gerar.
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from estoque.models import Categoria, Produto, Entrega, MovimentacaoEstoque

Users = get_user_model()


class PermissoesEstoqueTests(TestCase):
    """Cobre a regra: Atendente usa o estoque no dia a dia, mas só o Gestor
    (ou Admin) pode excluir produtos e categorias."""

    def setUp(self):
        self.categoria = Categoria.objects.create(nome='Analgésicos')
        self.produto = Produto.objects.create(
            nome='Dipirona', categoria=self.categoria, quantidade=20, estoque_minimo=5,
        )
        self.gestor = Users.objects.create_user('gestor1', 'gestor1@teste.com', 'SenhaForte123', cargo='G')
        self.atendente = Users.objects.create_user('atendente1', 'atendente1@teste.com', 'SenhaForte123', cargo='A')

    def test_usuario_anonimo_e_redirecionado_para_login(self):
        resposta = self.client.get(reverse('lista_produtos'))
        self.assertEqual(resposta.status_code, 302)
        self.assertIn('/login', resposta.url)

    def test_atendente_consegue_ver_a_lista_de_produtos(self):
        self.client.force_login(self.atendente)
        resposta = self.client.get(reverse('lista_produtos'))
        self.assertEqual(resposta.status_code, 200)

    def test_atendente_nao_pode_excluir_produto(self):
        self.client.force_login(self.atendente)
        resposta = self.client.post(reverse('excluir_produto', args=[self.produto.id]))
        self.assertEqual(resposta.status_code, 403)
        self.assertTrue(Produto.objects.filter(id=self.produto.id).exists())

    def test_gestor_pode_excluir_produto(self):
        self.client.force_login(self.gestor)
        resposta = self.client.post(reverse('excluir_produto', args=[self.produto.id]))
        self.assertEqual(resposta.status_code, 302)
        self.assertFalse(Produto.objects.filter(id=self.produto.id).exists())

    def test_atendente_nao_pode_editar_produto(self):
        # Regressão: a tela só mostrava o link "Editar" para Gestor, mas a
        # view aceitava qualquer usuário logado. Um Atendente que soubesse
        # a URL conseguia editar produtos diretamente — corrigido para
        # exigir @gestor_required, igual à exclusão.
        self.client.force_login(self.atendente)
        resposta = self.client.get(reverse('editar_produto', args=[self.produto.id]))
        self.assertEqual(resposta.status_code, 403)

    def test_gestor_pode_editar_produto(self):
        self.client.force_login(self.gestor)
        resposta = self.client.get(reverse('editar_produto', args=[self.produto.id]))
        self.assertEqual(resposta.status_code, 200)

    def test_gestor_edita_produto_com_sucesso_e_ajuste_de_quantidade_vira_movimentacao(self):
        self.client.force_login(self.gestor)
        resposta = self.client.post(reverse('editar_produto', args=[self.produto.id]), {
            'nome': self.produto.nome,
            'categoria': self.categoria.id,
            'quantidade': 35,  # era 20
            'estoque_minimo': self.produto.estoque_minimo,
            'data_validade': '',
            'ultima_compra': '',
        })
        self.assertEqual(resposta.status_code, 302)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade, 35)

        movimentacao = MovimentacaoEstoque.objects.filter(
            produto=self.produto, motivo_codigo=MovimentacaoEstoque.MOTIVO_AJUSTE_MANUAL,
        ).first()
        self.assertIsNotNone(movimentacao)
        self.assertEqual(movimentacao.tipo, MovimentacaoEstoque.ENTRADA)
        self.assertEqual(movimentacao.quantidade, 15)

    def test_excluir_produto_via_get_mostra_confirmacao_sem_excluir(self):
        self.client.force_login(self.gestor)
        resposta = self.client.get(reverse('excluir_produto', args=[self.produto.id]))
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(Produto.objects.filter(id=self.produto.id).exists())


class CadastroDeProdutoTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nome='Vitaminas')
        self.atendente = Users.objects.create_user('atendente2', 'atendente2@teste.com', 'SenhaForte123', cargo='A')
        self.client.force_login(self.atendente)

    def test_cadastrar_produto_com_quantidade_inicial_gera_movimentacao_de_entrada(self):
        resposta = self.client.post(reverse('adicionar_produto'), {
            'nome': 'Vitamina D',
            'categoria': self.categoria.id,
            'quantidade': 50,
            'estoque_minimo': 10,
            'data_validade': (date.today() + timedelta(days=120)).isoformat(),
            'ultima_compra': date.today().isoformat(),
        })
        self.assertEqual(resposta.status_code, 302)
        produto = Produto.objects.get(nome='Vitamina D')
        self.assertEqual(produto.quantidade, 50)

        movimentacao = MovimentacaoEstoque.objects.get(produto=produto)
        self.assertEqual(movimentacao.tipo, MovimentacaoEstoque.ENTRADA)
        self.assertEqual(movimentacao.quantidade, 50)
        self.assertEqual(movimentacao.motivo_codigo, MovimentacaoEstoque.MOTIVO_CADASTRO_PRODUTO)

    def test_cadastrar_produto_duplicado_nao_salva_de_novo(self):
        dados = {
            'nome': 'Vitamina D',
            'categoria': self.categoria.id,
            'quantidade': 50,
            'estoque_minimo': 10,
            'data_validade': (date.today() + timedelta(days=120)).isoformat(),
            'ultima_compra': date.today().isoformat(),
        }
        self.client.post(reverse('adicionar_produto'), dados)
        self.client.post(reverse('adicionar_produto'), dados)
        self.assertEqual(Produto.objects.filter(nome='Vitamina D').count(), 1)


class EntregaDeProdutoTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nome='Analgésicos')
        self.produto = Produto.objects.create(
            nome='Dipirona', categoria=self.categoria, quantidade=10, estoque_minimo=5,
        )
        self.atendente = Users.objects.create_user('atendente3', 'atendente3@teste.com', 'SenhaForte123', cargo='A')
        self.client.force_login(self.atendente)

    def test_entrega_reduz_o_estoque_e_registra_historico(self):
        resposta = self.client.post(reverse('entregar_produto', args=[self.produto.id]), {
            'paciente': 'João Souza',
            'data_entrega': date.today().isoformat(),
            'quantidade': 3,
        })
        self.assertEqual(resposta.status_code, 302)

        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade, 7)

        entrega = Entrega.objects.get(produto=self.produto)
        self.assertEqual(entrega.paciente, 'João Souza')
        self.assertEqual(entrega.quantidade, 3)

        movimentacao = MovimentacaoEstoque.objects.get(produto=self.produto, tipo=MovimentacaoEstoque.SAIDA)
        self.assertEqual(movimentacao.motivo_codigo, MovimentacaoEstoque.MOTIVO_ENTREGA)
        self.assertEqual(movimentacao.motivo_detalhe, 'João Souza')

    def test_entrega_maior_que_o_estoque_e_bloqueada(self):
        resposta = self.client.post(reverse('entregar_produto', args=[self.produto.id]), {
            'paciente': 'João Souza',
            'data_entrega': date.today().isoformat(),
            'quantidade': 999,
        })
        self.assertEqual(resposta.status_code, 200)  # não redireciona: fica na mesma página com erro
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade, 10)  # estoque não mudou
        self.assertFalse(Entrega.objects.filter(produto=self.produto).exists())


class FiltroDeEstoqueTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nome='Analgésicos')
        self.atendente = Users.objects.create_user('atendente4', 'atendente4@teste.com', 'SenhaForte123', cargo='A')
        self.client.force_login(self.atendente)

        self.produto_baixo = Produto.objects.create(
            nome='Produto Baixo', categoria=self.categoria, quantidade=2, estoque_minimo=10,
        )
        self.produto_normal = Produto.objects.create(
            nome='Produto Normal', categoria=self.categoria, quantidade=100, estoque_minimo=10,
        )

    def test_filtro_estoque_baixo_mostra_so_produtos_abaixo_do_minimo(self):
        resposta = self.client.get(reverse('lista_produtos'), {'filtro': 'estoque_baixo'})
        produtos = list(resposta.context['produtos'])
        self.assertIn(self.produto_baixo, produtos)
        self.assertNotIn(self.produto_normal, produtos)

    def test_sem_filtro_mostra_todos_os_produtos(self):
        resposta = self.client.get(reverse('lista_produtos'))
        produtos = list(resposta.context['produtos'])
        self.assertIn(self.produto_baixo, produtos)
        self.assertIn(self.produto_normal, produtos)

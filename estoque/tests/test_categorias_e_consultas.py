"""
Testes das telas que o primeiro lote de testes não cobriu: categorias,
históricos de entrega/movimentação, relatórios (tela + exportação) e
análises.
"""
import json
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from estoque.models import Categoria, Produto, Entrega, MovimentacaoEstoque

Users = get_user_model()


def _criar_usuario(username, cargo='A'):
    return Users.objects.create_user(username=username, email=f'{username}@teste.com', password='SenhaForte123', cargo=cargo)


class CategoriaViewsTests(TestCase):
    def setUp(self):
        self.gestor = _criar_usuario('gestor_cat', cargo='G')
        self.atendente = _criar_usuario('atendente_cat', cargo='A')
        self.categoria = Categoria.objects.create(nome='Analgésicos')

    def test_lista_categorias_acessivel_a_qualquer_logado(self):
        self.client.force_login(self.atendente)
        resposta = self.client.get(reverse('lista_categorias'))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Analgésicos')

    def test_atendente_pode_cadastrar_categoria(self):
        # Decisão deliberada da Fase 2: qualquer logado pode cadastrar
        # categoria, pra não travar o cadastro de produto por falta de opção.
        self.client.force_login(self.atendente)
        resposta = self.client.post(reverse('adicionar_categoria'), {'nome': 'Antibióticos'})
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(Categoria.objects.filter(nome='Antibióticos').exists())

    def test_adicionar_categoria_redireciona_para_next_quando_informado(self):
        self.client.force_login(self.atendente)
        destino = reverse('adicionar_produto')
        resposta = self.client.post(reverse('adicionar_categoria') + f'?next={destino}', {'nome': 'Higiene'})
        self.assertRedirects(resposta, destino)

    def test_atendente_nao_pode_excluir_categoria(self):
        self.client.force_login(self.atendente)
        resposta = self.client.post(reverse('excluir_categoria', args=[self.categoria.id]))
        self.assertEqual(resposta.status_code, 403)
        self.assertTrue(Categoria.objects.filter(id=self.categoria.id).exists())

    def test_gestor_pode_excluir_categoria(self):
        self.client.force_login(self.gestor)
        resposta = self.client.post(reverse('excluir_categoria', args=[self.categoria.id]))
        self.assertEqual(resposta.status_code, 302)
        self.assertFalse(Categoria.objects.filter(id=self.categoria.id).exists())

    def test_excluir_categoria_desvincula_produtos_em_vez_de_apagar(self):
        produto = Produto.objects.create(nome='Dipirona', categoria=self.categoria, quantidade=10)
        self.client.force_login(self.gestor)
        self.client.post(reverse('excluir_categoria', args=[self.categoria.id]))
        produto.refresh_from_db()
        self.assertIsNone(produto.categoria)
        self.assertTrue(Produto.objects.filter(id=produto.id).exists())


class HistoricoViewsTests(TestCase):
    def setUp(self):
        self.atendente = _criar_usuario('atendente_hist', cargo='A')
        self.categoria = Categoria.objects.create(nome='Analgésicos')
        self.produto = Produto.objects.create(nome='Dipirona', categoria=self.categoria, quantidade=10)
        self.client.force_login(self.atendente)

    def test_historico_entregas_lista_entregas_existentes(self):
        Entrega.objects.create(
            produto=self.produto, produto_nome=self.produto.nome, paciente='Maria',
            quantidade=2, data_entrega=date.today(),
        )
        resposta = self.client.get(reverse('historico_entregas'))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Maria')

    def test_historico_entregas_filtra_por_busca(self):
        Entrega.objects.create(
            produto=self.produto, produto_nome=self.produto.nome, paciente='Maria',
            quantidade=2, data_entrega=date.today(),
        )
        resposta = self.client.get(reverse('historico_entregas'), {'buscar': 'nome-que-nao-existe'})
        self.assertNotContains(resposta, 'Maria')

    def test_historico_movimentacoes_lista_e_filtra_por_tipo(self):
        MovimentacaoEstoque.objects.create(
            produto=self.produto, produto_nome=self.produto.nome, tipo=MovimentacaoEstoque.ENTRADA,
            quantidade=10, motivo='Cadastro inicial do produto',
            motivo_codigo=MovimentacaoEstoque.MOTIVO_CADASTRO_PRODUTO,
        )
        resposta = self.client.get(reverse('historico_movimentacoes'))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.context['movimentacoes']), 1)

        resposta_saida = self.client.get(reverse('historico_movimentacoes'), {'tipo': 'SAIDA'})
        self.assertEqual(len(resposta_saida.context['movimentacoes']), 0)

    def test_historico_movimentacoes_traduz_o_motivo_pelo_codigo(self):
        MovimentacaoEstoque.objects.create(
            produto=self.produto, produto_nome=self.produto.nome, tipo=MovimentacaoEstoque.SAIDA,
            quantidade=3, motivo='Entrega para João',
            motivo_codigo=MovimentacaoEstoque.MOTIVO_ENTREGA, motivo_detalhe='João',
        )
        resposta = self.client.get(reverse('historico_movimentacoes'))
        self.assertContains(resposta, 'Entrega para')
        self.assertContains(resposta, 'João')


class RelatoriosViewsTests(TestCase):
    def setUp(self):
        self.atendente = _criar_usuario('atendente_rel', cargo='A')
        self.categoria = Categoria.objects.create(nome='Analgésicos')
        Produto.objects.create(nome='Dipirona', categoria=self.categoria, quantidade=2, estoque_minimo=10)
        Produto.objects.create(nome='Paracetamol', categoria=self.categoria, quantidade=100, estoque_minimo=10)
        self.client.force_login(self.atendente)

    def test_relatorio_estoque_mostra_todos_os_produtos(self):
        resposta = self.client.get(reverse('relatorios'), {'tipo': 'estoque'})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context['total_linhas'], 2)

    def test_relatorio_estoque_baixo_filtra_corretamente(self):
        resposta = self.client.get(reverse('relatorios'), {'tipo': 'estoque_baixo'})
        self.assertEqual(resposta.context['total_linhas'], 1)

    def test_tipo_invalido_cai_no_padrao_estoque(self):
        resposta = self.client.get(reverse('relatorios'), {'tipo': 'nao-existe'})
        self.assertEqual(resposta.context['tipo_selecionado'], 'estoque')

    def test_exportar_csv_retorna_arquivo(self):
        resposta = self.client.get(reverse('relatorios'), {'tipo': 'estoque', 'formato': 'csv'})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta['Content-Type'], 'text/csv; charset=utf-8')

    def test_exportar_xlsx_retorna_arquivo(self):
        resposta = self.client.get(reverse('relatorios'), {'tipo': 'estoque', 'formato': 'xlsx'})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            resposta['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )


class AnalisesViewsTests(TestCase):
    def setUp(self):
        self.atendente = _criar_usuario('atendente_an', cargo='A')
        self.client.force_login(self.atendente)

    def test_sem_produtos_mostra_aviso_de_sem_dados(self):
        resposta = self.client.get(reverse('analises'))
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.context['sem_dados'])

    def test_com_produtos_monta_os_dados_dos_graficos(self):
        categoria = Categoria.objects.create(nome='Analgésicos')
        Produto.objects.create(nome='Dipirona', categoria=categoria, quantidade=10)
        resposta = self.client.get(reverse('analises'))
        self.assertFalse(resposta.context['sem_dados'])
        # labels_categoria chega na context já como string JSON (é injetada
        # direto no <script> do template), por isso precisa ser decodificada
        # antes de verificar o conteúdo.
        labels = json.loads(resposta.context['labels_categoria'])
        self.assertIn('Analgésicos', labels)

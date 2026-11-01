"""
Testes dos comportamentos novos/ajustados na refatoração: paginação,
cadastro de medicamento (fluxo compartilhado com produto), edição de produto
já vencido, entrega sobre produto sem saldo definido, POST vazio, exclusão
com rastro no histórico, e relatórios via módulo próprio.
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from estoque.models import Categoria, Entrega, Medicamento, MovimentacaoEstoque, Produto
from estoque.relatorios import montar_relatorio, parse_data
from farmacontrol.paginacao import ITENS_POR_PAGINA

Users = get_user_model()


def _usuario(username, cargo='A'):
    return Users.objects.create_user(
        username=username, email=f'{username}@teste.com', password='SenhaForte123', cargo=cargo)


class PaginacaoDaListaTests(TestCase):
    def setUp(self):
        categoria = Categoria.objects.create(nome='Lote')
        Produto.objects.bulk_create([
            Produto(nome=f'Item {i:03d}', categoria=categoria, quantidade=1, estoque_minimo=5)
            for i in range(ITENS_POR_PAGINA + 5)
        ])
        self.client.force_login(_usuario('pag_atendente'))

    def test_primeira_pagina_tem_o_limite_de_itens(self):
        resposta = self.client.get(reverse('lista_produtos'))
        self.assertEqual(len(resposta.context['produtos']), ITENS_POR_PAGINA)
        self.assertTrue(resposta.context['produtos'].has_next())

    def test_segunda_pagina_tem_o_resto(self):
        resposta = self.client.get(reverse('lista_produtos'), {'page': 2})
        self.assertEqual(len(resposta.context['produtos']), 5)

    def test_link_da_proxima_pagina_preserva_o_filtro(self):
        resposta = self.client.get(reverse('lista_produtos'), {'filtro': 'estoque_baixo'})
        self.assertContains(resposta, 'filtro=estoque_baixo&amp;page=2')

    def test_pagina_invalida_nao_quebra(self):
        resposta = self.client.get(reverse('lista_produtos'), {'page': 'abc'})
        self.assertEqual(resposta.status_code, 200)


class CadastroDeMedicamentoTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nome='Antibióticos')
        self.client.force_login(_usuario('med_atendente'))
        self.dados = {
            'nome': 'Amoxicilina', 'dosagem': '500mg', 'categoria': self.categoria.id,
            'quantidade': 30, 'estoque_minimo': 10,
            'data_validade': (date.today() + timedelta(days=90)).isoformat(),
            'ultima_compra': date.today().isoformat(),
        }

    def test_cadastro_cria_medicamento_e_registra_entrada(self):
        resposta = self.client.post(reverse('adicionar_medicamento'), self.dados)
        self.assertEqual(resposta.status_code, 302)
        medicamento = Medicamento.objects.get(nome='Amoxicilina')
        mov = MovimentacaoEstoque.objects.get(produto=medicamento)
        self.assertEqual(mov.tipo, MovimentacaoEstoque.ENTRADA)
        self.assertEqual(mov.quantidade, 30)
        self.assertEqual(mov.motivo_codigo, MovimentacaoEstoque.MOTIVO_CADASTRO_MEDICAMENTO)

    def test_medicamento_duplicado_nao_e_criado_de_novo(self):
        self.client.post(reverse('adicionar_medicamento'), self.dados)
        self.client.post(reverse('adicionar_medicamento'), self.dados)
        self.assertEqual(Medicamento.objects.filter(nome='Amoxicilina').count(), 1)
        self.assertEqual(MovimentacaoEstoque.objects.count(), 1)

    def test_cadastro_sem_quantidade_nao_gera_movimentacao(self):
        self.dados['quantidade'] = ''
        self.client.post(reverse('adicionar_medicamento'), self.dados)
        self.assertTrue(Medicamento.objects.filter(nome='Amoxicilina').exists())
        self.assertEqual(MovimentacaoEstoque.objects.count(), 0)


class FormularioVazioTests(TestCase):
    def test_post_totalmente_vazio_mostra_os_erros_de_campo(self):
        self.client.force_login(_usuario('vazio_atendente'))
        resposta = self.client.post(reverse('adicionar_produto'), {})
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.context['form'].is_bound)
        self.assertIn('nome', resposta.context['form'].errors)


class EdicaoDeProdutoVencidoTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nome='Antigos')
        self.validade_antiga = date.today() - timedelta(days=10)
        self.produto = Produto.objects.create(
            nome='Xarope Velho', categoria=self.categoria, quantidade=5,
            estoque_minimo=2, data_validade=self.validade_antiga,
        )
        self.client.force_login(_usuario('ed_gestor', cargo='G'))

    def _payload(self, **extra):
        dados = {
            'nome': self.produto.nome, 'categoria': self.categoria.id, 'quantidade': 0,
            'estoque_minimo': 2, 'data_validade': self.validade_antiga.isoformat(), 'ultima_compra': '',
        }
        dados.update(extra)
        return dados

    def test_ajustar_quantidade_mantendo_a_validade_vencida_e_permitido(self):
        resposta = self.client.post(reverse('editar_produto', args=[self.produto.id]), self._payload())
        self.assertEqual(resposta.status_code, 302)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade, 0)

    def test_trocar_para_outra_data_vencida_continua_barrado(self):
        outra = (date.today() - timedelta(days=3)).isoformat()
        resposta = self.client.post(
            reverse('editar_produto', args=[self.produto.id]), self._payload(data_validade=outra))
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('data_validade', resposta.context['form'].errors)


class EntregaSemSaldoDefinidoTests(TestCase):
    def test_produto_sem_quantidade_nao_quebra_a_entrega(self):
        categoria = Categoria.objects.create(nome='Sem saldo')
        produto = Produto.objects.create(nome='Gaze', categoria=categoria, quantidade=None)
        self.client.force_login(_usuario('ent_atendente'))
        resposta = self.client.post(reverse('entregar_produto', args=[produto.id]), {
            'paciente': 'Ana', 'data_entrega': date.today().isoformat(), 'quantidade': 1,
        })
        self.assertEqual(resposta.status_code, 200)  # bloqueada por estoque insuficiente, sem erro 500
        self.assertFalse(Entrega.objects.exists())


class ExclusaoComRastroTests(TestCase):
    def test_excluir_produto_registra_saida_e_preserva_o_nome_no_historico(self):
        categoria = Categoria.objects.create(nome='Descarte')
        produto = Produto.objects.create(nome='Soro', categoria=categoria, quantidade=7)
        self.client.force_login(_usuario('exc_gestor', cargo='G'))
        self.client.post(reverse('excluir_produto', args=[produto.id]))

        self.assertFalse(Produto.objects.filter(nome='Soro').exists())
        mov = MovimentacaoEstoque.objects.get(produto_nome='Soro')
        self.assertEqual(mov.tipo, MovimentacaoEstoque.SAIDA)
        self.assertEqual(mov.quantidade, 7)
        self.assertIsNone(mov.produto)  # FK vira NULL; o nome fica guardado


class ModuloDeRelatoriosTests(TestCase):
    def setUp(self):
        categoria = Categoria.objects.create(nome='Rel')
        Produto.objects.create(nome='Baixo', categoria=categoria, quantidade=1, estoque_minimo=10)
        Produto.objects.create(nome='Alto', categoria=categoria, quantidade=99, estoque_minimo=10)

    def test_montar_relatorio_de_estoque_baixo(self):
        colunas, linhas = montar_relatorio('estoque_baixo', '', None, None, 'pt-br')
        self.assertEqual([l[0] for l in linhas], ['Baixo'])
        self.assertEqual(colunas[0], 'Nome')

    def test_cabecalhos_seguem_o_idioma(self):
        colunas, _ = montar_relatorio('estoque', '', None, None, 'en')
        self.assertEqual(colunas[0], 'Name')

    def test_tipo_desconhecido_devolve_vazio(self):
        self.assertEqual(montar_relatorio('nada', '', None, None, 'pt-br'), ([], []))

    def test_parse_data(self):
        self.assertEqual(parse_data('2026-09-26'), date(2026, 9, 26))
        self.assertIsNone(parse_data('26/09/2026'))
        self.assertIsNone(parse_data(''))

    def test_csv_exportado_tem_bom_e_cabecalho(self):
        self.client.force_login(_usuario('rel_atendente'))
        resposta = self.client.get(reverse('relatorios'), {'tipo': 'estoque', 'formato': 'csv'})
        texto = resposta.content.decode('utf-8-sig')
        self.assertTrue(texto.startswith('Nome,'))
        self.assertIn('Baixo', texto)

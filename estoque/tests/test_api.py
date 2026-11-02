"""Testes da API JSON somente leitura (estoque/api.py)."""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from estoque.models import Categoria, Entrega, Medicamento, MovimentacaoEstoque, Produto

Users = get_user_model()


class ApiBaseTests(TestCase):
    def setUp(self):
        hoje = date.today()
        self.cat = Categoria.objects.create(nome='Analgésicos')
        self.normal = Produto.objects.create(
            nome='Gaze', categoria=self.cat, quantidade=100, estoque_minimo=10,
            data_validade=hoje + timedelta(days=200),
        )
        self.vencendo = Produto.objects.create(
            nome='Soro', categoria=self.cat, quantidade=50, estoque_minimo=10,
            data_validade=hoje + timedelta(days=10),
        )
        self.vencido = Produto.objects.create(
            nome='Luva', categoria=self.cat, quantidade=50, estoque_minimo=10,
            data_validade=hoje - timedelta(days=1),
        )
        self.baixo = Produto.objects.create(
            nome='Seringa', categoria=self.cat, quantidade=2, estoque_minimo=10,
        )
        self.remedio = Medicamento.objects.create(
            nome='Dipirona', dosagem='500 mg', categoria=self.cat, quantidade=30,
            estoque_minimo=5, data_validade=hoje + timedelta(days=90),
        )
        self.usuario = Users.objects.create_user('atend', 'atend@teste.com', 'SenhaForte123', cargo='A')
        self.client.force_login(self.usuario)

    def get(self, nome, *args, **params):
        return self.client.get(reverse(nome, args=args), params)


class AutenticacaoEMetodoTests(ApiBaseTests):
    def test_anonimo_recebe_401_em_json(self):
        self.client.logout()
        for nome in ('api_indice', 'api_produtos', 'api_alertas', 'api_categorias',
                     'api_entregas', 'api_movimentacoes'):
            resposta = self.get(nome)
            self.assertEqual(resposta.status_code, 401, nome)
            self.assertIn('erro', resposta.json())

    def test_metodos_de_escrita_sao_rejeitados(self):
        for metodo in ('post', 'put', 'patch', 'delete'):
            resposta = getattr(self.client, metodo)(reverse('api_produtos'))
            self.assertEqual(resposta.status_code, 405, metodo)

    def test_indice_lista_os_endpoints(self):
        dados = self.get('api_indice').json()
        self.assertTrue(dados['somente_leitura'])
        self.assertEqual(dados['endpoints']['produtos'], '/api/produtos/')

    def test_resposta_e_json_utf8(self):
        resposta = self.get('api_categorias')
        self.assertEqual(resposta['Content-Type'], 'application/json')
        self.assertIn('Analgésicos', resposta.content.decode('utf-8'))


class ProdutosApiTests(ApiBaseTests):
    def test_lista_todos_com_campos_calculados(self):
        dados = self.get('api_produtos').json()
        self.assertEqual(dados['count'], 5)
        por_nome = {p['nome']: p for p in dados['results']}
        self.assertEqual(por_nome['Soro']['status_validade'], 'aviso')
        self.assertEqual(por_nome['Luva']['status_validade'], 'vencido')
        self.assertEqual(por_nome['Gaze']['status_validade'], 'normal')
        self.assertIsNone(por_nome['Seringa']['status_validade'])
        self.assertTrue(por_nome['Seringa']['estoque_baixo'])
        self.assertEqual(por_nome['Soro']['dias_para_vencer'], 10)

    def test_medicamento_traz_dosagem_e_tipo(self):
        dados = self.get('api_produtos', buscar='Dipirona').json()
        item = dados['results'][0]
        self.assertEqual(item['tipo'], 'medicamento')
        self.assertEqual(item['dosagem'], '500 mg')
        outro = self.get('api_produtos', buscar='Gaze').json()['results'][0]
        self.assertEqual(outro['tipo'], 'produto')
        self.assertIsNone(outro['dosagem'])

    def test_filtros_de_situacao(self):
        def nomes(filtro):
            return {p['nome'] for p in self.get('api_produtos', filtro=filtro).json()['results']}
        self.assertEqual(nomes('vencidos'), {'Luva'})
        self.assertEqual(nomes('vencendo'), {'Soro'})
        self.assertEqual(nomes('estoque_baixo'), {'Seringa'})
        self.assertEqual(nomes('normal'), {'Gaze', 'Dipirona'})

    def test_filtro_invalido_retorna_400(self):
        resposta = self.get('api_produtos', filtro='xyz')
        self.assertEqual(resposta.status_code, 400)
        self.assertIn('erro', resposta.json())

    def test_busca_e_categoria(self):
        outra = Categoria.objects.create(nome='Outra')
        Produto.objects.create(nome='Algodão', categoria=outra, quantidade=5)
        self.assertEqual(self.get('api_produtos', buscar='algod').json()['count'], 1)
        self.assertEqual(self.get('api_produtos', categoria=outra.pk).json()['count'], 1)
        self.assertEqual(self.get('api_produtos', categoria='abc').json()['count'], 6)

    def test_paginacao(self):
        dados = self.get('api_produtos', por_pagina=2).json()
        self.assertEqual(dados['por_pagina'], 2)
        self.assertEqual(dados['pages'], 3)
        self.assertEqual(len(dados['results']), 2)
        ultima = self.get('api_produtos', por_pagina=2, page=3).json()
        self.assertEqual(len(ultima['results']), 1)

    def test_por_pagina_e_limitado_e_invalido_usa_padrao(self):
        self.assertEqual(self.get('api_produtos', por_pagina=9999).json()['por_pagina'], 100)
        self.assertEqual(self.get('api_produtos', por_pagina='x').json()['por_pagina'], 50)
        self.assertEqual(self.get('api_produtos', por_pagina=-3).json()['por_pagina'], 50)

    def test_detalhe(self):
        dados = self.get('api_produto', self.vencido.pk).json()
        self.assertEqual(dados['nome'], 'Luva')
        self.assertEqual(dados['categoria'], 'Analgésicos')

    def test_detalhe_inexistente_retorna_404_json(self):
        resposta = self.get('api_produto', 99999)
        self.assertEqual(resposta.status_code, 404)
        self.assertIn('erro', resposta.json())

    def test_api_nao_altera_dados(self):
        antes = Produto.objects.count()
        self.get('api_produtos')
        self.get('api_alertas')
        self.assertEqual(Produto.objects.count(), antes)


class AlertasApiTests(ApiBaseTests):
    def test_totais_e_listas(self):
        dados = self.get('api_alertas').json()
        self.assertEqual(dados['dias_aviso_vencimento'], 30)
        self.assertEqual(dados['totais'], {
            'produtos': 5, 'estoque_baixo': 1, 'vencendo': 1, 'vencidos': 1,
        })
        self.assertEqual([p['nome'] for p in dados['vencidos']], ['Luva'])
        self.assertEqual([p['nome'] for p in dados['vencendo']], ['Soro'])
        self.assertEqual([p['nome'] for p in dados['estoque_baixo']], ['Seringa'])


class HistoricosApiTests(ApiBaseTests):
    def setUp(self):
        super().setUp()
        Entrega.objects.create(
            produto=self.normal, produto_nome='Gaze', paciente='Maria',
            quantidade=3, data_entrega=date.today(), usuario=self.usuario,
        )
        Entrega.objects.create(
            produto=self.vencendo, produto_nome='Soro', paciente='João',
            quantidade=1, data_entrega=date.today(), usuario=self.usuario,
        )
        MovimentacaoEstoque.objects.create(
            produto=self.normal, produto_nome='Gaze', tipo=MovimentacaoEstoque.SAIDA,
            quantidade=3, motivo='Entrega', motivo_codigo='entrega',
            motivo_detalhe='Maria', usuario=self.usuario,
        )
        MovimentacaoEstoque.objects.create(
            produto=self.normal, produto_nome='Gaze', tipo=MovimentacaoEstoque.ENTRADA,
            quantidade=100, motivo='Cadastro inicial do produto',
            motivo_codigo='cadastro_produto', usuario=None,
        )

    def test_entregas_e_filtros(self):
        dados = self.get('api_entregas').json()
        self.assertEqual(dados['count'], 2)
        self.assertEqual(dados['results'][0]['responsavel'], 'atend')
        self.assertEqual(self.get('api_entregas', buscar='maria').json()['count'], 1)
        self.assertEqual(self.get('api_entregas', produto=self.vencendo.pk).json()['count'], 1)

    def test_movimentacoes_e_filtro_de_tipo(self):
        self.assertEqual(self.get('api_movimentacoes').json()['count'], 2)
        saidas = self.get('api_movimentacoes', tipo='saida').json()
        self.assertEqual(saidas['count'], 1)
        self.assertEqual(saidas['results'][0]['motivo_detalhe'], 'Maria')
        sem_usuario = self.get('api_movimentacoes', tipo='ENTRADA').json()['results'][0]
        self.assertIsNone(sem_usuario['responsavel'])

    def test_tipo_invalido_retorna_400(self):
        self.assertEqual(self.get('api_movimentacoes', tipo='X').status_code, 400)

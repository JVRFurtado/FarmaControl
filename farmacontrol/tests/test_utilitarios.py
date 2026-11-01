"""Testes dos utilitários compartilhados: formatação, paginação, helpers de formulário e tradução."""
from datetime import date, datetime

from django.test import RequestFactory, SimpleTestCase

from farmacontrol.context_processors import traducoes_da_requisicao
from farmacontrol.formatacao import formatar_data, formatar_data_hora
from farmacontrol.formularios import dados_do_post
from farmacontrol.paginacao import ITENS_POR_PAGINA, paginar, querystring_sem_pagina


class FormatacaoTests(SimpleTestCase):
    def test_data_em_portugues_e_ingles(self):
        self.assertEqual(formatar_data(date(2026, 9, 26), 'pt-br'), '26/09/2026')
        self.assertEqual(formatar_data(date(2026, 9, 26), 'en'), 'Sep 26, 2026')

    def test_vazio_vira_travessao(self):
        self.assertEqual(formatar_data(None, 'pt-br'), '—')
        self.assertEqual(formatar_data_hora(None, 'en'), '—')

    def test_data_hora(self):
        valor = datetime(2026, 9, 26, 14, 30)
        self.assertEqual(formatar_data_hora(valor, 'pt-br'), '26/09/2026 14:30')
        self.assertEqual(formatar_data_hora(valor, 'en'), 'Sep 26, 2026 02:30 PM')


class PaginacaoTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.itens = list(range(ITENS_POR_PAGINA * 2 + 5))  # 3 páginas

    def test_sem_parametro_devolve_a_primeira_pagina(self):
        pagina = paginar(self.factory.get('/'), self.itens)
        self.assertEqual(pagina.number, 1)
        self.assertEqual(len(pagina), ITENS_POR_PAGINA)

    def test_ultima_pagina_tem_o_resto(self):
        pagina = paginar(self.factory.get('/', {'page': 3}), self.itens)
        self.assertEqual(len(pagina), 5)

    def test_pagina_invalida_cai_na_primeira(self):
        pagina = paginar(self.factory.get('/', {'page': 'abc'}), self.itens)
        self.assertEqual(pagina.number, 1)

    def test_pagina_alem_do_fim_cai_na_ultima(self):
        pagina = paginar(self.factory.get('/', {'page': 999}), self.itens)
        self.assertEqual(pagina.number, 3)

    def test_querystring_preserva_filtros_e_remove_page(self):
        request = self.factory.get('/', {'filtro': 'vencidos', 'page': 2})
        self.assertEqual(querystring_sem_pagina(request), 'filtro=vencidos')

    def test_querystring_vazia_sem_filtros(self):
        self.assertEqual(querystring_sem_pagina(self.factory.get('/', {'page': 2})), '')


class HelpersTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_post_vazio_ainda_e_post(self):
        # request.POST vazio é falsy — `request.POST or None` perderia os erros do form.
        request = self.factory.post('/', {})
        self.assertIsNotNone(dados_do_post(request))

    def test_get_nao_liga_o_formulario(self):
        self.assertIsNone(dados_do_post(self.factory.get('/')))

    def test_traducoes_da_requisicao_segue_o_cookie(self):
        request = self.factory.get('/')
        request.COOKIES['idioma'] = 'en'
        self.assertEqual(traducoes_da_requisicao(request)['comum']['voltar_inicio'], 'Back to Home')

    def test_traducoes_da_requisicao_padrao_e_portugues(self):
        self.assertEqual(
            traducoes_da_requisicao(self.factory.get('/'))['comum']['voltar_inicio'], 'Voltar ao Início')

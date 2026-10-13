"""
Testes do sistema de idiomas: a view que troca o idioma manualmente
(farmacontrol/views.py) e a detecção automática via Accept-Language
(farmacontrol/context_processors.py).
"""
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from django.urls import reverse

from farmacontrol.context_processors import idioma_da_requisicao, idioma_e_tema

Users = get_user_model()


class MudarIdiomaViewTests(TestCase):
    def setUp(self):
        self.usuario = Users.objects.create_user(
            username='usuarioidioma', email='usuarioidioma@teste.com', password='SenhaForte123', cargo='A',
        )
        self.client.force_login(self.usuario)

    def test_trocar_para_ingles_define_o_cookie(self):
        resposta = self.client.get(reverse('mudar_idioma', args=['en']))
        self.assertEqual(resposta.cookies['idioma'].value, 'en')

    def test_codigo_invalido_cai_no_idioma_padrao(self):
        resposta = self.client.get(reverse('mudar_idioma', args=['xx-invalido']))
        self.assertEqual(resposta.cookies['idioma'].value, 'pt-br')

    def test_sem_next_redireciona_para_o_dashboard(self):
        resposta = self.client.get(reverse('mudar_idioma', args=['en']))
        self.assertEqual(resposta.url, reverse('dashboard'))

    def test_next_externo_e_ignorado_por_seguranca(self):
        # Proteção contra open redirect: um `next` para outro domínio não é
        # seguido, cai no padrão (dashboard).
        resposta = self.client.get(reverse('mudar_idioma', args=['en']) + '?next=https://site-malicioso.com/')
        self.assertEqual(resposta.url, reverse('dashboard'))

    def test_next_interno_e_respeitado(self):
        destino = reverse('lista_produtos')
        resposta = self.client.get(reverse('mudar_idioma', args=['en']) + f'?next={destino}')
        self.assertEqual(resposta.url, destino)


class DeteccaoDeIdiomaTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_sem_cookie_e_sem_accept_language_usa_portugues(self):
        request = self.factory.get('/')
        self.assertEqual(idioma_da_requisicao(request), 'pt-br')

    def test_accept_language_em_ingles_detecta_ingles(self):
        request = self.factory.get('/', HTTP_ACCEPT_LANGUAGE='en-US,en;q=0.9')
        self.assertEqual(idioma_da_requisicao(request), 'en')

    def test_cookie_manual_tem_prioridade_sobre_o_navegador(self):
        request = self.factory.get('/', HTTP_ACCEPT_LANGUAGE='en-US,en;q=0.9')
        request.COOKIES['idioma'] = 'pt-br'
        self.assertEqual(idioma_da_requisicao(request), 'pt-br')

    def test_context_processor_devolve_textos_do_idioma_certo(self):
        request = self.factory.get('/')
        request.COOKIES['idioma'] = 'en'
        contexto = idioma_e_tema(request)
        self.assertEqual(contexto['idioma_atual'], 'en')
        self.assertEqual(contexto['t']['comum']['voltar_inicio'], 'Back to Home')

    def test_fallback_de_secao_ausente_usa_portugues(self):
        # Se uma seção não existir pro idioma, o _TraducaoComFallback cai no português.
        request = self.factory.get('/')
        request.COOKIES['idioma'] = 'en'
        contexto = idioma_e_tema(request)
        self.assertEqual(contexto['t']['secao-que-nao-existe'], {})

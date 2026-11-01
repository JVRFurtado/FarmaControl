from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import NoReverseMatch, reverse

Users = get_user_model()


class LoginTests(TestCase):
    def setUp(self):
        self.usuario = Users.objects.create_user(
            username='loginteste', email='loginteste@teste.com', password='SenhaForte123', cargo='A')

    def test_erro_de_login_aparece_uma_vez_so_e_sem_a_mensagem_padrao_do_django(self):
        resposta = self.client.post(reverse('login'), {'username': 'loginteste', 'password': 'errada'})
        texto = resposta.content.decode()
        self.assertEqual(texto.count('Usuário ou senha incorretos'), 1)
        self.assertNotIn('Por favor, entre com um usu', texto)  # texto padrão do Django

    def test_erro_de_login_em_ingles_quando_o_idioma_e_ingles(self):
        self.client.cookies['idioma'] = 'en'
        resposta = self.client.post(reverse('login'), {'username': 'loginteste', 'password': 'errada'})
        self.assertContains(resposta, 'Incorrect username or password')

    def test_login_volta_para_a_pagina_que_pediu_login(self):
        destino = reverse('lista_produtos')
        resposta = self.client.post(
            reverse('login') + f'?next={destino}', {'username': 'loginteste', 'password': 'SenhaForte123'})
        self.assertRedirects(resposta, destino)

    def test_pagina_protegida_manda_ao_login_com_next(self):
        resposta = self.client.get(reverse('lista_produtos'))
        self.assertEqual(resposta.status_code, 302)
        self.assertIn('next=', resposta.url)


class RotasEModeloLimposTests(TestCase):
    def test_rotas_de_login_logout_duplicadas_do_estoque_nao_existem_mais(self):
        self.assertEqual(self.client.get('/estoque/login/').status_code, 404)
        self.assertEqual(self.client.get('/estoque/logout/').status_code, 404)

    def test_logout_continua_funcionando_pelo_nome(self):
        self.assertEqual(reverse('logout'), '/usuarios/logout/')

    def test_funcao_morta_de_alternar_cargo_foi_removida(self):
        with self.assertRaises(NoReverseMatch):
            reverse('alternar_para_atendente')

    def test_campo_morto_do_modelo_foi_removido(self):
        nomes = [campo.name for campo in Users._meta.get_fields()]
        self.assertNotIn('is_temporarily_atendente', nomes)

    def test_logout_por_post_redireciona_ao_login(self):
        usuario = Users.objects.create_user(
            username='saida', email='saida@teste.com', password='SenhaForte123', cargo='A')
        self.client.force_login(usuario)
        resposta = self.client.post(reverse('logout'))
        self.assertEqual(resposta.status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)

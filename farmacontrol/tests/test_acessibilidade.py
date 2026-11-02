"""
Testes automáticos de acessibilidade (WCAG 2.1 AA) — o que dá para verificar
sem navegador: estrutura das páginas renderizadas e contraste das cores do
sistema de design. Não substituem uma auditoria com leitor de tela, mas
impedem que regressões óbvias voltem sem ninguém perceber.
"""
import re
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from estoque.models import Categoria, Produto

Users = get_user_model()


# --- Contraste (WCAG 1.4.3 texto 4.5:1 · 1.4.11 componentes 3:1) -----------

def _luminancia(cor):
    cor = cor.lstrip('#')
    r, g, b = (int(cor[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def razao_contraste(a, b):
    la, lb = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _tokens(bloco):
    return dict(re.findall(r'--([\w-]+):\s*(#[0-9a-fA-F]{6})', bloco))


class ContrasteDeCoresTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        css = (Path(settings.BASE_DIR) / 'estoque' / 'static' / 'estoque' / 'css' / 'estilo.css').read_text(encoding='utf-8')
        cls.temas = {
            'claro': _tokens(re.search(r':root \{(.*?)\n\}', css, re.S).group(1)),
            'escuro': _tokens(re.search(r':root\[data-theme="dark"\] \{(.*?)\n\}', css, re.S).group(1)),
        }

    # (texto, fundo, mínimo)
    PARES = [
        ('text', 'surface', 4.5), ('text', 'bg', 4.5),
        ('text-muted', 'surface', 4.5), ('text-muted', 'bg', 4.5), ('text-muted', 'surface-muted', 4.5),
        ('brand', 'surface', 4.5), ('brand', 'bg', 4.5),
        ('brand-on-light', 'brand-light', 4.5),
        ('text-on-brand', 'brand', 4.5),
        ('success-text', 'success-bg', 4.5), ('warning-text', 'warning-bg', 4.5),
        ('danger-text', 'danger-bg', 4.5), ('info-text', 'info-bg', 4.5),
        ('border-input', 'surface', 3.0),
    ]

    def test_pares_de_cores_atendem_ao_contraste_minimo(self):
        for tema, tokens in self.temas.items():
            for texto, fundo, minimo in self.PARES:
                with self.subTest(tema=tema, texto=texto, fundo=fundo):
                    razao = razao_contraste(tokens[texto], tokens[fundo])
                    self.assertGreaterEqual(razao, minimo, f'{texto} sobre {fundo}: {razao:.2f}')

    def test_foco_visivel_tem_contraste_de_componente(self):
        self.assertGreaterEqual(razao_contraste('#2563eb', self.temas['claro']['surface']), 3.0)
        self.assertGreaterEqual(razao_contraste(self.temas['escuro']['accent'], self.temas['escuro']['surface']), 3.0)


# --- Estrutura das páginas ------------------------------------------------

class EstruturaDasPaginasTests(TestCase):
    def setUp(self):
        cat = Categoria.objects.create(nome='Analgésicos')
        self.produto = Produto.objects.create(
            nome='Dipirona', categoria=cat, quantidade=20, estoque_minimo=5,
            data_validade=date.today() + timedelta(days=90),
        )
        self.cat = cat
        self.gestor = Users.objects.create_user('gestor1', 'g@teste.com', 'SenhaForte123', cargo='G')
        self.client.force_login(self.gestor)

    def paginas(self):
        return [
            reverse('dashboard'), reverse('lista_produtos'), reverse('adicionar_produto'),
            reverse('adicionar_medicamento'), reverse('editar_produto', args=[self.produto.pk]),
            reverse('entregar_produto', args=[self.produto.pk]), reverse('lista_categorias'),
            reverse('adicionar_categoria'), reverse('historico_entregas'),
            reverse('historico_movimentacoes'), reverse('relatorios'), reverse('analises'),
            reverse('lista_usuarios'), reverse('adicionar_usuario'),
            reverse('editar_usuario', args=[self.gestor.pk]),
            reverse('redefinir_senha_usuario', args=[self.gestor.pk]),
            reverse('password_change'),
        ]

    def verificar(self, html, url):
        self.assertRegex(html, r'<html lang="[a-zA-Z-]+"', f'{url}: falta lang no <html>')
        self.assertIn('skip-link', html, f'{url}: falta link "pular para o conteúdo"')
        self.assertIn('<main', html, f'{url}: falta landmark <main>')
        self.assertEqual(len(re.findall(r'<h1[\s>]', html)), 1, f'{url}: deve haver exatamente um <h1>')
        for img in re.findall(r'<img\b[^>]*>', html):
            self.assertIn('alt=', img, f'{url}: imagem sem alt: {img}')
        for th in re.findall(r'<th\b[^>]*>', html):
            self.assertIn('scope=', th, f'{url}: <th> sem scope: {th}')
        # todo campo visível precisa de rótulo associado (label for / aria-label)
        rotulados = set(re.findall(r'<label[^>]*\bfor="([^"]+)"', html))
        for campo in re.findall(r'<(?:input|select|textarea)\b[^>]*>', html):
            if re.search(r'type="(hidden|submit|button)"', campo):
                continue
            ident = re.search(r'\bid="([^"]+)"', campo)
            ok = ('aria-label' in campo) or (ident and ident.group(1) in rotulados)
            # checkbox dentro de <label> também é válido (rótulo envolvente)
            if not ok and 'type="checkbox"' in campo:
                continue
            self.assertTrue(ok, f'{url}: campo sem rótulo: {campo}')

    def test_paginas_autenticadas_seguem_a_estrutura_acessivel(self):
        for url in self.paginas():
            with self.subTest(url=url):
                resposta = self.client.get(url)
                self.assertEqual(resposta.status_code, 200, url)
                self.verificar(resposta.content.decode('utf-8'), url)

    def test_pagina_de_login(self):
        self.client.logout()
        resposta = self.client.get(reverse('login'))
        self.assertEqual(resposta.status_code, 200)
        self.verificar(resposta.content.decode('utf-8'), 'login')

    def test_tabelas_tem_legenda_e_regiao_rolavel_focavel(self):
        for url in (reverse('lista_produtos'), reverse('historico_entregas'),
                    reverse('historico_movimentacoes'), reverse('lista_usuarios')):
            with self.subTest(url=url):
                html = self.client.get(url).content.decode('utf-8')
                if '<table' in html:
                    self.assertIn('<caption', html)
                    self.assertIn('tabindex="0" role="region"', html)

    def test_html_declara_o_idioma_escolhido(self):
        self.client.cookies['idioma'] = 'en'
        html = self.client.get(reverse('dashboard')).content.decode('utf-8')
        self.assertIn('<html lang="en"', html)

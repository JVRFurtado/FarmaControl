"""
Testes dos filtros de template que formatam datas conforme o idioma
(estoque/templatetags/i18n_extras.py).
"""
from datetime import date, datetime

from django.test import SimpleTestCase

from estoque.templatetags.i18n_extras import data_localizada, data_hora_localizada


class DataLocalizadaTests(SimpleTestCase):
    def test_none_retorna_travessao(self):
        self.assertEqual(data_localizada(None, 'pt-br'), '—')

    def test_portugues_formata_dia_mes_ano(self):
        self.assertEqual(data_localizada(date(2026, 9, 26), 'pt-br'), '26/09/2026')

    def test_ingles_formata_mes_abreviado(self):
        self.assertEqual(data_localizada(date(2026, 9, 26), 'en'), 'Sep 26, 2026')

    def test_idioma_desconhecido_cai_no_portugues(self):
        self.assertEqual(data_localizada(date(2026, 9, 26), 'fr'), '26/09/2026')


class DataHoraLocalizadaTests(SimpleTestCase):
    def test_none_retorna_travessao(self):
        self.assertEqual(data_hora_localizada(None, 'pt-br'), '—')

    def test_portugues_inclui_hora_24h(self):
        valor = datetime(2026, 9, 26, 14, 30)
        self.assertEqual(data_hora_localizada(valor, 'pt-br'), '26/09/2026 14:30')

    def test_ingles_inclui_hora_12h_am_pm(self):
        valor = datetime(2026, 9, 26, 14, 30)
        self.assertEqual(data_hora_localizada(valor, 'en'), 'Sep 26, 2026 02:30 PM')

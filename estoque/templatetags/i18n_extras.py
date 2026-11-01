from django import template

from farmacontrol.formatacao import formatar_data, formatar_data_hora

register = template.Library()

data_localizada = register.filter('data_localizada', formatar_data)
data_hora_localizada = register.filter('data_hora_localizada', formatar_data_hora)

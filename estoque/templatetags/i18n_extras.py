from django import template

register = template.Library()


@register.filter
def data_localizada(valor, idioma):
    """Formata uma data conforme o idioma atual: dd/mm/aaaa em português,
    formato mês-abreviado em inglês. Evita depender do LANGUAGE_CODE nativo
    do Django, já que este projeto usa seu próprio sistema de idiomas
    (veja farmacontrol/i18n.py)."""
    if not valor:
        return '—'
    if idioma == 'en':
        return valor.strftime('%b %d, %Y')
    return valor.strftime('%d/%m/%Y')


@register.filter
def data_hora_localizada(valor, idioma):
    """Igual a `data_localizada`, mas incluindo o horário (usado no
    histórico de movimentações)."""
    if not valor:
        return '—'
    if idioma == 'en':
        return valor.strftime('%b %d, %Y %I:%M %p')
    return valor.strftime('%d/%m/%Y %H:%M')

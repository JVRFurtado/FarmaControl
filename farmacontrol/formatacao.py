"""Formatação de datas conforme o idioma do sistema (um só lugar para
templates, views e relatórios."""


def formatar_data(valor, idioma):
    """dd/mm/aaaa em português; mês abreviado em inglês; '—' se vazio."""
    if not valor:
        return '—'
    if idioma == 'en':
        return valor.strftime('%b %d, %Y')
    return valor.strftime('%d/%m/%Y')


def formatar_data_hora(valor, idioma):
    """Igual a `formatar_data`, incluindo o horário (24h em pt, 12h em inglês)."""
    if not valor:
        return '—'
    if idioma == 'en':
        return valor.strftime('%b %d, %Y %I:%M %p')
    return valor.strftime('%d/%m/%Y %H:%M')

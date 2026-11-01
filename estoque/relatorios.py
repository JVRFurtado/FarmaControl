"""
Montagem e exportação dos relatórios (tela, CSV e Excel).
"""
import csv
from datetime import datetime
from io import BytesIO

from django.http import HttpResponse
from django.utils.text import slugify

from farmacontrol.formatacao import formatar_data, formatar_data_hora
from farmacontrol.i18n import TRANSLATIONS, IDIOMA_PADRAO

from .models import Entrega, MovimentacaoEstoque, Produto
from .movimentacoes import motivo_traduzido

TIPOS_RELATORIO_VALIDOS = {
    'estoque', 'estoque_baixo', 'vencendo', 'vencidos', 'entregas', 'movimentacoes',
}
TIPOS_DE_PRODUTO = ('estoque', 'estoque_baixo', 'vencendo', 'vencidos')
TIPOS_COM_PERIODO = ('entregas', 'movimentacoes')

TIPO_XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def parse_data(valor):
    """Converte 'AAAA-MM-DD' em date; vazio ou formato inválido → None."""
    if not valor:
        return None
    try:
        return datetime.strptime(valor, '%Y-%m-%d').date()
    except ValueError:
        return None


def rotulos_dos_tipos(tr):
    """Nome de cada tipo de relatório no idioma do dicionário `tr`."""
    r = tr['relatorios']
    return {tipo: r[f'tipo_{tipo}'] for tipo in TIPOS_RELATORIO_VALIDOS}


def _linhas_de_produtos(tipo, categoria_id, tr, idioma):
    p_t = tr['produtos']
    produtos = Produto.objects.select_related('categoria').order_by('nome')
    if categoria_id:
        produtos = produtos.filter(categoria_id=categoria_id)
    if tipo != 'estoque':  # 'estoque_baixo' | 'vencendo' | 'vencidos' são nomes de filtro
        produtos = produtos.por_filtro(tipo)

    status_labels = {
        'vencido': p_t['status_vencido'],
        'aviso': p_t['status_aviso'],
        'normal': p_t['status_normal'],
    }
    colunas = [p_t['col_nome'], p_t['col_categoria'], p_t['col_quantidade'],
               p_t['col_estoque_minimo'], p_t['col_validade'], p_t['col_status']]
    linhas = [
        [
            p.nome,
            p.categoria.nome if p.categoria else '—',
            p.quantidade if p.quantidade is not None else '—',
            p.estoque_minimo,
            formatar_data(p.data_validade, idioma),
            status_labels.get(p.status_validade, '—'),
        ]
        for p in produtos
    ]
    return colunas, linhas


def _linhas_de_entregas(categoria_id, data_inicio, data_fim, tr, idioma):
    e_t = tr['entregas_hist']
    entregas = Entrega.objects.select_related('usuario')
    if data_inicio:
        entregas = entregas.filter(data_entrega__gte=data_inicio)
    if data_fim:
        entregas = entregas.filter(data_entrega__lte=data_fim)
    if categoria_id:
        entregas = entregas.filter(produto__categoria_id=categoria_id)

    colunas = [e_t['col_data'], e_t['col_produto'], e_t['col_paciente'],
               e_t['col_quantidade'], e_t['col_registrado_por']]
    linhas = [
        [
            formatar_data(e.data_entrega, idioma),
            e.produto_nome,
            e.paciente,
            e.quantidade,
            e.usuario.username if e.usuario else '—',
        ]
        for e in entregas
    ]
    return colunas, linhas


def _linhas_de_movimentacoes(categoria_id, data_inicio, data_fim, tr, idioma):
    m_t = tr['movimentacoes_hist']
    movs = MovimentacaoEstoque.objects.select_related('usuario')
    if data_inicio:
        movs = movs.filter(data__date__gte=data_inicio)
    if data_fim:
        movs = movs.filter(data__date__lte=data_fim)
    if categoria_id:
        movs = movs.filter(produto__categoria_id=categoria_id)

    tipo_labels = {MovimentacaoEstoque.ENTRADA: m_t['tipo_entrada'],
                   MovimentacaoEstoque.SAIDA: m_t['tipo_saida']}
    colunas = [m_t['col_data'], m_t['col_produto'], m_t['col_tipo'],
               m_t['col_quantidade'], m_t['col_motivo'], m_t['col_usuario']]
    linhas = [
        [
            formatar_data_hora(m.data, idioma),
            m.produto_nome,
            tipo_labels.get(m.tipo, m.get_tipo_display()),
            m.quantidade,
            motivo_traduzido(m.motivo_codigo, m.motivo_detalhe, m.motivo, tr),
            m.usuario.username if m.usuario else '—',
        ]
        for m in movs
    ]
    return colunas, linhas


def montar_relatorio(tipo, categoria_id, data_inicio, data_fim, idioma):
    """Devolve (colunas, linhas) do relatório pedido, já filtrado e com os
    cabeçalhos no idioma atual."""
    tr = TRANSLATIONS.get(idioma, TRANSLATIONS[IDIOMA_PADRAO])
    if tipo in TIPOS_DE_PRODUTO:
        return _linhas_de_produtos(tipo, categoria_id, tr, idioma)
    if tipo == 'entregas':
        return _linhas_de_entregas(categoria_id, data_inicio, data_fim, tr, idioma)
    if tipo == 'movimentacoes':
        return _linhas_de_movimentacoes(categoria_id, data_inicio, data_fim, tr, idioma)
    return [], []


def exportar_csv(titulo, colunas, linhas):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{slugify(titulo)}.csv"'
    response.write('\ufeff')  # BOM: garante que o Excel abra acentuação corretamente
    writer = csv.writer(response)
    writer.writerow(colunas)
    writer.writerows(linhas)
    return response


def exportar_xlsx(titulo, colunas, linhas):
    import openpyxl  # importado aqui: só é necessário quando alguém exporta Excel
    from openpyxl.styles import Font

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = titulo[:31]  # limite de 31 caracteres do Excel para nome de aba

    ws.append(colunas)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for linha in linhas:
        ws.append(linha)

    for coluna in ws.columns:
        largura = max((len(str(c.value)) for c in coluna if c.value is not None), default=10)
        ws.column_dimensions[coluna[0].column_letter].width = min(largura + 2, 40)

    buffer = BytesIO()
    wb.save(buffer)

    response = HttpResponse(buffer.getvalue(), content_type=TIPO_XLSX)
    response['Content-Disposition'] = f'attachment; filename="{slugify(titulo)}.xlsx"'
    return response

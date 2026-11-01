"""
Registro e exibição do histórico de movimentações de estoque.

Toda alteração de quantidade (cadastro, ajuste na edição, entrega,
exclusão) passa por `registrar_movimentacao`, para o histórico ter uma
única porta de entrada. A exibição traduzida do motivo fica em
`motivo_traduzido`.
"""
from .models import MovimentacaoEstoque


def registrar_movimentacao(produto, tipo, quantidade, motivo, usuario,
                           motivo_codigo='', motivo_detalhe=''):
    """Registra uma entrada ou saída no histórico de movimentações.

    Não registra nada se a quantidade for zero/negativa/vazia (nada de fato
    mudou).

    `motivo` guarda o texto em português (histórico bruto e fallback para
    motivos sem código conhecido). `motivo_codigo` identifica um motivo
    "padrão" para que a exibição possa traduzir o texto conforme o idioma
    da pessoa (veja `motivo_traduzido`); `motivo_detalhe` guarda a parte
    variável (ex.: o nome do paciente numa entrega).
    """
    if not quantidade or quantidade <= 0:
        return None
    return MovimentacaoEstoque.objects.create(
        produto=produto,
        produto_nome=produto.nome,
        tipo=tipo,
        quantidade=quantidade,
        motivo=motivo,
        motivo_codigo=motivo_codigo,
        motivo_detalhe=motivo_detalhe,
        usuario=usuario if getattr(usuario, 'is_authenticated', False) else None,
    )


def motivo_traduzido(motivo_codigo, motivo_detalhe, motivo_bruto, tr):
    """Traduz o motivo de uma movimentação para o idioma do dicionário `tr`.

    Registros antigos (sem código) ou motivos livres caem no texto bruto
    salvo em português.
    """
    m_t = tr['movimentacoes_hist']
    if motivo_codigo == MovimentacaoEstoque.MOTIVO_ENTREGA:
        return f"{m_t['motivo_entrega_prefixo']} {motivo_detalhe}"

    chave_por_codigo = {
        MovimentacaoEstoque.MOTIVO_CADASTRO_PRODUTO: 'motivo_cadastro_produto',
        MovimentacaoEstoque.MOTIVO_CADASTRO_MEDICAMENTO: 'motivo_cadastro_medicamento',
        MovimentacaoEstoque.MOTIVO_AJUSTE_MANUAL: 'motivo_ajuste_manual',
        MovimentacaoEstoque.MOTIVO_EXCLUSAO_PRODUTO: 'motivo_exclusao_produto',
    }
    chave = chave_por_codigo.get(motivo_codigo)
    return m_t[chave] if chave else motivo_bruto

from .i18n import TRANSLATIONS, IDIOMAS_DISPONIVEIS, IDIOMA_PADRAO


def detectar_idioma_do_navegador(request):
    """Idioma automático: olha o cabeçalho Accept-Language do navegador.
    Só usado quando a pessoa nunca escolheu um idioma manualmente."""
    aceitos = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
    if aceitos.lower().startswith('en'):
        return 'en'
    return IDIOMA_PADRAO


def idioma_da_requisicao(request):
    """Resolve o idioma atual (cookie manual > navegador > padrão). Usado
    tanto pelo context processor (para templates) quanto diretamente por
    views que precisam montar texto traduzido em Python (ex.: relatórios,
    onde os cabeçalhos de coluna e o nome do arquivo exportado também
    precisam respeitar o idioma escolhido)."""
    idioma = request.COOKIES.get('idioma')
    if idioma in TRANSLATIONS:
        return idioma
    return detectar_idioma_do_navegador(request)


class _TraducaoComFallback(dict):
    """Um dict que, se uma chave (seção) não existir, devolve a seção
    equivalente do idioma padrão em vez de quebrar o template. Assim, um
    texto novo que só foi adicionado em pt-br não derruba a página em
    inglês — só aparece em português naquele ponto específico."""

    def __init__(self, secoes, secoes_padrao):
        super().__init__(secoes)
        self._secoes_padrao = secoes_padrao

    def __getitem__(self, chave):
        if chave in self:
            return dict.__getitem__(self, chave)
        return self._secoes_padrao.get(chave, {})

    def __getattr__(self, chave):
        return self[chave]


def idioma_e_tema(request):
    """Disponibiliza `t` (textos traduzidos), `idioma_atual` e a lista de
    idiomas em todos os templates, sem precisar declarar nada em cada view.

    Prioridade do idioma: cookie escolhido manualmente > detecção automática
    pelo navegador > português (padrão do sistema).
    """
    idioma = idioma_da_requisicao(request)

    textos = _TraducaoComFallback(
        TRANSLATIONS.get(idioma, TRANSLATIONS[IDIOMA_PADRAO]),
        TRANSLATIONS[IDIOMA_PADRAO],
    )

    return {
        't': textos,
        'idioma_atual': idioma,
        'idiomas_disponiveis': IDIOMAS_DISPONIVEIS,
    }

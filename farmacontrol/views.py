from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .i18n import TRANSLATIONS, IDIOMA_PADRAO


def mudar_idioma(request, codigo):
    """Define o idioma escolhido manualmente num cookie de longa duração
    (1 ano) e volta para a página onde a pessoa estava. Sempre que o cookie
    existir, ele tem prioridade sobre a detecção automática do navegador."""
    if codigo not in TRANSLATIONS:
        codigo = IDIOMA_PADRAO

    next_url = request.POST.get('next') or request.GET.get('next')
    if not next_url or not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = reverse('dashboard')

    response = HttpResponseRedirect(next_url)
    response.set_cookie('idioma', codigo, max_age=365 * 24 * 60 * 60)
    return response

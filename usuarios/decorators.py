from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .permissoes import eh_gestor_ou_admin


def gestor_required(view_func):
    """Só permite acesso a Gestor ou Admin (superusuário). Atendentes recebem 403.

    O Admin é o superusuário do Django (`is_superuser=True`, criado via
    `python manage.py createsu`) tem, no mínimo, os mesmos privilégios
    do Gestor em todo o sistema. Usuários anônimos são redirecionados ao
    login (o `login_required` roda primeiro)."""
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not eh_gestor_ou_admin(request.user):
            raise PermissionDenied('Apenas o Gestor pode realizar esta ação.')
        return view_func(request, *args, **kwargs)
    return _wrapped

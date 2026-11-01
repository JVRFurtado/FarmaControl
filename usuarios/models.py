from django.contrib.auth.models import AbstractUser
from django.db import models


class Users(AbstractUser):
    """Usuário do sistema. O privilégio de Admin não é um cargo: é o
    `is_superuser` do próprio Django."""

    CARGO_GESTOR = 'G'
    CARGO_ATENDENTE = 'A'
    choices_cargo = (
        (CARGO_GESTOR, 'Gestor'),
        (CARGO_ATENDENTE, 'Atendente'),
    )

    cargo = models.CharField(max_length=1, choices=choices_cargo, default=CARGO_ATENDENTE)
    email = models.EmailField('email address', unique=True, blank=False, null=False)

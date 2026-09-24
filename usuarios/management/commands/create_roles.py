import os

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from rolepermissions.roles import assign_role


class Command(BaseCommand):
    help = 'Cria usuários iniciais (gestor e atendente) e atribui suas roles.'

    def handle(self, *args, **kwargs):
        from usuarios.roles import Gestor, Atendente

        User = get_user_model()  # usa o modelo customizado usuarios.Users, não o padrão do Django

        # Senhas vêm de variáveis de ambiente; se não definidas, gera uma senha
        # aleatória e avisa no terminal (evita credenciais padrão previsíveis).
        # get_random_string substitui User.objects.make_random_password(),
        # removido a partir do Django 5.1.
        gestor_password = os.environ.get('GESTOR_INITIAL_PASSWORD') or get_random_string(12)
        atendente_password = os.environ.get('ATENDENTE_INITIAL_PASSWORD') or get_random_string(12)

        if not User.objects.filter(username='gestor').exists():
            gestor = User.objects.create_user(
                username='gestor', password=gestor_password, cargo='G', email='gestor@farmacontrol.local'
            )
            assign_role(gestor, Gestor)
            if not os.environ.get('GESTOR_INITIAL_PASSWORD'):
                self.stdout.write(self.style.WARNING(f'Senha gerada para "gestor": {gestor_password} (troque no primeiro login)'))

        if not User.objects.filter(username='atendente').exists():
            atendente = User.objects.create_user(
                username='atendente', password=atendente_password, cargo='A', email='atendente@farmacontrol.local'
            )
            assign_role(atendente, Atendente)
            if not os.environ.get('ATENDENTE_INITIAL_PASSWORD'):
                self.stdout.write(self.style.WARNING(f'Senha gerada para "atendente": {atendente_password} (troque no primeiro login)'))

        self.stdout.write(self.style.SUCCESS('Roles criadas com sucesso'))


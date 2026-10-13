import os

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Cria um superusuário inicial "admin" se ele ainda não existir.'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        if User.objects.filter(username='admin').exists():
            self.stdout.write(self.style.WARNING('Superuser já existe.'))
            return

        password = os.environ.get('ADMIN_INITIAL_PASSWORD')
        if not password:
            raise CommandError(
                'Defina a variável de ambiente ADMIN_INITIAL_PASSWORD antes de rodar este comando '
                '(evita criar um superusuário com senha padrão previsível).'
            )

        admin = User.objects.create_superuser('admin', 'admin@example.com', password)
        # cargo='G' é só para exibição (ex.: badges na tela de usuários);
        # o privilégio de Admin de verdade vem de is_superuser=True, não do cargo.
        admin.cargo = 'G'
        admin.save()
        self.stdout.write(self.style.SUCCESS('Superuser criado com sucesso!'))


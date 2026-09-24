# Generated manually for a Fase 2 (alertas de estoque baixo)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='produto',
            name='estoque_minimo',
            field=models.PositiveIntegerField(
                default=10,
                help_text='Quantidade mínima antes de disparar o alerta de estoque baixo.',
            ),
        ),
    ]

# Generated manually: substitui o campo de texto livre "tamanho" por três
# campos numéricos (altura, largura, comprimento) e adiciona validação
# para impedir quantidades negativas.

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0002_produto_estoque_minimo'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='produto',
            name='tamanho',
        ),
        migrations.AddField(
            model_name='produto',
            name='altura',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=8, null=True,
                help_text='Em centímetros.',
                validators=[django.core.validators.MinValueValidator(0, message='A altura não pode ser negativa.')],
            ),
        ),
        migrations.AddField(
            model_name='produto',
            name='largura',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=8, null=True,
                help_text='Em centímetros.',
                validators=[django.core.validators.MinValueValidator(0, message='A largura não pode ser negativa.')],
            ),
        ),
        migrations.AddField(
            model_name='produto',
            name='comprimento',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=8, null=True,
                help_text='Em centímetros.',
                validators=[django.core.validators.MinValueValidator(0, message='O comprimento não pode ser negativo.')],
            ),
        ),
        migrations.AlterField(
            model_name='produto',
            name='quantidade',
            field=models.IntegerField(
                blank=True, null=True,
                validators=[django.core.validators.MinValueValidator(0, message='A quantidade em estoque não pode ser negativa.')],
            ),
        ),
        migrations.AddConstraint(
            model_name='produto',
            constraint=models.UniqueConstraint(
                fields=('nome', 'altura', 'largura', 'comprimento', 'categoria', 'data_validade', 'ultima_compra'),
                name='unique_produto_completo',
            ),
        ),
        migrations.AlterModelOptions(
            name='categoria',
            options={'ordering': ['nome']},
        ),
    ]

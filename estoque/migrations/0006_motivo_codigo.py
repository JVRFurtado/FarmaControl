from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0005_entrega_movimentacaoestoque'),
    ]

    operations = [
        migrations.AddField(
            model_name='movimentacaoestoque',
            name='motivo_codigo',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
        migrations.AddField(
            model_name='movimentacaoestoque',
            name='motivo_detalhe',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
    ]

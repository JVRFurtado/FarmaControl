import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('estoque', '0004_categorias_padrao'),
    ]

    operations = [
        migrations.CreateModel(
            name='Entrega',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('produto_nome', models.CharField(max_length=100)),
                ('paciente', models.CharField(max_length=100)),
                ('quantidade', models.PositiveIntegerField()),
                ('data_entrega', models.DateField()),
                ('registrado_em', models.DateTimeField(auto_now_add=True)),
                ('produto', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='entregas', to='estoque.produto')),
                ('usuario', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='entregas_registradas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-data_entrega', '-registrado_em'],
            },
        ),
        migrations.CreateModel(
            name='MovimentacaoEstoque',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('produto_nome', models.CharField(max_length=100)),
                ('tipo', models.CharField(choices=[('ENTRADA', 'Entrada'), ('SAIDA', 'Saída')], max_length=10)),
                ('quantidade', models.PositiveIntegerField()),
                ('motivo', models.CharField(max_length=200)),
                ('data', models.DateTimeField(auto_now_add=True)),
                ('produto', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='movimentacoes', to='estoque.produto')),
                ('usuario', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='movimentacoes_registradas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-data'],
            },
        ),
    ]

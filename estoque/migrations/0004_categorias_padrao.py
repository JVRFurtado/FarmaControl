from django.db import migrations


CATEGORIAS_PADRAO = [
    'Medicamentos',
    'Materiais Hospitalares',
    'Higiene e Limpeza',
    'Outros',
]


def criar_categorias_padrao(apps, schema_editor):
    Categoria = apps.get_model('estoque', 'Categoria')
    for nome in CATEGORIAS_PADRAO:
        Categoria.objects.get_or_create(nome=nome)


def remover_categorias_padrao(apps, schema_editor):
    Categoria = apps.get_model('estoque', 'Categoria')
    Categoria.objects.filter(nome__in=CATEGORIAS_PADRAO).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0003_padronizacao_campos'),
    ]

    operations = [
        migrations.RunPython(criar_categorias_padrao, remover_categorias_padrao),
    ]

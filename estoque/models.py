from django.db import models

# Modelo Categoria
class Categoria(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nome

# Modelo Produto
class Produto(models.Model):
    nome = models.CharField(max_length=100)
    tamanho = models.CharField(max_length=50, blank=True, default="")
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True)
    quantidade = models.IntegerField(null=True, blank=True)
    data_validade = models.DateField(null=True, blank=True)
    ultima_compra = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['nome', 'tamanho', 'categoria', 'data_validade', 'ultima_compra'],
                name='unique_produto_completo'
            )
        ]

    def __str__(self):
        return self.nome

# Modelo Medicamento
class Medicamento(Produto):
    dosagem = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.nome} - {self.dosagem}"
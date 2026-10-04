from datetime import date

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

DIAS_AVISO_VENCIMENTO = 30

# Modelo Categoria
class Categoria(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome

# Modelo Produto
class Produto(models.Model):
    nome = models.CharField(max_length=100)
    altura = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0, message='A altura não pode ser negativa.')],
        help_text='Em centímetros.',
    )
    largura = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0, message='A largura não pode ser negativa.')],
        help_text='Em centímetros.',
    )
    comprimento = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0, message='O comprimento não pode ser negativo.')],
        help_text='Em centímetros.',
    )
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True)
    quantidade = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0, message='A quantidade em estoque não pode ser negativa.')],
    )
    estoque_minimo = models.PositiveIntegerField(
        default=10,
        help_text="Quantidade mínima antes de disparar o alerta de estoque baixo.",
    )
    data_validade = models.DateField(null=True, blank=True)
    ultima_compra = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['nome', 'altura', 'largura', 'comprimento', 'categoria', 'data_validade', 'ultima_compra'],
                name='unique_produto_completo'
            )
        ]

    def __str__(self):
        return self.nome

    @property
    def estoque_baixo(self):
        """True quando a quantidade em estoque está no mínimo configurado ou abaixo dele."""
        if self.quantidade is None:
            return False
        return self.quantidade <= self.estoque_minimo

    @property
    def dias_para_vencer(self):
        """Dias restantes até a validade (negativo se já venceu). None se não há data de validade."""
        if self.data_validade is None:
            return None
        return (self.data_validade - date.today()).days

    @property
    def status_validade(self):
        """Retorna 'vencido', 'aviso' ou 'normal' com base na regra de 30 dias.
        Retorna None quando o produto não tem data de validade cadastrada."""
        dias = self.dias_para_vencer
        if dias is None:
            return None
        if dias < 0:
            return 'vencido'
        if dias <= DIAS_AVISO_VENCIMENTO:
            return 'aviso'
        return 'normal'

    @property
    def esta_vencido(self):
        return self.status_validade == 'vencido'

    @property
    def vencimento_proximo(self):
        return self.status_validade == 'aviso'

# Modelo Medicamento
class Medicamento(Produto):
    dosagem = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.nome} - {self.dosagem}"


# Histórico de entregas: registra cada entrega feita a um paciente.
class Entrega(models.Model):
    produto = models.ForeignKey(
        Produto, on_delete=models.SET_NULL, null=True, related_name='entregas'
    )
    # Guarda o nome do produto no momento da entrega, para o histórico continuar
    # legível mesmo que o produto seja excluído depois.
    produto_nome = models.CharField(max_length=100)
    paciente = models.CharField(max_length=100)
    quantidade = models.PositiveIntegerField()
    data_entrega = models.DateField()
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='entregas_registradas',
    )
    registrado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_entrega', '-registrado_em']

    def __str__(self):
        return f'{self.produto_nome} → {self.paciente} ({self.quantidade})'


# Histórico de movimentações de estoque: toda entrada ou saída de quantidade,
# de onde quer que venha (cadastro, edição, entrega, exclusão).
class MovimentacaoEstoque(models.Model):
    ENTRADA = 'ENTRADA'
    SAIDA = 'SAIDA'
    TIPO_CHOICES = [
        (ENTRADA, 'Entrada'),
        (SAIDA, 'Saída'),
    ]

    # Motivos "conhecidos": permitem traduzir o texto exibido conforme o
    # idioma da pessoa. `motivo` continua guardando o texto em português
    # (serve de histórico bruto e cobre registros antigos ou motivos livres
    # que não se encaixam em nenhum código). `motivo_detalhe` guarda a parte
    # variável (ex.: o nome do paciente, no caso de uma entrega).
    MOTIVO_CADASTRO_PRODUTO = 'cadastro_produto'
    MOTIVO_CADASTRO_MEDICAMENTO = 'cadastro_medicamento'
    MOTIVO_AJUSTE_MANUAL = 'ajuste_manual'
    MOTIVO_ENTREGA = 'entrega'
    MOTIVO_EXCLUSAO_PRODUTO = 'exclusao_produto'

    produto = models.ForeignKey(
        Produto, on_delete=models.SET_NULL, null=True, related_name='movimentacoes'
    )
    produto_nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    quantidade = models.PositiveIntegerField()
    motivo = models.CharField(max_length=200)
    motivo_codigo = models.CharField(max_length=30, blank=True, default='')
    motivo_detalhe = models.CharField(max_length=200, blank=True, default='')
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='movimentacoes_registradas',
    )
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data']

    def __str__(self):
        return f'{self.get_tipo_display()} de {self.quantidade} — {self.produto_nome}'
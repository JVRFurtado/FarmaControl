from datetime import date

from django import forms

from farmacontrol.formularios import aplicar_classe_input, marcar_campos_obrigatorios

from .models import Categoria, Medicamento, Produto

FORMATO_DATA = '%Y-%m-%d'
WIDGETS_DE_DATA = {
    'data_validade': forms.DateInput(attrs={'type': 'date'}, format=FORMATO_DATA),
    'ultima_compra': forms.DateInput(attrs={'type': 'date'}, format=FORMATO_DATA),
}


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Ex.: Analgésicos'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_classe_input(self)
        marcar_campos_obrigatorios(self)


class _ItemDeEstoqueForm(forms.ModelForm):
    """Base de ProdutoForm e MedicamentoForm: as regras de data e quantidade
    são as mesmas — só muda a palavra usada na mensagem de erro."""

    mensagem_vencido = 'Não é possível cadastrar um item já vencido.'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_classe_input(self)
        for campo in ('data_validade', 'ultima_compra'):
            self.fields[campo].input_formats = [FORMATO_DATA]
        # Dica visual no seletor de data; a regra de verdade está em clean_data_validade.
        self.fields['data_validade'].widget.attrs['min'] = date.today().isoformat()
        self.fields['categoria'].empty_label = 'Selecione uma categoria...'
        marcar_campos_obrigatorios(self)

    def clean_data_validade(self):
        data_validade = self.cleaned_data.get('data_validade')
        # Só barra datas passadas quando a data foi informada/alterada agora:
        # editar a quantidade de um produto que JÁ está vencido (e mantém a
        # mesma data) tem que continuar possível.
        if data_validade and data_validade < date.today() and 'data_validade' in self.changed_data:
            raise forms.ValidationError(self.mensagem_vencido)
        return data_validade

    def clean_quantidade(self):
        quantidade = self.cleaned_data.get('quantidade')
        if quantidade is not None and quantidade < 0:
            raise forms.ValidationError('A quantidade em estoque não pode ser negativa.')
        return quantidade


class ProdutoForm(_ItemDeEstoqueForm):
    mensagem_vencido = 'Não é possível cadastrar um produto já vencido.'

    class Meta:
        model = Produto
        fields = '__all__'
        widgets = WIDGETS_DE_DATA


class MedicamentoForm(_ItemDeEstoqueForm):
    mensagem_vencido = 'Não é possível cadastrar um medicamento já vencido.'

    class Meta:
        model = Medicamento
        fields = ['nome', 'dosagem', 'categoria', 'quantidade', 'estoque_minimo',
                  'data_validade', 'ultima_compra']
        widgets = WIDGETS_DE_DATA


class EntregaForm(forms.Form):
    paciente = forms.CharField(
        label='Para quem', max_length=100, widget=forms.TextInput(attrs={'required': 'required'}))
    data_entrega = forms.DateField(
        label='Data da Entrega', widget=forms.DateInput(attrs={'type': 'date', 'required': 'required'}))
    quantidade = forms.IntegerField(
        label='Quantidade', min_value=1, widget=forms.NumberInput(attrs={'required': 'required'}))

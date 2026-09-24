from django import forms
from .models import Produto, Medicamento, Categoria


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'input-form', 'placeholder': 'Ex.: Analgésicos'}),
        }


class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = '__all__'
        widgets = {
            'data_validade': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'ultima_compra': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from datetime import date
        self.fields['data_validade'].input_formats = ['%Y-%m-%d']
        self.fields['ultima_compra'].input_formats = ['%Y-%m-%d']
        self.fields['data_validade'].widget.attrs['min'] = date.today().isoformat()
        self.fields['categoria'].empty_label = 'Selecione uma categoria...'

    def clean_data_validade(self):
        from datetime import date
        data_validade = self.cleaned_data.get('data_validade')
        if data_validade and data_validade < date.today():
            raise forms.ValidationError('Não é possível cadastrar um produto já vencido.')
        return data_validade

    def clean_quantidade(self):
        quantidade = self.cleaned_data.get('quantidade')
        if quantidade is not None and quantidade < 0:
            raise forms.ValidationError('A quantidade em estoque não pode ser negativa.')
        return quantidade

class MedicamentoForm(forms.ModelForm):
    class Meta:
        model = Medicamento
        fields = ['nome', 'dosagem', 'categoria', 'quantidade', 'estoque_minimo', 'data_validade', 'ultima_compra']
        widgets = {
            'data_validade': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'ultima_compra': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from datetime import date
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'input-form'})
        self.fields['data_validade'].input_formats = ['%Y-%m-%d']
        self.fields['ultima_compra'].input_formats = ['%Y-%m-%d']
        self.fields['data_validade'].widget.attrs['min'] = date.today().isoformat()
        self.fields['categoria'].empty_label = 'Selecione uma categoria...'

    def clean_data_validade(self):
        from datetime import date
        data_validade = self.cleaned_data.get('data_validade')
        if data_validade and data_validade < date.today():
            raise forms.ValidationError('Não é possível cadastrar um medicamento já vencido.')
        return data_validade

    def clean_quantidade(self):
        quantidade = self.cleaned_data.get('quantidade')
        if quantidade is not None and quantidade < 0:
            raise forms.ValidationError('A quantidade em estoque não pode ser negativa.')
        return quantidade

class EntregaForm(forms.Form):
    paciente = forms.CharField(label="Para quem", max_length=100)
    data_entrega = forms.DateField(label="Data da Entrega", widget=forms.DateInput(attrs={'type': 'date'}))
    quantidade = forms.IntegerField(label="Quantidade", min_value=1)

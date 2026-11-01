def dados_do_post(request):
    """`request.POST` se a requisição for um POST (mesmo vazio); senão None.

    Passar `request.POST or None` direto ao formulário tem uma armadilha: um
    POST sem nenhum campo é falsy, o formulário não é "ligado" e a pessoa
    não vê os erros de campo obrigatório. Aqui o critério é o método."""
    return request.POST if request.method == 'POST' else None


def marcar_campos_obrigatorios(form):
    """Põe o atributo HTML `required` em todo campo obrigatório do formulário
    (usado pelo script form-validation.js para liberar o botão de salvar)."""
    for campo in form.fields.values():
        if campo.required:
            campo.widget.attrs['required'] = 'required'


def aplicar_classe_input(form, classe='input-form'):
    """Aplica a mesma classe CSS a todos os campos do formulário."""
    for campo in form.fields.values():
        campo.widget.attrs['class'] = classe

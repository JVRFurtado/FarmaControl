/* Desabilita o botão de salvar/cadastrar até que todos os campos
 * obrigatórios do formulário estejam preenchidos. Funciona em qualquer
 * página sem configuração: procura campos com o atributo HTML `required`
 * e o botão de envio do mesmo formulário. Não faz nada em formulários sem
 * campos obrigatórios (ex.: filtros, busca), então é seguro incluir em
 * todas as páginas. */
(function () {
  function campoPreenchido(campo) {
    if (campo.type === 'checkbox' || campo.type === 'radio') {
      return campo.checked;
    }
    return campo.value !== null && campo.value.trim() !== '';
  }

  function validarFormulario(form, botao) {
    var obrigatorios = form.querySelectorAll('[required]');
    var completo = true;
    obrigatorios.forEach(function (campo) {
      if (!campoPreenchido(campo)) completo = false;
    });
    botao.disabled = !completo;
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form').forEach(function (form) {
      var obrigatorios = form.querySelectorAll('[required]');
      var botao = form.querySelector('button[type="submit"]');
      if (!botao || obrigatorios.length === 0) return;

      var atualizar = function () { validarFormulario(form, botao); };
      obrigatorios.forEach(function (campo) {
        campo.addEventListener('input', atualizar);
        campo.addEventListener('change', atualizar);
      });
      atualizar();
    });
  });
})();

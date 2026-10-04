/* Alternância manual de tema claro/escuro. Funciona junto com o script
 * inline de inicialização (farmacontrol/partials/tema_init.html), que evita
 * o "flash" de tema errado ao carregar a página. */
(function () {
  function temaAtual() {
    var manual = document.documentElement.getAttribute('data-theme');
    if (manual === 'dark' || manual === 'light') return manual;
    var prefereEscuro = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    return prefereEscuro ? 'dark' : 'light';
  }

  function atualizarBotao(botao, tema) {
    botao.setAttribute('aria-pressed', tema === 'dark' ? 'true' : 'false');
    botao.textContent = tema === 'dark' ? '☀️' : '🌙';
  }

  function aplicarTema(tema, botao) {
    document.documentElement.setAttribute('data-theme', tema);
    try {
      localStorage.setItem('farmacontrol-tema', tema);
    } catch (e) { /* localStorage indisponível — a escolha só vale para esta visita */ }
    if (botao) atualizarBotao(botao, tema);
  }

  document.addEventListener('DOMContentLoaded', function () {
    var botao = document.getElementById('theme-toggle');
    if (!botao) return;

    atualizarBotao(botao, temaAtual());

    botao.addEventListener('click', function () {
      var novoTema = temaAtual() === 'dark' ? 'light' : 'dark';
      aplicarTema(novoTema, botao);
    });
  });
})();

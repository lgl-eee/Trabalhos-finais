/* Recursos de acessibilidade: tamanho da fonte e alto contraste.
   As preferências ficam salvas no navegador (localStorage). */
(function () {
  var raiz = document.documentElement;
  var NIVEIS = ['0', '1', '2', '3']; // 0 = menor, 1 = padrão, 3 = maior

  function guardar(chave, valor) {
    try { localStorage.setItem(chave, valor); } catch (e) {}
  }

  function definirFonte(nivel) {
    nivel = Math.max(0, Math.min(3, nivel));
    raiz.setAttribute('data-fonte', String(nivel));
    guardar('ap-fonte', String(nivel));
  }

  document.querySelectorAll('[data-fonte-acao]').forEach(function (botao) {
    botao.addEventListener('click', function () {
      var atual = parseInt(raiz.getAttribute('data-fonte') || '1', 10);
      var acao = botao.getAttribute('data-fonte-acao');
      definirFonte(acao === 'mais' ? atual + 1 : acao === 'menos' ? atual - 1 : 1);
    });
  });

  var botaoContraste = document.getElementById('btn-contraste');
  if (botaoContraste) {
    var atualizar = function () {
      botaoContraste.setAttribute('aria-pressed', raiz.classList.contains('alto-contraste') ? 'true' : 'false');
    };
    atualizar();
    botaoContraste.addEventListener('click', function () {
      raiz.classList.toggle('alto-contraste');
      guardar('ap-contraste', raiz.classList.contains('alto-contraste') ? '1' : '0');
      atualizar();
    });
  }
})();

# FarmaControl — Acessibilidade (WCAG 2.1 nível AA)

Este documento registra o que foi implementado, como foi verificado e o que ainda precisa de verificação manual.

## 1. Critérios atendidos e como

| Critério WCAG | Implementação |
|---|---|
| 1.1.1 Conteúdo não textual | Ícones decorativos com `aria-hidden="true"`; logo com `alt=""` (decorativa, o nome aparece em texto); cada gráfico tem `role="img"`, `aria-labelledby` **e uma tabela equivalente** com os mesmos dados (visível só para leitores de tela) |
| 1.3.1 Informação e relações | `<html lang>` conforme o idioma escolhido; um `<h1>` por página; landmarks `<header>`, `<nav aria-label>`, `<main>`; tabelas com `<caption>` e `<th scope>`; todo campo com `<label for>` (ou `aria-label`); legenda de campos obrigatórios |
| 1.3.5 Finalidade da entrada | Campos de login e senha com rótulos claros |
| 1.4.1 Uso de cor | Status (Vencido, Vencendo, Estoque baixo) sempre com **texto** além da cor; links em texto corrido sublinhados |
| 1.4.3 Contraste (mínimo) | Todos os pares texto/fundo ≥ 4,5:1 nos temas claro e escuro (verificado por teste automático) |
| 1.4.4 / 1.4.10 Redimensionar e reflow | Layout responsivo sem rolagem horizontal da página; tabelas rolam dentro de região própria |
| 1.4.11 Contraste de não texto | Bordas de campos e botões ≥ 3:1 (`--border-input`); foco ≥ 3:1 |
| 1.4.12 Espaçamento de texto | Alturas mínimas (`min-height`), sem alturas fixas que cortem texto |
| 2.1.1 Teclado | Tudo operável por teclado; menu mobile, regiões de tabela rolável (`tabindex="0"`) e botão Salvar são focáveis |
| 2.4.1 Ignorar blocos | Link "Pular para o conteúdo" em todas as páginas (inclusive login) |
| 2.4.2 Título da página | `<title>` próprio em cada página |
| 2.4.3 / 2.4.7 Ordem e foco visível | Ordem do DOM coerente; contorno de foco de 3 px em links, botões e campos |
| 2.3.3 / boa prática | `prefers-reduced-motion` respeitado (animações e transições mínimas) |
| 3.1.1 / 3.1.2 Idioma | `lang` da página muda com o idioma; português e inglês completos |
| 3.2.x Previsibilidade | Troca de idioma avisa que recarrega a página (texto auxiliar para leitor de tela) |
| 3.3.1 / 3.3.2 / 3.3.3 Erros e instruções | Erros em bloco com `role="alert"` (anunciados automaticamente) listando campo e mensagem; obrigatórios marcados com `*` + legenda |
| 4.1.2 Nome, função, valor | Botões de ícone com `aria-label`; botão de tema com `aria-pressed`; botão Salvar usa `aria-disabled` e `aria-describedby` apontando para a legenda (continua focável e explica por que está indisponível) |
| 4.1.3 Mensagens de status | Mensagens de sucesso/erro com `role="status"`/`role="alert"` |

Também: suporte ao modo de alto contraste do Windows (`forced-colors`), alvos de toque de pelo menos 40 px em telas sensíveis ao toque e `accent-color` nas caixas de seleção.

## 2. Correções desta rodada
- **Contraste:** o texto do item de menu ativo no tema escuro (4,34:1) agora usa `--brand-on-light` (8,7:1); bordas de campos e botões (1,3:1) passaram para `--border-input` (≥ 3,4:1); número laranja do painel agora usa `--warning-text`.
- **Tabelas:** `<caption>` e região rolável focável em Estoque, Entregas, Movimentações, Relatórios e Usuários.
- **Entrega:** campo "Produto" ganhou rótulo associado.
- **Login:** conteúdo agora está em `<main>`, destino do link "Pular para o conteúdo".
- **Gráficos:** alternativa em tabela para os três gráficos.
- **Botão Salvar:** de `disabled` para `aria-disabled`, com explicação e foco no primeiro campo vazio se alguém tentar enviar.
- **CSS:** `prefers-reduced-motion`, `forced-colors`, `pointer: coarse`.

## 3. Como foi verificado
- **Testes automáticos** (`farmacontrol/tests/test_acessibilidade.py`): contraste de todos os pares de cores nos dois temas; para as 17 páginas autenticadas e para o login: `lang`, link de pular, `<main>`, um único `<h1>`, `alt` nas imagens, `scope` nos `<th>`, rótulo em todo campo; legenda e região focável nas tabelas; `lang` em inglês.
- **Auditoria estática** dos 22 templates (rótulos, landmarks, hierarquia de títulos, nomes de botões e links).
- **Limitação:** não foi possível rodar Lighthouse, axe ou leitor de tela no ambiente de desenvolvimento.

## 4. Checklist de verificação manual (recomendado antes da entrega)
1. **Lighthouse** (Chrome → F12 → Lighthouse → Accessibility) em: login, dashboard, estoque, relatórios, análises, usuários. Meta: ≥ 95.
2. **WAVE** (extensão wave.webaim.org) nas mesmas páginas — deve mostrar 0 erros.
3. **Teclado:** percorrer o login e o cadastro de produto só com Tab/Shift+Tab/Enter; o foco deve ser sempre visível; o primeiro Tab deve revelar "Pular para o conteúdo".
4. **Leitor de tela** (NVDA no Windows ou VoiceOver): conferir se o botão Salvar anuncia "indisponível" + legenda, se erros são anunciados e se as tabelas dos gráficos são lidas.
5. **Zoom 200 %** e largura de 320 px: sem perda de conteúdo.
6. **Tema escuro** e idioma inglês nas mesmas páginas.

Resultados dessas verificações podem ser anexados aqui como evidência do projeto.

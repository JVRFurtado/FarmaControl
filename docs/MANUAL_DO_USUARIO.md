# FarmaControl — Manual do Usuário

Para **Atendentes** e **Gestores**. (Administração do sistema: veja o *Manual do Administrador*.)

## 1. Primeiros passos

1. Abra o endereço do sistema e entre com **usuário e senha** fornecidos pela sua equipe.
2. Se a senha foi gerada para você, troque-a: ícone de **chave** no cabeçalho (no celular: menu ☰ → "Alterar senha").
3. Escolha **idioma** (Português/English) e **tema** (🌙/☀️) no cabeçalho. Se você não escolher, o sistema usa o idioma e o tema do seu navegador/aparelho.
4. Para sair, use o botão **Sair**.

### Cabeçalho
Logo e nome (volta ao início) · menu: Início, Estoque, Categorias, Entregas, Movimentações, Relatórios, Análises (e Usuários, só para Gestor) · idioma · tema · sair. No celular, o menu fica no botão ☰, no fim da barra.

## 2. Início (painel)

Cartões clicáveis: **Produtos cadastrados**, **Estoque baixo**, **Vencendo em breve** e **Vencidos**. Clicar leva ao Estoque já filtrado. Abaixo, a lista de **alertas recentes** (vencidos primeiro, depois a vencer, depois estoque baixo). Se nada estiver pendente aparece "Tudo em dia!".

## 3. Estoque

- **Busca** por nome e **filtros** (estoque baixo, vencendo, vencidos, normal).
- Colunas: quantidade (com aviso de estoque baixo) e validade (data e, abaixo, a situação: Normal, Vence em N dias, Vencido).
- Linhas de produtos vencidos/vencendo ficam destacadas.
- Ações por linha: **Entregar** e **Histórico**; Gestores também veem **Editar** e **Excluir**.
- A lista é paginada (50 itens por página).

### Cadastrar produto ou medicamento
1. Clique em **Adicionar Produto** ou **Adicionar Medicamento**.
2. Preencha os campos marcados como obrigatórios — o botão **Salvar** só habilita quando estiverem completos.
3. Regras: quantidade não pode ser negativa; altura/largura/comprimento são números; a validade não pode estar no passado; **estoque mínimo** define quando o alerta de estoque baixo dispara.
4. Medicamentos têm também o campo **dosagem**.

### Editar / excluir (Gestor)
- **Editar** altera os dados do produto.
- **Excluir** pede confirmação. A exclusão fica registrada nas movimentações.

## 4. Entregar um produto

1. Na lista, clique em **Entregar** no produto.
2. Informe **paciente**, **quantidade** e **data**.
3. Confirme. O estoque diminui automaticamente. Se a quantidade for maior que o estoque, o sistema avisa e não registra.

A entrega aparece em **Entregas** e como saída em **Movimentações**.

## 5. Categorias

Lista as categorias; qualquer usuário pode **adicionar**. Somente o Gestor **exclui**. Produtos de uma categoria excluída ficam sem categoria.

## 6. Históricos

- **Entregas:** produto, paciente, quantidade, data e responsável. Tem filtros e paginação.
- **Movimentações:** toda entrada e saída (cadastro, ajuste, entrega, exclusão), com motivo, data e responsável.

## 7. Relatórios

1. Escolha o relatório: Estoque atual, Estoque baixo, Vencendo em breve, Vencidos, Histórico de entregas ou Movimentações.
2. Filtre por **categoria** e, para Entregas/Movimentações, por **período** (De/Até).
3. Use **Ver relatório** (tela), **Exportar CSV** ou **Exportar Excel**. Os arquivos saem no idioma atual.

## 8. Análises

Três gráficos: estoque por categoria (barras), situação dos produtos (rosca: normal/vencendo/vencido/sem validade) e entradas × saídas dos últimos 30 dias (linha). Sem produtos cadastrados, aparece um aviso.

## 9. Gestão de usuários (somente Gestor)

Menu **Usuários**: lista com cargo e status.
- **Adicionar:** usuário, e-mail, cargo (Atendente ou Gestor) e senha.
- **Editar:** dados de Atendentes (e os seus próprios). Pode **promover** Atendente a Gestor.
- **Senha:** define nova senha para você ou para Atendentes.
- O Gestor **não** pode alterar outro Gestor, rebaixar, desativar ou remover usuários — peça ao Administrador.

## 10. Acessibilidade e conforto de uso

- **Teclado:** use Tab e Shift+Tab para navegar e Enter para ativar. O primeiro Tab de cada página mostra "Pular para o conteúdo".
- **Leitor de tela:** as páginas têm títulos, regiões e rótulos; os gráficos têm uma tabela equivalente com os mesmos dados.
- **Tema e idioma:** escolha tema claro/escuro e Português/English no cabeçalho; o sistema respeita as preferências do seu aparelho.
- **Zoom:** a interface se adapta até 200 % de zoom e a telas de celular.
- **Botão Salvar indisponível:** significa que há campo obrigatório (*) vazio; o sistema informa e leva você ao primeiro campo pendente.

## 11. Perguntas frequentes

**Não consigo entrar.** Confira usuário e senha (diferencia maiúsculas). Se estiver correto, a conta pode estar desativada: fale com o Administrador.

**Não vejo o botão Editar/Excluir ou o menu Usuários.** São exclusivos de Gestor/Administrador.

**O botão Salvar está desabilitado.** Falta preencher algum campo obrigatório.

**Esqueci minha senha.** Peça a um Gestor (se você for Atendente) ou ao Administrador para redefinir.

**A página abriu devagar no primeiro acesso.** Em hospedagem gratuita o sistema "dorme" após inatividade; aguarde cerca de um minuto.

**Aparece "Acesso negado" (403).** Você não tem permissão para essa ação.

# FarmaControl — Documentação Técnica

Sistema web de controle de estoque e distribuição de medicamentos e materiais de saúde (projeto integrador).

> Documento de referência para desenvolvedores. A fundamentação, os requisitos, a modelagem com diagramas, a verificação e a discussão dos resultados estão no [Relatório técnico](RELATORIO_TECNICO.md).

Em produção: https://farmacontrol-mxr1.onrender.com

## 1. Visão geral

| Item | Tecnologia |
|---|---|
| Linguagem / framework | Python 3.12 · Django 5.2 |
| Banco de dados | PostgreSQL (produção, Render) · SQLite (desenvolvimento) |
| Front-end | HTML + CSS próprio (variáveis CSS, tema claro/escuro) + JavaScript puro · Chart.js (CDN) · Font Awesome (CDN) |
| Arquivos estáticos | WhiteNoise (`CompressedManifestStaticFilesStorage` em produção) |
| Servidor | Gunicorn |
| Hospedagem | Render (`render.yaml`, `build.sh`) |
| Exportação | CSV (biblioteca padrão) e Excel (`openpyxl`) |
| API | JSON somente leitura em `/api/` (ver `docs/API.md`) |
| Testes | `unittest` do Django + `coverage` (199 testes) |
| Controle de versão | Git / GitHub |

## 2. Estrutura do projeto

```
FarmaControl/
├── manage.py
├── build.sh · render.yaml · Procfile · .python-version   # deploy
├── requirements.txt · requirements-dev.txt
├── farmacontrol/            # configuração do projeto
│   ├── settings.py · urls.py · wsgi.py
│   ├── i18n.py              # dicionário de traduções pt-br / en
│   ├── context_processors.py# disponibiliza `t`, idioma e tema aos templates
│   ├── formatacao.py · formularios.py · paginacao.py
│   ├── views.py             # troca de idioma
│   └── partials/            # header.html, paginacao.html, favicon, tema_init
├── estoque/                 # produtos, categorias, entregas, movimentações, relatórios
│   ├── models.py · forms.py · views.py · urls.py
│   ├── api.py · api_urls.py # API JSON somente leitura (/api/)
│   ├── relatorios.py        # montagem de relatórios + exportação CSV/Excel
│   ├── movimentacoes.py     # registro e tradução de motivos
│   ├── templatetags/i18n_extras.py
│   ├── static/estoque/{css,js}/
│   └── templates/estoque/
├── usuarios/                # autenticação, cargos, gestão de usuários, dashboard
│   ├── models.py · forms.py · views.py · urls.py
│   ├── permissoes.py        # regras "quem pode o quê" (fonte única)
│   ├── decorators.py        # @gestor_required
│   └── management/commands/{createsu,create_roles}.py
└── docs/
```

## 3. Modelo de dados

- **Users** (`usuarios.Users`, estende `AbstractUser`): `cargo` (`G` Gestor / `A` Atendente), `email` único. O **Admin** é um usuário com `is_superuser=True`.
- **Categoria**: `nome` (único). Categorias padrão criadas pela migração `0004`.
- **Produto**: `nome`, `altura`/`largura`/`comprimento` (decimais), `categoria` (FK, `SET_NULL`), `quantidade` (≥ 0), `estoque_minimo`, `data_validade`, `ultima_compra`. Restrição única `unique_produto_completo`.
- **Medicamento** (herda de Produto): acrescenta `dosagem`.
- **Entrega**: produto (FK `SET_NULL`) + `produto_nome` (cópia, preserva histórico), `paciente`, `quantidade`, `data_entrega`, `usuario`, `registrado_em`.
- **MovimentacaoEstoque**: produto + `produto_nome`, `tipo` (entrada/saída), `quantidade`, `motivo`, `motivo_codigo`, `motivo_detalhe`, `usuario`, `data`. Motivos: cadastro de produto/medicamento, ajuste manual, entrega, exclusão.

Os históricos guardam o nome do produto como texto para continuarem legíveis mesmo após a exclusão do produto.

## 4. Regras de negócio

- **Estoque baixo:** `quantidade <= estoque_minimo`.
- **Vencimento** (`DIAS_AVISO_VENCIMENTO = 30`): mais de 30 dias → normal; 30 dias ou menos → aviso ("vencendo"); data passada → vencido.
- Status é **calculado na consulta** (`ProdutoQuerySet`: `estoque_baixo`, `vencendo`, `vencidos`, `validade_normal`, `por_filtro`), nunca gravado, para não ficar desatualizado.
- **Validações:** quantidade não negativa; medidas numéricas; data de validade passada bloqueada no cadastro (na edição só se o campo for alterado); campos obrigatórios marcados e botão "Salvar" desabilitado até o preenchimento.
- **Entrega:** executada em `transaction.atomic` com `select_for_update` (evita corrida entre dois atendentes); bloqueia quantidade acima do estoque; grava `Entrega` + `MovimentacaoEstoque` de saída.
- **Exclusão de produto:** somente via POST com tela de confirmação; registra movimentação de saída.
- Listagens paginadas (50 por página).

## 5. Permissões

Centralizadas em `usuarios/permissoes.py` e usadas tanto pelas views quanto pelos templates.

| Ação | Atendente | Gestor | Admin |
|---|:-:|:-:|:-:|
| Consultar estoque, relatórios, análises, históricos | ✅ | ✅ | ✅ |
| Cadastrar produto/medicamento/categoria; registrar entrega | ✅ | ✅ | ✅ |
| Editar/excluir produto; excluir categoria | ❌ | ✅ | ✅ |
| Acessar gestão de usuários | ❌ | ✅ | ✅ |
| Criar Atendente ou Gestor | ❌ | ✅ | ✅ |
| Trocar a senha | ❌ | própria e de Atendentes | de qualquer um |
| Promover Atendente → Gestor | ❌ | ✅ | ✅ |
| Alterar cargo de qualquer usuário / rebaixar | ❌ | ❌ | ✅ |
| Ativar/desativar usuário | ❌ | ❌ | ✅ |
| Editar outro Gestor | ❌ | ❌ | ✅ |

Todas as rotas exigem login (`@login_required`); rotas restritas usam `@gestor_required` (Gestor ou superusuário), retornando 403 caso contrário. Usuários não são excluídos, apenas desativados, preservando a rastreabilidade.

## 6. Rotas principais

| Rota | Função |
|---|---|
| `/` , `/usuarios/login/` | Login |
| `/usuarios/dashboard/` | Painel com cartões e alertas recentes |
| `/estoque/` | Lista de produtos (busca + filtros) |
| `/estoque/adicionar/` · `/adicionar-medicamento/` | Cadastros |
| `/estoque/editar/<id>/` · `/excluir/<id>/` | Edição / exclusão (Gestor) |
| `/estoque/produtos/<id>/entregar/` | Registrar entrega |
| `/estoque/categorias/` (+ `adicionar/`, `excluir/<id>/`) | Categorias |
| `/estoque/entregas/` · `/estoque/movimentacoes/` | Históricos |
| `/estoque/relatorios/` | Relatórios (tela, CSV, Excel) |
| `/estoque/analises/` | Gráficos |
| `/usuarios/usuarios/` (+ `adicionar/`, `<id>/editar/`, `<id>/senha/`, `<id>/status/`) | Gestão de usuários |
| `/auth/password_change/` | Troca da própria senha |
| `/idioma/<codigo>/?next=…` | Troca de idioma |
| `/api/…` | API JSON somente leitura (ver `API.md`) |
| `/admin/` | Admin do Django |

### API
Endpoints `GET` em `/api/` (produtos, alertas, categorias, entregas, movimentações) com autenticação por sessão, paginação e filtros; erros em JSON. Detalhes e exemplos em [`API.md`](API.md).

## 7. Internacionalização e tema

- Idiomas: pt-br e en, em `farmacontrol/i18n.py`. Prioridade: cookie `idioma` → cabeçalho `Accept-Language` → pt-br. O seletor grava o cookie por 1 ano; o redirecionamento pós-troca é protegido contra *open redirect*.
- Textos vêm de `{{ t.secao.chave }}` nos templates; views usam `traducoes_da_requisicao`. Relatórios exportados e legendas de gráficos também são traduzidos.
- Tema: variáveis CSS; automático por `prefers-color-scheme`, manual por botão (grava em `localStorage`, chave `farmacontrol-tema`).
- Para adicionar um texto: inclua a mesma chave em **pt-br e en** (testes verificam a paridade).

## 8. Segurança

- `SECRET_KEY` e `DATABASE_URL` só por variáveis de ambiente; sem `SECRET_KEY` em produção a aplicação não inicia.
- `DEBUG=False` por padrão. Em produção: HTTPS forçado, cookies `Secure`, HSTS, `X-Frame-Options: DENY`, `nosniff`.
- CSRF em todos os formulários POST; exclusões e logout apenas via POST.
- Senhas validadas pelos validadores do Django; senhas iniciais vêm do ambiente (nunca fixas no código).
- Controle de acesso por cargo em todas as rotas, com testes automatizados.

## 9. Acessibilidade (WCAG 2.1 AA) — detalhes em `ACESSIBILIDADE.md`

Link "pular para o conteúdo", ícones decorativos com `aria-hidden`, `scope="col"` nas tabelas, mensagens com `role="status"/"alert"`, foco visível, rótulos reais nos campos, gráficos com `role="img"` e `aria-labelledby`, layout responsivo (cabeçalho em linha única; hambúrguer no mobile).

## 10. Testes

```bash
pip install -r requirements-dev.txt
python manage.py test                       # 199 testes
coverage run --source='.' manage.py test && coverage report
```
Cobertura anterior à refatoração: 92 %. Detalhes em `TESTES.md`; mudanças estruturais em `REFATORACAO.md`.

## 11. Executar localmente

```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
export DEBUG=True                                    # Windows PowerShell: $env:DEBUG="True"
python manage.py migrate
export ADMIN_INITIAL_PASSWORD='SenhaForte123'
python manage.py createsu && python manage.py create_roles
python manage.py runserver
```
Sem `DATABASE_URL`, usa SQLite (`db.sqlite3`).

## 12. Deploy

Ver `DEPLOY.md`. Resumo: Render lê `render.yaml`; `build.sh` instala dependências, executa `collectstatic` e `migrate` e cria os usuários iniciais. Variáveis: `SECRET_KEY`, `DEBUG`, `DATABASE_URL`, `PYTHON_VERSION`, `ADMIN_/GESTOR_/ATENDENTE_INITIAL_PASSWORD`, opcional `ALLOWED_HOSTS`.

## 13. Limitações conhecidas

- Sem exportação em PDF (CSV e Excel disponíveis).
- Sem recuperação de senha por e-mail (a senha é redefinida por Gestor/Admin).
- Mensagens do framework de mensagens do Django estão traduzidas; páginas de erro 403/404 usam o padrão do Django.
- Dependência `django-role-permissions` ainda instalada, embora a autorização use `permissoes.py`.

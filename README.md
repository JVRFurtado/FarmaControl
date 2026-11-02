# 💊 FarmaControl

Sistema web de **controle de estoque e distribuição de medicamentos e materiais de saúde**, desenvolvido como projeto integrador com Django e PostgreSQL e hospedado em nuvem.

🌐 **Em produção:** https://farmacontrol-mxr1.onrender.com
*(plano gratuito: o primeiro acesso após um período parado pode levar cerca de 1 minuto)*

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-banco-4169E1?logo=postgresql&logoColor=white)
![WCAG](https://img.shields.io/badge/WCAG-2.1%20AA-blue)
![Testes](https://img.shields.io/badge/testes-199-brightgreen)

---

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Funcionalidades](#2-funcionalidades)
3. [Perfis e permissões](#3-perfis-e-permissões)
4. [Tecnologias](#4-tecnologias)
5. [Estrutura do projeto](#5-estrutura-do-projeto)
6. [Executando localmente](#6-executando-localmente)
7. [Variáveis de ambiente](#7-variáveis-de-ambiente)
8. [Testes](#8-testes)
9. [API JSON](#9-api-json)
10. [Deploy no Render](#10-deploy-no-render)
11. [Segurança](#11-segurança)
12. [Acessibilidade](#12-acessibilidade)
13. [Internacionalização e tema](#13-internacionalização-e-tema)
14. [Documentação completa](#14-documentação-completa)
15. [Limitações conhecidas e próximos passos](#15-limitações-conhecidas-e-próximos-passos)
16. [Autoria e licença](#16-autoria-e-licença)

---

## 1. Visão geral

O FarmaControl ajuda uma equipe pequena a responder, a qualquer momento:

- **O que está acabando?** Alertas de estoque abaixo do mínimo definido por item.
- **O que está vencendo?** Regra de validade: mais de 30 dias (normal), 30 dias ou menos (aviso) e vencido.
- **Quem retirou, quando e para quem?** Cada entrega e cada movimentação de estoque fica registrada com responsável, data e motivo.
- **Como estamos?** Relatórios filtráveis, exportação em CSV/Excel e gráficos.

O sistema é responsivo (celular e computador), tem tema claro/escuro, está em português e inglês e segue critérios de acessibilidade das WCAG 2.1 nível AA.

## 2. Funcionalidades

| Área | O que faz |
|---|---|
| **Painel (início)** | Cartões clicáveis (produtos, estoque baixo, vencendo, vencidos) que levam à lista já filtrada; lista de alertas recentes |
| **Estoque** | Cadastro de produtos e medicamentos (dosagem), busca, filtros de situação e de categoria, edição, exclusão com confirmação, paginação |
| **Alertas** | Estoque baixo (`quantidade ≤ estoque mínimo`) e vencimento, calculados na hora (nunca ficam desatualizados) |
| **Entregas** | Registro de entrega a paciente com quantidade e data; abate o estoque em transação atômica e impede saldo negativo |
| **Movimentações** | Histórico de toda entrada e saída (cadastro, ajuste, entrega, exclusão) com motivo traduzido no idioma escolhido |
| **Categorias** | Criar, listar e excluir (categorias padrão já incluídas) |
| **Relatórios** | Estoque atual, estoque baixo, vencendo, vencidos, entregas e movimentações, com filtros de categoria e período; exportação em **CSV** e **Excel** |
| **Análises** | Gráficos de estoque por categoria, situação de validade e entradas × saídas dos últimos 30 dias |
| **Usuários** | Criar Atendentes e Gestores, trocar senhas, promover, ativar/desativar contas (conforme o perfil) |
| **API** | Consulta em JSON (somente leitura) de produtos, alertas, categorias, entregas e movimentações |
| **Interface** | Responsiva, tema claro/escuro automático ou manual, idiomas pt-BR/en, cabeçalho em linha única |

## 3. Perfis e permissões

Três níveis de acesso; as regras ficam centralizadas em `usuarios/permissoes.py`.

| Ação | Atendente | Gestor | Admin |
|---|:-:|:-:|:-:|
| Consultar estoque, históricos, relatórios, análises e API | ✅ | ✅ | ✅ |
| Cadastrar produto, medicamento e categoria; registrar entrega | ✅ | ✅ | ✅ |
| Editar/excluir produto; excluir categoria | ❌ | ✅ | ✅ |
| Gerenciar usuários; criar Atendente ou Gestor | ❌ | ✅ | ✅ |
| Trocar senha | ❌ | própria e de Atendentes | de qualquer usuário |
| Promover Atendente → Gestor | ❌ | ✅ | ✅ |
| Alterar qualquer cargo / rebaixar; editar outro Gestor | ❌ | ❌ | ✅ |
| Ativar ou desativar contas | ❌ | ❌ | ✅ |

> O **Admin** é o superusuário do Django (`is_superuser`). Contas **não são excluídas**, apenas desativadas, para preservar o histórico de quem fez o quê.

## 4. Tecnologias

| Camada | Tecnologia |
|---|---|
| Linguagem / framework | Python 3.12 · Django 5.2 |
| Banco de dados | PostgreSQL (produção) · SQLite (desenvolvimento) |
| Front-end | HTML5 · CSS3 (variáveis, tema) · JavaScript · Chart.js · Font Awesome |
| Servidor e estáticos | Gunicorn · WhiteNoise |
| Exportação | `csv` (biblioteca padrão) · openpyxl |
| Testes | Testes do Django · coverage |
| Hospedagem e versão | Render · Git/GitHub |

## 5. Estrutura do projeto

```
FarmaControl/
├── manage.py
├── build.sh · render.yaml · Procfile · .python-version   # deploy (Render)
├── requirements.txt · requirements-dev.txt
├── farmacontrol/             # configuração do projeto
│   ├── settings.py · urls.py · wsgi.py
│   ├── i18n.py               # traduções pt-br / en
│   ├── context_processors.py # disponibiliza traduções, idioma e tema aos templates
│   └── partials/             # cabeçalho, paginação, favicon, tema
├── estoque/                  # produtos, categorias, entregas, movimentações
│   ├── models.py · forms.py · views.py · urls.py
│   ├── api.py · api_urls.py  # API JSON (somente leitura)
│   ├── relatorios.py         # relatórios + exportação CSV/Excel
│   ├── static/estoque/       # CSS (sistema de design) e JavaScript
│   └── templates/estoque/
├── usuarios/                 # login, cargos, permissões, gestão de usuários, painel
│   ├── permissoes.py         # quem pode o quê (fonte única)
│   ├── decorators.py         # @gestor_required
│   └── management/commands/  # createsu, create_roles
└── docs/                     # relatório técnico, manuais, API, acessibilidade
```

## 6. Executando localmente

**Pré-requisitos:** Python 3.12+ e Git. Não é necessário instalar PostgreSQL: sem `DATABASE_URL`, o projeto usa SQLite.

### Linux / macOS

```bash
git clone https://github.com/JVRFurtado/FarmaControl.git
cd FarmaControl

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export DEBUG=True
export ADMIN_INITIAL_PASSWORD='SenhaForte123'   # defina a sua

python manage.py migrate
python manage.py createsu        # cria o usuário "admin"
python manage.py create_roles    # cria "gestor" e "atendente" (senhas geradas e mostradas no terminal)
python manage.py runserver
```

### Windows (PowerShell)

```powershell
git clone https://github.com/JVRFurtado/FarmaControl.git
cd FarmaControl

python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:DEBUG = "True"
$env:ADMIN_INITIAL_PASSWORD = "SenhaForte123"

python manage.py migrate
python manage.py createsu
python manage.py create_roles
python manage.py runserver
```

> Dica: o arquivo `start.ps1` ativa o ambiente virtual e inicia o servidor. Se o PowerShell bloquear scripts, rode `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

Acesse **http://127.0.0.1:8000/** e entre com `admin` e a senha definida (ou `gestor` / `atendente` com as senhas exibidas pelo `create_roles`). Para definir as senhas desses dois usuários, use as variáveis `GESTOR_INITIAL_PASSWORD` e `ATENDENTE_INITIAL_PASSWORD` antes de rodar `create_roles`.

> ⚠️ **Troque as senhas iniciais** no primeiro acesso (ícone de chave no cabeçalho).

### Usuários criados pelos comandos

| Usuário | Perfil | Comando | Senha |
|---|---|---|---|
| `admin` | Admin (superusuário) | `createsu` | `ADMIN_INITIAL_PASSWORD` (obrigatória) |
| `gestor` | Gestor | `create_roles` | `GESTOR_INITIAL_PASSWORD` ou aleatória |
| `atendente` | Atendente | `create_roles` | `ATENDENTE_INITIAL_PASSWORD` ou aleatória |

Os comandos são idempotentes: não recriam usuários que já existem.

## 7. Variáveis de ambiente

| Variável | Obrigatória | Descrição |
|---|:-:|---|
| `SECRET_KEY` | Em produção | Chave criptográfica do Django. Sem ela, com `DEBUG` desligado, a aplicação **não inicia** |
| `DEBUG` | Não | `True` só em desenvolvimento. Padrão: `False` |
| `DATABASE_URL` | Em produção | Conexão PostgreSQL. Sem ela, usa SQLite local (`db.sqlite3`) |
| `ALLOWED_HOSTS` | Não | Hosts extras, separados por vírgula (o host do Render é incluído automaticamente) |
| `PYTHON_VERSION` | No Render | Ex.: `3.12.7` |
| `ADMIN_INITIAL_PASSWORD` | Para `createsu` | Senha do usuário `admin` |
| `GESTOR_INITIAL_PASSWORD` | Opcional | Senha inicial do `gestor` |
| `ATENDENTE_INITIAL_PASSWORD` | Opcional | Senha inicial do `atendente` |

Gerar uma `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

## 8. Testes

```bash
python manage.py test                        # toda a suíte (199 testes)
python manage.py test estoque                # só um app
python manage.py test usuarios.tests.test_permissoes   # só um módulo
```

Cobertura de código:

```bash
pip install -r requirements-dev.txt
coverage run --source='.' manage.py test
coverage report
coverage html          # relatório navegável em htmlcov/index.html
```

| Área | Testes |
|---|---:|
| Modelos, formulários e tags de template | 38 |
| Filtros de consulta e refatoração | 25 |
| Views, categorias e consultas | 31 |
| API JSON | 18 |
| Permissões e usuários | 58 |
| Idioma, utilitários e acessibilidade | 29 |
| **Total** | **199** |

Última cobertura medida (Etapa 1, 128 testes): **92 %**. Detalhes em [`TESTES.md`](TESTES.md).

## 9. API JSON

API **somente leitura** (`GET`), com a mesma sessão e o mesmo controle de acesso do site. Sem login responde `401` em JSON.

| Endpoint | Descrição |
|---|---|
| `GET /api/` | Índice da API |
| `GET /api/produtos/` | Produtos e medicamentos — filtros `buscar`, `categoria`, `filtro` (`estoque_baixo`, `vencendo`, `vencidos`, `normal`) |
| `GET /api/produtos/{id}/` | Detalhe de um item |
| `GET /api/alertas/` | Totais e listas de vencidos, vencendo e estoque baixo |
| `GET /api/categorias/` | Categorias |
| `GET /api/entregas/` | Histórico de entregas — filtros `produto`, `buscar` |
| `GET /api/movimentacoes/` | Entradas e saídas — filtros `produto`, `tipo` |

Listas paginadas com `?page=` e `?por_pagina=` (padrão 50, máximo 100). Exemplo rápido, com o navegador já logado:

```js
const r = await fetch('/api/produtos/?filtro=vencendo');
console.log(await r.json());
```

Documentação completa e exemplos em curl e Python: [`docs/API.md`](docs/API.md).

## 10. Deploy no Render

O repositório já traz `render.yaml`, `build.sh` e `Procfile`.

1. Envie o código para o GitHub.
2. No Render: **New → Blueprint** e selecione o repositório (ou crie manualmente um *Web Service* + um PostgreSQL).
3. Se criar manualmente, configure:
   - **Build Command:** `bash build.sh`
   - **Start Command:** `gunicorn farmacontrol.wsgi:application --log-file -`
4. Defina as variáveis de ambiente (seção 7). A `DATABASE_URL` deve ser a **Internal Database URL** do banco.
5. A cada deploy, o `build.sh` instala as dependências, roda `collectstatic` e `migrate` e cria os usuários iniciais (quando as senhas estão definidas).

Passo a passo e checklist de validação: [`DEPLOY.md`](DEPLOY.md). Problemas comuns de implantação estão no [Manual do administrador](docs/MANUAL_DO_ADMINISTRADOR.md).

> No plano gratuito o serviço "dorme" por inatividade e o banco expira em 30 dias: faça *backup* (`pg_dump "$DATABASE_URL" > backup.sql`) antes de apresentações ou entregas.

## 11. Segurança

- `SECRET_KEY` e `DATABASE_URL` apenas por variáveis de ambiente; nenhuma credencial no código.
- `DEBUG` desligado por padrão; em produção: HTTPS forçado, HSTS, *cookies* seguros, `X-Frame-Options: DENY`, `nosniff`.
- Proteção CSRF em todos os formulários; exclusões e logout somente via `POST`.
- Controle de acesso por perfil verificado no servidor em todas as rotas, com testes por perfil.
- Troca de idioma protegida contra redirecionamento aberto.
- Senhas validadas pelos validadores do Django; senhas iniciais definidas por ambiente.
- Transações com bloqueio de linha nas entregas (sem saldo negativo por concorrência).

> **Dados pessoais:** as entregas guardam o nome do paciente. Para uso real, avalie a adequação à LGPD (base legal, retenção, controle de acesso e *backups*).

## 12. Acessibilidade

Implementada com base nas **WCAG 2.1 nível AA**: link "Pular para o conteúdo", `lang` conforme o idioma, um `h1` por página, landmarks (`header`, `nav`, `main`), rótulos em todos os campos, tabelas com legenda e `scope`, gráficos com tabela equivalente, mensagens com `role="status"/"alert"`, foco visível, contraste mínimo de 4,5:1 (texto) e 3:1 (componentes) nos dois temas, suporte a `prefers-reduced-motion` e a alto contraste, e navegação completa por teclado. Parte da verificação é automática (testes de contraste e estrutura). Veja [`docs/ACESSIBILIDADE.md`](docs/ACESSIBILIDADE.md) para o detalhamento e o checklist de verificação manual (Lighthouse, WAVE, leitor de tela).

## 13. Internacionalização e tema

- **Idioma:** escolha manual no cabeçalho (cookie por 1 ano) → idioma do navegador (`Accept-Language`) → português. Traduções em `farmacontrol/i18n.py`; para criar um texto novo, adicione a **mesma chave em `pt-br` e `en`** (um teste verifica a paridade).
- **Tema:** automático conforme o sistema operacional ou manual pelo botão 🌙/☀️ (guardado no navegador).

## 14. Documentação completa

| Documento | Conteúdo |
|---|---|
| [Relatório técnico](docs/RELATORIO_TECNICO.md) ([Word](docs/RELATORIO_TECNICO.docx) · [PDF](docs/RELATORIO_TECNICO.pdf)) | Texto acadêmico: objetivos, fundamentação, requisitos, arquitetura com diagramas, implementação, testes, nuvem, resultados |
| [Documentação técnica](docs/DOCUMENTACAO_TECNICA.md) | Referência para desenvolvedores |
| [Manual do usuário](docs/MANUAL_DO_USUARIO.md) | Uso do sistema por Atendentes e Gestores |
| [Manual do administrador](docs/MANUAL_DO_ADMINISTRADOR.md) | Instalação, usuários, backup, solução de problemas |
| [API JSON](docs/API.md) | Endpoints, parâmetros e exemplos |
| [Acessibilidade](docs/ACESSIBILIDADE.md) | Critérios atendidos e verificação |
| [Deploy](DEPLOY.md) · [Testes](TESTES.md) · [Refatoração](REFATORACAO.md) | Operação, suíte de testes e histórico de refatoração |

## 15. Limitações conhecidas e próximos passos

**Limitações atuais**
- Sem exportação em PDF (CSV e Excel disponíveis) e sem recuperação de senha por e-mail (a senha é redefinida por Gestor/Admin).
- Controle de **um** local de estoque; sem lotes múltiplos por item, fornecedores ou compras.
- A API usa autenticação por sessão (sem *tokens*) e é somente leitura.
- A acessibilidade foi verificada por testes automáticos e auditoria estrutural; falta auditoria com tecnologias assistivas.
- Dependência `django-role-permissions` ainda instalada, embora a autorização use o módulo próprio.

**Ideias futuras**
- Notificação por e-mail dos alertas; controle por lote e fornecedor.
- API com *tokens* e documentação OpenAPI.
- Exportação em PDF.
- Adequação completa à LGPD (política de retenção, anonimização).
- *Backup* e monitoramento em plano de hospedagem pago.

## 16. Autoria e licença

Projeto integrador desenvolvido por **João Furtado** ([@JVRFurtado](https://github.com/JVRFurtado)).

Licença: *[definir — ex.: MIT, ou "uso acadêmico, todos os direitos reservados"]*.

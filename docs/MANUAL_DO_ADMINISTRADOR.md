# FarmaControl — Manual do Administrador

Para quem instala, mantém e administra o sistema. **Admin** = superusuário do Django (`is_superuser`); tem os privilégios do Gestor e mais.

## 1. Responsabilidades exclusivas do Admin

| Ação | Onde |
|---|---|
| Trocar a senha de **qualquer** usuário | Usuários → Senha |
| Alterar o **cargo** de qualquer usuário (inclusive rebaixar Gestor → Atendente) | Usuários → Editar |
| **Ativar/desativar** contas | Usuários → Ativar/Desativar |
| Editar outros Gestores | Usuários → Editar |
| Acessar o painel `/admin/` do Django | URL `/admin/` |

Gestores não têm essas permissões (podem criar usuários, trocar a senha própria e de Atendentes e promover Atendente a Gestor). Você não pode desativar a própria conta.

> Contas **não são excluídas**: desativar bloqueia o login imediatamente e preserva o histórico de entregas e movimentações. Reativar restaura o acesso.

## 2. Instalação em produção (Render)

Resumo; passo a passo completo em `DEPLOY.md`.

1. Publique o repositório no GitHub.
2. Render → **New → Blueprint** (usa `render.yaml`) ou crie Web Service + PostgreSQL manualmente.
3. Configurações do serviço:
   - **Build Command:** `bash build.sh`
   - **Start Command:** `gunicorn farmacontrol.wsgi:application --log-file -`
4. Variáveis de ambiente:

| Variável | Descrição |
|---|---|
| `PYTHON_VERSION` | `3.12.7` |
| `DEBUG` | `False` (nunca `True` em produção) |
| `SECRET_KEY` | chave longa e aleatória (`python -c "import secrets; print(secrets.token_urlsafe(50))"`) |
| `DATABASE_URL` | Internal Database URL do PostgreSQL |
| `ADMIN_INITIAL_PASSWORD` | senha do usuário `admin` |
| `GESTOR_INITIAL_PASSWORD` / `ATENDENTE_INITIAL_PASSWORD` | senhas iniciais de `gestor` e `atendente` |
| `ALLOWED_HOSTS` | opcional; o host do Render é incluído automaticamente |

5. Cada deploy executa `collectstatic` e `migrate`. Os usuários iniciais são criados uma única vez (se já existirem, nada muda).

## 3. Usuários iniciais

| Usuário | Cargo | Observação |
|---|---|---|
| `admin` | Admin (superusuário) | criado por `createsu`; exige `ADMIN_INITIAL_PASSWORD` |
| `gestor` | Gestor | criado por `create_roles` |
| `atendente` | Atendente | criado por `create_roles` |

**Troque essas senhas no primeiro acesso** e, se não forem mais necessárias, desative as contas de exemplo.

Comandos manuais (shell do Render ou local):
```bash
python manage.py createsu
python manage.py create_roles
python manage.py createsuperuser   # outro administrador
```

## 4. Rotinas de administração

### Criar um usuário
Usuários → **Adicionar** → usuário, e-mail (único), cargo, senha.

### Redefinir senha de alguém
Usuários → **Senha** → informe a nova senha e repasse por canal seguro; peça que a altere no próximo acesso.

### Promover ou rebaixar
Usuários → **Editar** → campo **Cargo**. Apenas você pode rebaixar.

### Desativar um funcionário que saiu
Usuários → **Desativar** (confirma na tela seguinte). Não use exclusão: o histórico precisa ser mantido.

### Gerenciar categorias e dados
Categorias pelo menu; dados brutos pelo `/admin/` (use com cuidado — alterações ali não geram movimentação de estoque).

## 5. Backup e recuperação

- Render PostgreSQL gratuito **expira em 30 dias**: exporte antes (`pg_dump "$DATABASE_URL" > backup.sql`) ou use plano pago com backups automáticos.
- Restaurar: `psql "$DATABASE_URL" < backup.sql`.
- Relatórios em Excel/CSV (Movimentações e Entregas) servem de cópia adicional dos históricos.
- Rollback de versão: Render → Deploys → *Rollback*.

## 6. Monitoramento e solução de problemas

| Sintoma | Causa provável / ação |
|---|---|
| `No module named 'app'` ao iniciar | Start Command padrão do Render; ajuste para `gunicorn farmacontrol.wsgi:application` |
| `SECRET_KEY não foi definida` | defina a variável de ambiente |
| Erro 400 *Bad Request* | host fora de `ALLOWED_HOSTS`; defina `ALLOWED_HOSTS` |
| Página sem CSS / erro 500 de static | `collectstatic` não rodou; confirme `bash build.sh` no build |
| `relation ... does not exist` | `migrate` não rodou; rode `python manage.py migrate` |
| Erro de conexão com o banco | confira `DATABASE_URL` (use a URL **interna**) e se o banco está ativo |
| Primeiro acesso lento | serviço gratuito dormindo; normal |
| Muitos redirecionamentos | `DEBUG=False` força HTTPS; acesse por `https://` |

Logs: painel do Render → **Logs**.

## 7. Atualização do sistema

```bash
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py test      # antes de publicar
```
No Render, o *push* na branch `main` dispara o deploy (se *auto-deploy* estiver ativo).

## 8. API de consulta

Os dados do sistema podem ser consultados em JSON (somente leitura) em `/api/`, com o mesmo login do site e o mesmo controle de acesso. Endpoints, parâmetros e exemplos estão em `API.md`. Para integrações automatizadas, use uma conta dedicada de Atendente (menor privilégio) e não compartilhe a senha de Gestor ou Admin.

## 9. Dados pessoais (LGPD)

As entregas registram o nome do paciente. Antes de uso real: defina a base legal e a finalidade do tratamento; restrinja o acesso a quem precisa (os perfis já separam permissões); defina por quanto tempo os registros serão mantidos; e proteja os *backups*. O sistema não anonimiza dados automaticamente nesta versão.

## 10. Boas práticas de segurança

- Mantenha `DEBUG=False` e `SECRET_KEY` secreta; nunca versionar `.env`.
- Use senhas fortes e troque as iniciais.
- Dê o cargo mínimo necessário (Atendente por padrão).
- Revise periodicamente a lista de usuários e desative contas inativas.
- Se uma credencial do banco vazar, gere outra e atualize `DATABASE_URL`.
- Mantenha as dependências atualizadas (`pip list --outdated`) e rode os testes antes de cada release.

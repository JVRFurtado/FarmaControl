#!/usr/bin/env bash
# Executado pelo Render a cada deploy (buildCommand).
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput

# Usuários iniciais: só são criados se as senhas estiverem definidas no
# ambiente (assim nenhuma senha aleatória vaza para os logs de build).
# Os comandos são idempotentes: não recriam quem já existe.
if [ -n "$ADMIN_INITIAL_PASSWORD" ]; then
  python manage.py createsu
fi
if [ -n "$GESTOR_INITIAL_PASSWORD" ] && [ -n "$ATENDENTE_INITIAL_PASSWORD" ]; then
  python manage.py create_roles
fi

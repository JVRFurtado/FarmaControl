import os
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# SECRET_KEY: obrigatório via variável de ambiente em produção.
# Em desenvolvimento local, usa uma chave fixa apenas para não travar o `runserver`
# (nunca faça deploy sem definir SECRET_KEY no ambiente).
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-only-chave-local-nao-usar-em-producao'
    else:
        raise RuntimeError(
            'SECRET_KEY não foi definida. Configure a variável de ambiente SECRET_KEY '
            '(no Render: Environment > Environment Variables) antes de rodar em produção.'
        )

# Hosts permitidos: definidos via variável de ambiente (separados por vírgula),
# com um padrão razoável para desenvolvimento e para o domínio conhecido no Render.
ALLOWED_HOSTS = os.environ.get(
    'ALLOWED_HOSTS',
    'farmcontrol.onrender.com,localhost,127.0.0.1'
).split(',')

# App de usuários customizado
AUTH_USER_MODEL = 'usuarios.Users'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'estoque',
    'usuarios',
    'rolepermissions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Para servir arquivos estáticos no Heroku
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'rolepermissions.middleware.RolePermissionsMiddleware',
]

ROOT_URLCONF = 'farmacontrol.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'farmacontrol'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.static',
            ],
        },
    },
]

WSGI_APPLICATION = 'farmacontrol.wsgi.application'

# Configuração do banco de dados:
# Usa a variável de ambiente DATABASE_URL (fornecida automaticamente pelo Render,
# conforme configurado em render.yaml). Em desenvolvimento local, se DATABASE_URL
# não estiver definida, cai para um SQLite local (db.sqlite3) para facilitar testes
# sem precisar de um Postgres rodando na máquina.
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=not DEBUG,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }




# Validação de senha
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Internacionalização
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# Arquivos estáticos
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # Diretório para collectstatic no Heroku
STATICFILES_DIRS = [BASE_DIR / 'estoque' / 'static']

# Config WhiteNoise para otimizar arquivos estáticos no Heroku
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Configurações de login
LOGIN_URL = '/usuarios/login/'
LOGIN_REDIRECT_URL = '/usuarios/dashboard/'
LOGOUT_REDIRECT_URL = '/usuarios/login/'

# Role permissions
ROLEPERMISSIONS_MODULE = 'usuarios.roles'

# Default auto field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

import logging
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.WARNING)


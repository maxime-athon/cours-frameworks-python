from pathlib import Path
from decouple import config
from datetime import timedelta

# --- Bloc 1 : Chemins de base ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Bloc 2 : Sécurité et accès ---
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost').split(',')

# --- Bloc 3 : Applications installées ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Applications
    'etudiants.apps.EtudiantsConfig',
    'auth_api',

    # DRF et extensions
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'drf_spectacular',
    'django_filters',
]
# --- Bloc 4 : Pile de middlewares ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # doit être avant SessionMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'kara_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'kara_backend.wsgi.application'

# --- Bloc 5 : Base de données ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',   # Dev
        'NAME': BASE_DIR / 'db.sqlite3',

        # Production PostgreSQL :
        # 'ENGINE': 'django.db.backends.postgresql',
        # 'NAME': config('DB_NAME'),
        # 'USER': config('DB_USER'),
        # 'PASSWORD': config('DB_PASSWORD'),
        # 'HOST': config('DB_HOST', default='localhost'),
        # 'PORT': config('DB_PORT', default='5432'),
    }
}

# --- Bloc 6 : Configuration CORS ---
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",   # React en dev
    "http://10.0.2.2:3000",    # Emulateur Android
]
CORS_ALLOW_ALL_ORIGINS = DEBUG  # True en dev uniquement

# --- Bloc 7 : Django REST Framework ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}

# --- Bloc 8 : Configuration JWT ---
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# --- Bloc 9 : Swagger, i18n, fichiers statiques ---
SPECTACULAR_SETTINGS = {
    'TITLE': 'Kara University API',
    'DESCRIPTION': 'API REST -- Gestion universitaire -- Module Django',
    'VERSION': '1.0.0',
}

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Lome'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# URL vers laquelle @login_required redirige si non connecté
LOGIN_URL = '/auth/connexion/'

# URL par défaut après connexion réussie (si pas de ?next=)
LOGIN_REDIRECT_URL = '/etudiants/'
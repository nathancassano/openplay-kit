# Initialize App Engine and import the default settings (DB backend, etc.).
# If you want to use a different backend you have to remove all occurences
# of "djangoappengine" from this file.
from djangoappengine.settings_base import *
from djangoappengine.utils import on_production_server, have_appserver

import os

DEBUG = not on_production_server
TEMPLATE_DEBUG = DEBUG

# Activate django-dbindexer for the default database
DATABASES['native'] = DATABASES['default']
DATABASES['default'] = {'ENGINE': 'dbindexer', 'TARGET': 'native'}
DATABASES['gae'] = { 'ENGINE': 'djangoappengine.db'}

AUTOLOAD_SITECONF = 'indexes'

SECRET_KEY = ''

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'djangotoolbox',
    'autoload',
    'dbindexer',
    'permission_backend_nonrel',
    # djangoappengine should come last, so it can override a few manage.py commands
    'djangoappengine',
    'openplaykit'
)

MIDDLEWARE_CLASSES = (
    # This loads the index definitions, so it has to come first
    'autoload.middleware.AutoloadMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware'
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.request',
    'django.core.context_processors.media',
    'django.contrib.messages.context_processors.messages',
)

AUTHENTICATION_BACKENDS = (
    'permission_backend_nonrel.backends.NonrelPermissionBackend',
)

# This test runner captures stdout and associates tracebacks with their
# corresponding output. Helps a lot with print-debugging.
TEST_RUNNER = 'djangotoolbox.test.CapturingTestSuiteRunner'

TEMPLATE_DIRS = (os.path.join(os.path.dirname(__file__), 'templates'),)

STATIC_URL = '/media/'

ROOT_URLCONF = 'urls'

EMAIL_BACKEND = 'djangoappengine.mail.AsyncEmailBackend'

ALLOWED_HOSTS=['.appspot.com']

GOOGLE_PUBLIC_KEY=''

SECRET_KEY = "x"
DEBUG = False
ALLOWED_HOSTS = ["api.example.com"]
INSTALLED_APPS = ["django.contrib.contenttypes", "django.contrib.auth", "rest_framework", "orders"]
DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql", "NAME": "shop", "HOST": "db"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True

from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.models import AbstractUser as DjangoAbstractUser


USER_LANGUAGES_ENABLED = getattr(settings, 'USER_LANGUAGES_ENABLED', False)
LANGUAGES_EN = getattr(settings, 'LANGUAGES_EN', 'en')
LANGUAGES_RU = getattr(settings, 'LANGUAGES_RU', 'ru')
LANGUAGES = getattr(settings, 'LANGUAGES', (
    (LANGUAGES_EN, _('English')),
    (LANGUAGES_RU, _('Russian')),
))
AVAILABLE_LANGUAGES = [key for key, value in LANGUAGES]
LANGUAGES_LOCALE_MAP = getattr(settings, 'LANGUAGE_LOCALE_MAP', {
    LANGUAGES_EN: 'en-us',
    LANGUAGES_RU: 'ru-ru',
})


class UserManager(BaseUserManager):
    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class AbstractUser(DjangoAbstractUser):
    class Meta:
        abstract = True

    username = None
    username_validator = None
    email = models.EmailField(_('email address'), unique=True)

    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []


class User(AbstractUser):
    if USER_LANGUAGES_ENABLED:
        language = models.CharField(_('Interface language'), max_length=2, choices=LANGUAGES,
                                    default=LANGUAGES_EN)

        @property
        def locale(self):
            try:
                return LANGUAGES_LOCALE_MAP[self.language]
            except KeyError:
                return 'en-us'

        @staticmethod
        def is_language_supported(lang):
            return lang in AVAILABLE_LANGUAGES
    else:
        pass

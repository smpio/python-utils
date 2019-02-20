import itertools

from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import USER_LANGUAGES_ENABLED


class UserAdmin(DjangoUserAdmin):
    if USER_LANGUAGES_ENABLED:
        list_display = DjangoUserAdmin.list_display + ('language',)
        list_filter = DjangoUserAdmin.list_filter + ('language',)
        fieldsets = DjangoUserAdmin.fieldsets + ((_('Preferences'), {'fields': ('language',)}),)


for fs_name, fs_options in itertools.chain(UserAdmin.fieldsets, UserAdmin.add_fieldsets):
    fs_options['fields'] = [('email' if f == 'username' else f) for f in fs_options['fields'] if f != 'email']

for list_name in ('list_display', 'list_filter', 'search_fields', 'ordering'):
    lst = getattr(UserAdmin, list_name)
    lst = [f for f in lst if f != 'username']
    setattr(UserAdmin, list_name, lst)

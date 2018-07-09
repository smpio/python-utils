from __future__ import print_function, division, absolute_import, unicode_literals
from django.db import models


class EnumField(models.SmallIntegerField):
    """
    Used to make enum-choices in fields filterable by "in" lookup_type using their names, not values.
    Special class required to determine obviously when filter by name required
    and make FilterSet simpler because it allows do predefine required filter_class
    """
    pass

import importlib
import itertools
import logging
from collections.abc import Iterable
import re
from typing import Optional

from django.conf import settings
from django.utils.functional import SimpleLazyObject


log = SimpleLazyObject(lambda: logging.getLogger(__name__))
_MASK = '********'
SENSITIVE_KEYS_DEFAULT = frozenset([
    'access_token',
    'api_key',
    'apikey',
    'auth',
    'authorization',
    'card_number',
    'cvv'
    'passwd',
    'password',
    'secret',
    'sentry_dsn',
    'token',
    'x-smp-jwt',
])
_SEPARATOR_BASE = '_'
_SEPARATOR_ALTERNATIVES = (' ', '-', )
_SENSITIVE_VALUES_RE = re.compile(r'^(?:\d[ -]*?){13,16}$')


def _get_sensitive_keys_base():
    sensitive_keys_custom = getattr(settings, 'SENTRY_SENSITIVE_KEYS', [])
    sensitive_keys_replace = getattr(settings, 'SENTRY_SENSITIVE_KEYS_REPLACE', False)
    if sensitive_keys_custom:
        if sensitive_keys_replace:
            sensitive_keys = sensitive_keys_custom
        else:
            sensitive_keys = itertools.chain(SENSITIVE_KEYS_DEFAULT, sensitive_keys_custom)
    else:
        sensitive_keys = SENSITIVE_KEYS_DEFAULT
    return sensitive_keys


def _iter_sensitive_keys_variants():
    for key in _get_sensitive_keys_base():
        key = key.lower()
        for separator_alternative in _SEPARATOR_ALTERNATIVES:
            key = key.replace(separator_alternative, _SEPARATOR_BASE)
        yield key
        if _SEPARATOR_BASE in key:
            for separator_alternative in _SEPARATOR_ALTERNATIVES:
                yield key.replace(_SEPARATOR_BASE, separator_alternative)


def _is_key_sensitive(key: str) -> bool:
    key = key.lower()
    return any(key in sensitive for sensitive in _iter_sensitive_keys_variants())


def _sanitize_recursive(data: any,
                        _regexp: Optional[re.Pattern] = _SENSITIVE_VALUES_RE):
    """
    :param data:     data to sanitize
    :param _regexp:  sensitive strings regexp
                     or None if all strings should considered as sensitive
    :return:         sanitized data
    """
    if not data:
        return
    if isinstance(data, dict):
        return {
            _sanitize_recursive(key): _sanitize_recursive(
                val, _regexp=None if _is_key_sensitive(key) else _SENSITIVE_VALUES_RE
            )
            for key, val in data.items()
        }
    if isinstance(data, str):
        if _regexp is None:
            # all strings considered as sensitive
            return _MASK
        elif isinstance(_regexp, re.Pattern):
            # only strings matching regex are sensitive
            if _regexp.match(data):
                return _MASK
            return data
        else:
            raise TypeError(f'regexp arg expected to be None or Pattern, got {type(_regexp).__name__}')
    if isinstance(data, Iterable):
        return list(map(_sanitize_recursive, data))
    return data


def sanitize_sensitive_data(event, hint):
    for key in ('extra', 'request', 'response'):
        if key in event:
            event[key] = _sanitize_recursive(event[key])
    return event


def before_send(event, hint):
    processors_resolved_attr = '__processors_resolved__'
    processors_resolved = getattr(before_send, processors_resolved_attr, None)
    if processors_resolved is None:
        # On first run

        # Check sensitive keys
        sensitive_keys = _get_sensitive_keys_base()
        if not isinstance(sensitive_keys, Iterable):
            log.warning(f'Sensitive keys should be Iterable, got {type(sensitive_keys).__name__}')
            return
        for key in sensitive_keys:
            if not isinstance(key, str):
                log.warning(f'Sensitive keys should be strings, got {type(key).__name__}')
                continue

        # Resolve strings into funcs
        processors_resolved = []
        for processor_path in settings.SENTRY_PROCESSORS_BEFORE_SEND:
            module_name, func_name = processor_path.rsplit('.', 1)
            processors_resolved.append(
                getattr(importlib.import_module(module_name), func_name))

        setattr(before_send, processors_resolved_attr, processors_resolved)

    for processor in processors_resolved:
        event = processor(event, hint)
    return event

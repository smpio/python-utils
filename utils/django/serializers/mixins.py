# TODO: class name is "writEable", but attribute is "writ_able" (both are valid English words)
class WriteableFieldsMixin:
    def get_extra_kwargs(self):
        extra_kwargs = super().get_extra_kwargs()

        all_fields = self.Meta.fields
        writable_fields = getattr(self.Meta, 'writable_fields', [])
        for field_name in all_fields:
            if field_name not in writable_fields:
                kwargs = extra_kwargs.get(field_name, {})
                kwargs['read_only'] = True
                extra_kwargs[field_name] = kwargs

        return extra_kwargs


class WriteOnceFieldsMixin:
    def _is_create(self):
        try:
            action = self.context.get('action') or self.context['view'].action
        except KeyError:
            # act most strictly if unknown
            action = None
        return action == 'create'

    def get_extra_kwargs(self):
        """
        NOTE: Meta.extra_kwargs won't affect declared fields
        """
        extra_kwargs = super().get_extra_kwargs()
        if not self._is_create():
            write_once_fields = getattr(self.Meta, 'write_once_fields', [])
            for field_name in write_once_fields:
                if field_name not in self._declared_fields:
                    kwargs = extra_kwargs.get(field_name, {})
                    kwargs['read_only'] = True
                    extra_kwargs[field_name] = kwargs
        return extra_kwargs

    def get_fields(self):
        """
        Handle declared fields which is not affected by Meta.extra_kwargs
        """
        fields = super().get_fields()
        if not self._is_create():
            write_once_fields = getattr(self.Meta, 'write_once_fields', [])
            for field_name in write_once_fields:
                if field_name in self._declared_fields:
                    fields[field_name].read_only = True
        return fields

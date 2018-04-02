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
    def get_extra_kwargs(self):
        extra_kwargs = super().get_extra_kwargs()

        if self.context['request'].view.action != 'create':
            write_once_fields = getattr(self.Meta, 'write_once_fields', [])
            for field_name in write_once_fields:
                kwargs = extra_kwargs.get(field_name, {})
                kwargs['read_only'] = True
                extra_kwargs[field_name] = kwargs

        return extra_kwargs

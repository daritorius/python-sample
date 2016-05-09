# -*- coding: utf-8 -*-
import importlib
import inspect
import logging

from django.conf import settings
from django.contrib import admin


class BaseModelAdmin(admin.ModelAdmin):
    actions = None
    force_exclude = None
    exclude = []
    base_logger = logging.getLogger('main')

    def __init__(self, *args, **kwargs):
        self.model = args[0]
        self.mapping = BaseModelMapping()
        field_list = self.mapping.base_fields[:]
        self.readonly_fields = field_list
        self.exclude = [] if not self.force_exclude else self.force_exclude
        self.list_display = ['id'] + list(self.list_display)
        super(BaseModelAdmin, self).__init__(*args, **kwargs)

    def save_formset(self, request, form, formset, change):
        self.base_logger.info(formset)
        return super(BaseModelAdmin, self).save_formset(request, form, formset, change)

    def save_model(self, request, obj, form, change):
        try:
            app_path = None
            for app in settings.INSTALLED_APPS:
                if '.' + inspect.getfile(obj.__class__).split('/')[-2] in app:
                    app_path = app
            model_name = obj.__class__.__name__
            factory_module = importlib.import_module(app_path + '.factories.' + model_name + 'Factory')
            factory = getattr(factory_module, model_name + 'Factory')()
        except Exception:
            import traceback
            self.base_logger.info(traceback.format_exc())
        return super(BaseModelAdmin, self).save_model(request, obj, form, change)

    def get_queryset(self, request):
        try:
            app_path = None
            for app in settings.INSTALLED_APPS:
                if '.' + inspect.getfile(self.model).split('/')[-2] in app and \
                                inspect.getfile(self.model).split('/')[-2] == app.split('.')[-1]:
                    app_path = app
            factory_module = importlib.import_module(app_path + '.factories.' + self.model.__name__ + 'Factory')
            factory = getattr(factory_module, self.model.__name__ + 'Factory')()
            return factory.select()
        except Exception:
            import traceback
            self.base_logger.info(traceback.format_exc())
            qs = super(BaseModelAdmin, self).get_queryset(request)
            return qs

    def queryset(self, request):
        try:
            app_path = None
            for app in settings.INSTALLED_APPS:
                if '.' + inspect.getfile(self.model).split('/')[-2] in app:
                    app_path = app
            factory_module = importlib.import_module(app_path + '.factories.' + self.model.__name__ + 'Factory')
            factory = getattr(factory_module, self.model.__name__ + 'Factory')()
            return factory.select()
        except Exception:
            import traceback
            self.base_logger.info(traceback.format_exc())
            qs = super(BaseModelAdmin, self).queryset(request)
            return qs

    def add_view(self, request, form_url='', extra_context=None):
        self.exclude = self.mapping.base_fields if not self.force_exclude else \
            self.mapping.base_fields + self.force_exclude
        if 'is_locked' not in self.exclude:
            # self.exclude += ['is_locked']
            self.exclude.append('is_locked')
        self.readonly_fields = []
        return super(BaseModelAdmin, self).add_view(request, form_url='', extra_context=None)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        field_list = self.mapping.base_fields[:]
        self.readonly_fields = field_list
        if self.readonly_fields is not None:
            if 'is_locked' not in self.readonly_fields:
                self.readonly_fields.append('is_locked')
        self.exclude = [] if not self.force_exclude else self.force_exclude
        return super(BaseModelAdmin, self).change_view(request, object_id, form_url='', extra_context=None)

    def delete_model(self, request, obj):
        obj.is_deleted = True
        obj.save()

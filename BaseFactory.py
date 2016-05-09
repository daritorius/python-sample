# -*- coding: utf-8 -*-
import hashlib
import logging
from django.core.cache import get_cache
from django.db import transaction
from django.db.models import Model, Q
from django.conf import settings
from django.utils.functional import SimpleLazyObject


class BaseFactory(object):
    __metaclass__ = Singleton
    model_class = None
    mapping = None
    cache = get_cache('test')
    base_logger = logging.getLogger('main')
    
    def create(self, item_data):
        assert isinstance(item_data, BaseModelMapping)
        item = self.model_class()
        for key, value in item_data.__dict__.items():
            setattr(item, key, value)
        item.save()
        service_create.send(sender=self.__class__, factory=self.__class__.__name__, id=int(item.id))
        self.remove_object_lock(item.id)
        return item

    def update(self, item_id, item_data):
        self.set_object_lock(item_id)
        assert isinstance(item_id, int)
        assert isinstance(item_data, BaseModelMapping)
        with transaction.atomic():
            item = self.model_class.objects.select_for_update().get(id=item_id)
            for key, value in item_data.__dict__.items():
                setattr(item, key, value)
            item.save(force_update=True)
        service_update.send(sender=self.__class__, factory=self.__class__.__name__, id=int(item.id))
        self.remove_object_lock(item_id)
        return item

    def delete(self, item_id):
        assert isinstance(item_id, int)
        item_data = self.mapping(is_deleted=True)
        item = self.update(int(item_id), item_data)
        service_delete.send(sender=self.__class__, factory=self.__class__.__name__, id=int(item.id))
        return item

    def get_by_id(self, obj_id, for_update=False):
        assert isinstance(obj_id, int)
        assert isinstance(for_update, bool)
        try:
            item = self.model_class.objects.get(id=obj_id) if not for_update \
                else self.model_class.objects.select_for_update().get(id=obj_id)
            return item
        except self.model_class.DoesNotExist:
            return None

    def get_all(self, order_by=None):
        if order_by:
            assert isinstance(order_by, basestring)
        items = self.model_class.objects.all()
        if order_by and len(items):
            items = items.order_by(order_by)
        return items

    @staticmethod
    def get_list_ids(items):
        return [item.id for item in items]

    def get_last(self, force=False, is_deleted=False, order_by=None, query=None, plain_data=None):
        items = self.select(force=force, is_deleted=is_deleted, order_by='-id', query=query, plain_data=plain_data)
        try:
            return items[0]
        except IndexError:
            return None

    def select(self, force=False, is_deleted=False, order_by=None, query=None, plain_data=None):
        assert isinstance(force, bool)
        assert isinstance(is_deleted, bool)
        if query:
            assert isinstance(query, Q)
        if order_by:
            assert isinstance(order_by, basestring)
        if plain_data:
            assert isinstance(plain_data, BaseModelMapping)
        kws = self._generate_kws(plain_data)
        items = self._make_select(query, is_deleted, kws, force, order_by)
        return items

    def _make_select(self, query, is_deleted, kws, force, order_by):
        assert isinstance(force, bool)
        assert isinstance(is_deleted, bool)
        assert isinstance(kws, dict)
        if query:
            assert isinstance(query, Q)
            items = self.model_class.objects.filter(query, is_deleted=is_deleted, **kws) if not force \
                else self.model_class.objects.filter(query, **kws)
        else:
            items = self.model_class.objects.filter(is_deleted=is_deleted, **kws) if not force \
                else self.model_class.objects.filter(**kws)
        if order_by and len(items):
            items = items.order_by(order_by)
        return items

    def get_item(self, force=False, is_deleted=False, query=None, plain_data=None, force_cache=False):
        assert isinstance(force, bool)
        assert isinstance(force_cache, bool)
        assert isinstance(is_deleted, bool)
        if query:
            assert isinstance(query, Q)
        if plain_data:
            assert isinstance(plain_data, BaseModelMapping)
        kws = self._generate_kws(plain_data)
        return item

    def _make_get(self, query, is_deleted, kws, force):
        assert isinstance(force, bool)
        assert isinstance(is_deleted, bool)
        assert isinstance(kws, dict)
        if query:
            assert isinstance(query, Q)
        item = None
        try:
            if query:
                item = self.model_class.objects.get(query, is_deleted=is_deleted, **kws) \
                    if not force else self.model_class.objects.get(query, **kws)
            else:
                item = self.model_class.objects.get(is_deleted=is_deleted, **kws) if not force else \
                    self.model_class.objects.get(**kws)
        except self.model_class.DoesNotExist:
            item = None
        finally:
            return item

    def _generate_kws(self, plain_data):
        kws = {}
        if plain_data:
            assert isinstance(plain_data, BaseModelMapping)
            for key, value in plain_data.__dict__.iteritems():
                if isinstance(value, SimpleLazyObject):
                    kws[key] = self.reload_simplelazyobject(value)
                else:
                    kws[key] = value
        return kws

    @staticmethod
    def _generate_name(name, query, plain_data):
        assert isinstance(name, basestring)
        if query:
            assert isinstance(query, basestring)
        if plain_data is not None:
            assert isinstance(plain_data, BaseModelMapping)
            for key, value in plain_data.__dict__.iteritems():
                if isinstance(value, Model) or isinstance(value, SimpleLazyObject):
                    value = value.id
                elif isinstance(value, unicode):
                    value = value.encode('utf8')
                elif isinstance(value, str):
                    value = value.decode('utf8')
                name += r'|%s=%s' % (key, value)
        if query is not None:
            name += r'|query=%s' % str(query)
        return hashlib.sha256(name).hexdigest()

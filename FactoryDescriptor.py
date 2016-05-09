# -*- coding: utf-8 -*-
from utils.main.base.exceptions.DescriptorException import DescriptorException
from django.utils.translation import ugettext_lazy as _


class FactoryDescriptor(object):

    def __init__(self, model_instance):
        self.model = model_instance

    def __call__(self, model_instance, *args, **kwargs):
        self.model = model_instance
        return self.model

    def __get__(self, instance, owner):
        return self.model

    def __set__(self, instance, value):
        raise DescriptorException(u"You can't set this attribute")

    def __delete__(self, instance):
        raise DescriptorException(u"You can't remove this attribute")

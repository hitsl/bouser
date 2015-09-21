#!/usr/bin/env python
# -*- coding: utf-8 -*-
from . import interfaces, service, exceptions, mixin, objects, rpc, user_login

__author__ = 'viruzzz-kun'
__created__ = '08.02.2015'


def make(config):
    return service.CastielService(config)

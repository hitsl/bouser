#!/usr/bin/env python
# -*- coding: utf-8 -*-
from . import request, service
from bouser.web import interfaces, request, service, cors, resource, session, site, useragents

__author__ = 'viruzzz-kun'
__created__ = '08.02.2015'


def make(config):
    return service.WebService(config)
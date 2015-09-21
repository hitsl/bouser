#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re

from twisted.application.service import MultiService

from bouser.helpers.plugin_helpers import BouserPlugin, Dependency
from bouser.web.cors import OptionsFinish

__author__ = 'viruzzz-kun'
__created__ = '04.04.2015'


re_referrer_origin = re.compile(u'(?P<origin>\Ahttps?://[\.\w\d\-]+(:\d+)?)/.*', (re.U | re.I))


class WebService(MultiService, BouserPlugin):
    signal_name = 'bouser.web'
    cas = Dependency('bouser.web')

    def __init__(self, config):
        MultiService.__init__(self)
        import os
        from bouser.utils import safe_traverse

        from twisted.internet import reactor
        from twisted.application import strports
        from bouser.web.resource import DefaultRootResource
        from bouser.web.site import BouserSite
        from bouser.proxied_logger import proxiedLogFormatter

        root_resource = DefaultRootResource()
        current_dir = os.path.dirname(__file__)
        site = BouserSite(
            root_resource,
            static_path=safe_traverse(config, 'static-path', default=os.path.join(current_dir, 'static')),
            template_path=safe_traverse(config, 'template-path', default=os.path.join(current_dir, 'templates')),
            logFormatter=proxiedLogFormatter)

        description = config.get('strport', 'tcp:%s:interface=%s' % (
            config.get('port', 5000),
            config.get('host', '127.0.0.1')
        ))

        self.cors_domain = config.get('cors-domain', 'http://127.0.0.1:5000/')
        allowed_domains = set(filter(None, config.get('allowed-domains', '').replace(',', ' ').split(' ')))
        self.allowed_domains = set(allowed_domains) | {self.cors_domain}

        service = strports.service(description, site, reactor=reactor)
        service.setServiceParent(self)

        self.root_resource = root_resource
        self.site = site
        self.service = service

    def crossdomain(self, request, allow_credentials=False):
        """
        :type request: bouser.web.request.BouserRequest
        :param request:
        :param allow_credentials:
        :return:
        """
        domain = self.cors_domain
        uri = request.getHeader('Referer')
        if uri:
            match = re_referrer_origin.match(uri)
            if match:
                candidate_domain = match.groupdict()['origin']
                if candidate_domain in self.allowed_domains:
                    domain = candidate_domain

        request.setHeader('Access-Control-Allow-Origin', domain)
        if allow_credentials:
            request.setHeader('Access-Control-Allow-Credentials', 'true')
        if request.method == 'OPTIONS' and request.requestHeaders.hasHeader('Access-Control-Request-Method'):
            # Preflight Request
            request.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            request.setHeader('Access-Control-Allow-Headers', 'Content-Type')
            request.setHeader('Access-Control-Max-Age', '600')
            raise OptionsFinish

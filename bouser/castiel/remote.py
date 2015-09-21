# -*- coding: utf-8 -*-
"""
Access Castiel remotely using CAS RPC API
"""

from twisted.internet import defer
from zope.interface import implementer
from bouser.castiel.interfaces import ICasService
from bouser.castiel.mixin import RequestAuthMixin

from bouser.helpers.api_helpers import get_json
from bouser.helpers.plugin_helpers import BouserPlugin
from bouser.utils import as_json
from bouser.castiel.exceptions import EInvalidCredentials, EExpiredToken
from bouser.castiel.objects import AuthTokenObject

__author__ = 'viruzzz-kun'


@implementer(ICasService)
class RemoteCas(RequestAuthMixin, BouserPlugin):
    signal_name = 'bouser.castiel'

    def __init__(self, config):
        self.cas_url = config.get('url', 'http://127.0.0.1/').rstrip('/') + '/cas/api/'
        self.cookie_name = config.get('cookie_name', 'authToken')

    def acquire_token(self, login, password):
        def _cb(j):
            if j['success']:
                return AuthTokenObject(j['user'], j['deadline'], j['token'])
            exception = j['exception']
            if exception == 'EInvalidCredentials':
                raise EInvalidCredentials
            raise Exception(j)

        return get_json(
            self.cas_url + 'acquire',
            json={'login': login, 'password': password}
        ).addCallback(_cb)

    def release_token(self, token):
        def _cb(j):
            if j['success']:
                return True
            return defer.fail(EExpiredToken(token))

        return get_json(
            self.cas_url + 'release',
            json={'token': token}
        ).addCallback(_cb)

    def check_token(self, token, prolong=False):
        def _cb(j):
            if j['success']:
                return j['user_id'], j['deadline']
            return defer.fail(EExpiredToken(token))

        send = {'token': token.encode('hex')}
        if prolong:
            send['prolong'] = True

        return get_json(
            self.cas_url + 'check', json=send
        ).addCallback(_cb)

    def prolong_token(self, token):
        def _cb(j):
            if j['success']:
                return True, j['deadline']
            return defer.fail(EExpiredToken(token))
        return get_json(
            self.cas_url + 'prolong',
            json={'token': token}
        ).addCallback(_cb)

    def get_user_id(self, token):
        def _cb(j):
            if j['success']:
                return j['user_id']
            return defer.fail(EExpiredToken(token))
        return get_json(
            self.cas_url + 'get_user_id',
            json={'token': token.encode('hex')}
        ).addCallback(_cb)


def make(config):
    return RemoteCas(config)

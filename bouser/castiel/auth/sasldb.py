#!/usr/bin/env python
# -*- coding: utf-8 -*-
import bsddb

from twisted.internet import defer
from twisted.python import failure
from zope.interface import implementer

from bouser.helpers.plugin_helpers import BouserPlugin
from bouser.castiel.exceptions import EInvalidCredentials
from bouser.castiel.interfaces import IAuthenticator, IAuthObject
from bouser.utils import safe_bytes

__author__ = 'viruzzz-kun'
__created__ = '13.09.2015'


@implementer(IAuthObject)
class SasldbAuthObject(object):
    __slots__ = ['user_id', 'login', 'groups']

    def __init__(self, login=None):
        self.user_id = login
        self.login = login
        self.groups = []

    def __getstate__(self):
        return [
            self.user_id,
            self.login,
            self.groups,
        ]

    def __setstate__(self, state):
        self.user_id, self.login, self.groups = state


@implementer(IAuthenticator)
class SasldbAuthenticator(BouserPlugin):
    signal_name = 'bouser.auth'

    def __init__(self, filename, realm):
        self.filename = filename
        self.realm = safe_bytes(realm)

    def get_user(self, login, password):
        pwd = safe_bytes(password)
        login = safe_bytes(login)
        db = bsddb.hashopen(self.filename, 'r')
        key = b'%s\x00%s\x00userPassword' % (login, self.realm)
        try:
            if db[key] != pwd:
                raise KeyError
            obj = SasldbAuthObject(login)
            return defer.succeed(obj)
        except (KeyError,):
            pass
        return defer.fail(failure.Failure(EInvalidCredentials()))


def make(config):
    return SasldbAuthenticator(config['passwd'], config.get('realm', 'localhost'))

# -*- coding: utf-8 -*-
import time
from UserDict import UserDict
import os

import msgpack
from twisted.python.components import registerAdapter
from twisted.application.service import Service
from twisted.internet import defer
from twisted.internet.task import LoopingCall
from twisted.web.static import Data

from zope.interface import implementer

from bouser.castiel.mixin import RequestAuthMixin
from bouser.castiel.rpc import CastielApiResource
from bouser.castiel.user_login import CastielLoginResource
from bouser.helpers.plugin_helpers import Dependency, BouserPlugin
from bouser.helpers import msgpack_helpers
from bouser.utils import safe_traverse
from bouser.web.resource import AutoRedirectResource
from .objects import AuthTokenObject
from .exceptions import EExpiredToken
from .interfaces import ICasService, IAuthenticator

__author__ = 'viruzzz-kun'


class CastielUserRegistry(UserDict, msgpack_helpers.Serializable):
    def __getstate__(self):
        return [
            (ato.token, ato.deadline, ato.object)
            for ato in self.data.itervalues()
        ]

    def __setstate__(self, state):
        self.data = dict(
            (token, AuthTokenObject(obj, deadline, token))
            for (token, deadline, obj) in state
        )


class TestResource(AutoRedirectResource):

    def render(self, request):
        """
        :type request: bouser.web.request.BouserRequest
        :param request:
        :return:
        """
        from twisted.internet import reactor
        d = defer.Deferred()
        result = request.render_template(
            'test.html',
            my_deferred=d
        )
        reactor.callLater(3, d.callback, 'YAYYAYAYYYYY!')
        return result


@implementer(ICasService)
class CastielService(Service, RequestAuthMixin, BouserPlugin):
    signal_name = 'bouser.castiel'
    root = Dependency('bouser')
    auth = Dependency('bouser.auth')
    web = Dependency('bouser.web')

    def __init__(self, config):
        self.clean_period = config.get('clean_period', 10)
        self.expiry_time = config.get('expiry_time', 3600)
        self.cookie_name = config.get('cookie_name', 'authToken')
        self.cookie_domain = config.get('cookie_domain', '127.0.0.1')
        self.domain_map = config.get('domain_map', {})

        cas_resource = self.cas_resource = AutoRedirectResource()

        cas_resource.putChild('api', CastielApiResource())
        cas_resource.putChild('login', CastielLoginResource())
        cas_resource.putChild('test', TestResource())
        cas_resource.putChild('', Data('I am Castiel, angel of God', 'text/html'))

        self.tokens = CastielUserRegistry()
        self.expired_cleaner = None

    def get_cookie_domain(self, source):
        return self.domain_map.get(source, self.cookie_domain)

    @web.on
    def web_boot(self, sender):
        """
        :type sender: bouser.web.service.WebService
        :param sender:
        :return:
        """
        sender.root_resource.putChild('cas', self.cas_resource)

    def acquire_token(self, login, password):
        def _cb(user):
            user_id = user.user_id
            ctime = time.time()

            token = os.urandom(16)

            deadline = ctime + self.expiry_time
            ato = self.tokens[token] = AuthTokenObject(user, deadline, token)  # (deadline, user_id)
            return ato

        d = self.auth.get_user(login, password)
        d.addCallback(_cb)
        return d

    def release_token(self, token):
        if token in self.tokens:
            ato = self.tokens[token]
            del self.tokens[token]
            return defer.succeed(True)
        return defer.fail(EExpiredToken(token))

    def check_token(self, token, prolong=False):
        if token not in self.tokens:
            return defer.fail(EExpiredToken(token))
        ato = self.tokens[token]
        if ato.deadline < time.time():
            return defer.fail(EExpiredToken(token))
        if prolong:
            self.prolong_token(token)
        return defer.succeed((ato.user_id, ato.deadline))

    def prolong_token(self, token):
        if token not in self.tokens:
            return defer.fail(EExpiredToken(token))
        deadline = time.time() + self.expiry_time
        ato = self.tokens[token]
        ato.deadline = deadline
        return defer.succeed((True, deadline))

    def is_valid_credentials(self, login, password):
        return self.auth.get_user(login, password)

    def _clean_expired(self):
        now = time.time()
        for token, ato in self.tokens.items():
            if ato.deadline < now:
                print "token", token.encode('hex'), "expired"
                del self.tokens[token]

    def get_user_id(self, token):
        """
        Returns users Auth Token Object
        :param token: Auth token
        :rtype: AuthTokenObject | None
        :return:
        """
        if token not in self.tokens:
            return defer.succeed(None)
        ato = self.tokens[token]
        if ato.deadline < time.time():
            return defer.succeed(None)
        return defer.succeed(ato.object.user_id)

    def startService(self):
        try:
            with open('tokens.msgpack', 'rb') as f:
                self.tokens = msgpack_helpers.load(f.read())
        except (IOError, OSError, msgpack.UnpackException, msgpack.UnpackValueError):
            pass
        self.expired_cleaner = LoopingCall(self._clean_expired)
        self.expired_cleaner.start(self.clean_period)
        Service.startService(self)

    def stopService(self):
        if self.expired_cleaner and self.expired_cleaner.running:
            self.expired_cleaner.stop()
        with open('tokens.msgpack', 'wb') as f:
            f.write(msgpack_helpers.dump(self.tokens))
        Service.stopService(self)


registerAdapter(CastielService, IAuthenticator, ICasService)
# -*- coding: utf-8 -*-
from twisted.internet import defer

__author__ = 'viruzzz-kun'


# noinspection PyUnresolvedReferences
class RequestAuthMixin(object):
    def request_get_user_id(self, request):
        """
        :type request: bouser.web.request.BouserRequest
        :param request:
        :rtype: int | NoneType
        :return: User_id associated with request
        """
        token_hex = request.getCookie(self.cookie_name)
        if not token_hex:
            return defer.succeed(None)
        token = token_hex.decode('hex')
        return self.get_user_id(token)

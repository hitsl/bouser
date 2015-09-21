# -*- coding: utf-8 -*-
from twisted.web import resource

__author__ = 'viruzzz-kun'


class DefaultRootResource(resource.Resource):
    def __init__(self):
        from twisted.web.static import Data
        resource.Resource.__init__(self)
        self.putChild('', Data(u"""
<!DOCTYPE html>
<html>
<head><style>body { color: #fff; background-color: #027eae; font-family: "Segoe UI", "Lucida Grande", "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 16px; }
a, a:visited, a:hover { color: #fff; }</style></head>
<body><h1>Bouser</h1><h2>Подсистема всякой ерунды</h2>Давайте придумаем более человеческое название...</body>
</html>""".encode('utf-8'), 'text/html; charset=utf-8'))


class AutoRedirectResource(resource.Resource):
    def render(self, request):
        """ Redirect to the resource with a trailing slash if it was omitted
        :type request: BouserRequest
        :param request:
        :return:
        """
        request.redirect(request.uri + '/')
        return ""
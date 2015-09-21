# -*- coding: utf-8 -*-
import jinja2
from twisted.web.server import Site
from twisted.web.static import File
from zope.interface import implementer
from bouser.helpers.plugin_helpers import BouserPlugin, Dependency
from bouser.web.interfaces import IBouserSite
from bouser.web.request import BouserRequest

__author__ = 'viruzzz-kun'


@implementer(IBouserSite)
class BouserSite(Site, BouserPlugin):
    requestFactory = BouserRequest

    cas = Dependency('bouser.castiel')

    def __init__(self, root_resource, *args, **kwargs):
        """
        :param castiel_service:
        :param static_path:
        :param template_path:
        """

        static_path = kwargs.pop('static_path', None)
        if static_path:
            root_resource.putChild('static', File(static_path))

        template_path = kwargs.pop('template_path', None)
        if template_path:
            self.__jinja_loader = jinja2.FileSystemLoader(template_path)
            self.jinja_env = jinja2.Environment(
                extensions=['jinja2.ext.with_'],
                loader=self.__jinja_loader,
            )

        Site.__init__(self, root_resource, *args, **kwargs)

    def add_loader_path(self, path):
        self.__jinja_loader.searchpath.append(path)

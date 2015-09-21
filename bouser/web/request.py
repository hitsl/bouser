#!/usr/bin/env python
# -*- coding: utf-8 -*-
from urllib import urlencode

from jinja2.exceptions import TemplateNotFound
from twisted.python.log import callWithContext
from zope.interface import implementer
from twisted.internet import defer
from twisted.python import reflect, log
from twisted.python.compat import intToBytes
from twisted.web import resource, html, http, error, microdom
from twisted.web.server import Request, NOT_DONE_YET, supportedMethods
from bouser.web.cors import OptionsFinish

from .interfaces import IBouserSite, IWebSession, ITemplatedRequest

__author__ = 'viruzzz-kun'
__created__ = '08.02.2015'


def error_page(request, resrc, value, tb=None):
    result = "Request: %s<br />\nResource: %s<br />\nValue: %s" % (
        html.PRE(reflect.safe_repr(request)),
        html.PRE(reflect.safe_repr(resrc)),
        html.PRE(reflect.safe_repr(value)),
    )
    if tb:
        result += '\n%s' % html.PRE(reflect.safe_str(tb))
    return result


@implementer(ITemplatedRequest)
class BouserRequest(Request):
    currentAppPath = '/'

    def render_template(self, name, **kwargs):
        if not IBouserSite.providedBy(self.site):
            raise RuntimeError('Site does not provide templating capabilities')
        session = self.getSession()
        fm = IWebSession(session)

        context = {
            'get_flashed_messages': fm.get_flashed_messages,
            'url_for': self.__url_for,
            'request': self,
        }
        context.update(kwargs)

        try:
            template = self.site.jinja_env.get_template(name)
            return template.render(context).encode('utf-8')
        except TemplateNotFound as e:
            print('Template not found filename="%s", name="%s"' % (e.filename, e.name))

    def rememberAppPath(self):
        self.currentAppPath = '/' + '/'.join(self.prepath)

    def __url_for(self, endpoint, **kwargs):
        result = '/'
        if endpoint == 'static':
            filename = kwargs.pop('filename')
            if not filename:
                raise RuntimeError('filename')
            result = '/static/%s' % filename
        elif endpoint == '.static':
            filename = kwargs.pop('filename')
            if not filename:
                raise RuntimeError('filename')
            result = '%s/%s' % (self.currentAppPath, filename)
        if kwargs:
            result = '%s?%s' % (result, urlencode(kwargs.iteritems()))
        return result

    @property
    def user_agent(self):
        if not hasattr(self, '__user_agent'):
            from bouser.web.useragents import UserAgent
            self.__user_agent = UserAgent(self.getHeader('User-Agent'))
        return self.__user_agent

    def get_content_type(self):
        content_type = self.requestHeaders.getRawHeaders('content-type', [])
        if content_type:
            return content_type[0].split(';', 1)[0].split('/')
        return None, None

    def getClientIP(self):
        if self.requestHeaders.hasHeader('x-forwarded-for'):
            return self.requestHeaders.getRawHeaders(b"x-forwarded-for")[0].split(b",")[0].strip()
        if self.requestHeaders.hasHeader('x-real-ip'):
            return self.requestHeaders.getRawHeaders(b"x-real-ip")[0].split(b",")[0].strip()
        return Request.getClientIP(self)

    # This allows us to use Deferred as return value from Resource.render(request)
    @defer.inlineCallbacks
    def render(self, resrc):
        """
        Ask a resource to render itself.

        @param resrc: a L{twisted.web.resource.IResource}.
        """
        try:
            body = yield defer.maybeDeferred(resrc.render, self)
        except OptionsFinish:
            self.write(b'')
            self.finish()
            return
        except error.UnsupportedMethod as e:
            allowedMethods = e.allowedMethods
            if (self.method == b"HEAD") and (b"GET" in allowedMethods):
                # We must support HEAD (RFC 2616, 5.1.1).  If the
                # resource doesn't, fake it by giving the resource
                # a 'GET' request and then return only the headers,
                # not the body.
                log.msg("Using GET to fake a HEAD request for %s" %
                        (resrc,))
                self.method = b"GET"
                self._inFakeHead = True
                body = resrc.render(self)

                if body is NOT_DONE_YET:
                    log.msg("Tried to fake a HEAD request for %s, but "
                            "it got away from me." % resrc)
                    # Oh well, I guess we won't include the content length.
                else:
                    self.setHeader(b'content-length', intToBytes(len(body)))

                self._inFakeHead = False
                self.method = b"HEAD"
                self.write(b'')
                self.finish()
                return

            if self.method in (supportedMethods):
                # We MUST include an Allow header
                # (RFC 2616, 10.4.6 and 14.7)
                self.setHeader('Allow', ', '.join(allowedMethods))
                s = ('''Your browser approached me (at %(URI)s) with'''
                     ''' the method "%(method)s".  I only allow'''
                     ''' the method%(plural)s %(allowed)s here.''' % {
                         'URI': microdom.escape(self.uri),
                         'method': self.method,
                         'plural': ((len(allowedMethods) > 1) and 's') or '',
                         'allowed': ', '.join(allowedMethods)
                     })
                epage = resource.ErrorPage(http.NOT_ALLOWED,
                                           "Method Not Allowed", s)
                body = epage.render(self)
            else:
                epage = resource.ErrorPage(
                    http.NOT_IMPLEMENTED, "Huh?",
                    "I don't know how to treat a %s request." %
                    (microdom.escape(self.method.decode("charmap")),))
                body = epage.render(self)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            callWithContext({'system': 'RequestError'}, traceback.print_exc)

            body = resource.ErrorPage(
                http.INTERNAL_SERVER_ERROR,
                "Request failed",
                error_page(self, resrc, e, tb)
            ).render(self)

        if body == NOT_DONE_YET:
            return
        if not isinstance(body, bytes):
            body = resource.ErrorPage(
                http.INTERNAL_SERVER_ERROR,
                "Request did not return bytes",
                error_page(self, resrc, body)
            ).render(self)

        if self.method == b"HEAD":
            if len(body) > 0:
                # This is a Bad Thing (RFC 2616, 9.4)
                log.msg("Warning: HEAD request %s for resource %s is"
                        " returning a message body."
                        "  I think I'll eat it."
                        % (self, resrc))
                self.setHeader(b'content-length',
                               intToBytes(len(body)))
            self.write(b'')
        else:
            self.setHeader(b'content-length',
                           intToBytes(len(body)))
            self.write(body)
        self.finish()

    def log(self):
        # Awkward
        self.site.log(self)

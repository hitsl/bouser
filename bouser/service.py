#!/usr/bin/env python
# -*- coding: utf-8 -*-
import cStringIO

import blinker
from twisted.python import log, filepath
from twisted.internet import inotify, reactor
from twisted.application.service import MultiService

from bouser.helpers.config_helpers import make_config

__author__ = 'viruzzz-kun'
__created__ = '04.04.2015'


boot = blinker.signal('bouser:boot')
check_deps = blinker.signal('bouser:check_dependencies')


def make_plugin(name, config):
    module = __import__(name, globals(), locals(), ['make'])
    if not hasattr(module, 'make'):
        log.msg('Module "%s" has no attribute "make"' % name)
        return None
    return module.make(config)


def pretty_print(d, indent=0):
    result = cStringIO.StringIO()
    if isinstance(d, (list, tuple)):
        for value in d:
            result.write(u'\n%s- %s' % ('    '*indent, pretty_print(value, indent+1)))
    elif isinstance(d, dict):
        for key, value in sorted(d.items()):
            result.write(u'\n%s%s: %s' % ('   '*indent, key, pretty_print(value, indent+1)))
    else:
        result.write(str(d))
    return result.getvalue()


class Application(MultiService):
    def __init__(self, options):
        MultiService.__init__(self)
        self.options = options
        self.config = {}
        self.modules = []
        self.fail = False

        notifier = inotify.INotify()
        notifier.startReading()
        notifier.watch(
            filepath.FilePath(self.options['config']),
            callbacks=[self._inotify_reload]
        )

    def reload_config(self):
        config = self.config = make_config(self.options['config'])
        log.msg(pretty_print(config))
        self.modules = []
        for name, cfg in config.get('module', {}).iteritems():
            log.msg(name, system='Loading')
            self.modules.append(make_plugin(name, cfg))

    def startService(self):
        log.msg('...Booting...', system="Bouser")
        self.reload_config()
        log.callWithContext({"system": "Bootstrap"}, boot.send, self)
        log.callWithContext({"system": "Checking Dependencies"}, check_deps.send, self)
        if self.fail:
            raise RuntimeError('Not all dependencies satisfied')
        else:
            MultiService.startService(self)

    def _inotify_reload(self, _, filepath, mask):
        log.msg('%s occured on %s' % (', '.join(inotify.humanReadableMask(mask)), filepath))
        self.restartService()

    def restartService(self):
        log.msg('...Reloading service...', system="Bouser")
        self.stopService().addCallback(lambda x: self.startService())

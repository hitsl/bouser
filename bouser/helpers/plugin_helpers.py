# -*- coding: utf-8 -*-
import blinker
from twisted.python import log

__author__ = 'viruzzz-kun'


def connect_to_signal(*names):
    def decorator(func):
        if not hasattr(func, '_connect_to_signals'):
            func._connect_to_signals = []
        func._connect_to_signals.extend(names)
        return func
    return decorator


class BouserPlugin(object):
    signal_name = None

    def __new__(cls, *args, **kwargs):
        obj = super(BouserPlugin, cls).__new__(cls)
        for name in dir(cls):
            item = getattr(obj, name)
            if hasattr(item, '_connect_to_signals'):
                for signal in item._connect_to_signals:
                    blinker.signal(signal).connect(item)
        blinker.signal('bouser:boot').connect(obj._fob)
        return obj

    def _fob(self, root):
        if hasattr(self, 'setServiceParent'):
            self.setServiceParent(root)
        name = getattr(self, 'name', None) or self.__class__.__name__
        if self.signal_name:
            msg = "%s (%s)" % (name, self.signal_name)
        else:
            msg = "%s" % (name,)
        log.msg(msg, system="Bootstrap")
        if self.signal_name:
            blinker.signal(self.signal_name + ':boot').send(self)


class Dependency(object):
    __instances = {}

    def __new__(cls, signal_name, optional=False):
        if signal_name not in Dependency.__instances:
            obj = Dependency.__instances[signal_name] = super(Dependency, cls).__new__(cls)

            obj.signal_name = signal_name
            obj.optional = optional
            obj.dependency = None
            obj.hooks = []

            blinker.signal('bouser:check_dependencies').connect(obj.__check_deps)
            blinker.signal(signal_name + ':boot').connect(obj.__attach_dependency)
        else:
            obj = Dependency.__instances[signal_name]
            obj.optional = obj.optional and optional
        return obj

    def __init__(self, *args, **kwargs):
        pass

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return self.dependency

    def __attach_dependency(self, sender):
        self.dependency = sender

    def __check_deps(self, root):
        if self.dependency is None:
            if self.optional:
                log.msg('Optional dependency "%s" not satisfied' % self.signal_name, system="Bouser warning")
            else:
                log.msg('Required dependency "%s" not satisfied' % self.signal_name, system="Bouser error")
                root.fail = True

    def on(self, func):
        if not hasattr(func, '_connect_to_signals'):
            func._connect_to_signals = []
        func._connect_to_signals.append(self.signal_name + ':boot')
        return func

    @classmethod
    def destroy_all(cls):
        cls.__instances = {}

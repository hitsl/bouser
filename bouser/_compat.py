# -*- coding: utf-8 -*-
import functools
import types
from twisted.internet import defer

__author__ = 'viruzzz-kun'


try:
    import stackless
except ImportError:
    stackless = None


class ReturnValue(object):
    def __init__(self, value):
        self.value = value


if stackless:
    def block_on(deferred):
        def _cb(r):
            ch.send(r)
            return r
        ch = stackless.channel()
        deferred.addBoth(_cb)
        return ch.receive()

    def deferred_tasklet(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            d = defer.Deferred()

            def tasklet(*args, **kwargs):
                try:
                    d.callback(func(*args, **kwargs))
                except:
                    d.errback()
            stackless.tasklet(tasklet)(*args, **kwargs).run()
            return d
        return wrapper

    def inline_callbacks_tasklet(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            d = defer.Deferred()

            def tasklet():
                try:
                    iterator = func(*args, **kwargs)
                except:
                    d.errback()
                else:
                    if not isinstance(iterator, types.GeneratorType):
                        d.callback(iterator)
                        return
                    while 1:
                        try:
                            val = iterator.next()
                        except StopIteration:
                            d.callback(val)
                        except ReturnValue, e:
                            d.callback(e.value)
                        except Exception as e:
                            val.throw(e)

    defer.Deferred.__unicode__ = block_on

else:
    def block_on(deferred):
        yield deferred

    deferred_tasklet = defer.inlineCallbacks
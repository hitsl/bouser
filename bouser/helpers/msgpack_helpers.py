#!/usr/bin/env python
# -*- coding: utf-8 -*-
import msgpack

__author__ = 'viruzzz-kun'
__created__ = '05.04.2015'


class Serializable(object):
    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__ = state


def __encode_hook(obj):
    if isinstance(obj, set):
        return msgpack.ExtType(0, dump(sorted(obj)))
    elif isinstance(obj, Serializable):
        return msgpack.ExtType(
            1,
            dump([
                obj.__module__,
                obj.__class__.__name__,
                obj.__getstate__(),
            ]))
    elif hasattr(obj, '__dict__'):
        return msgpack.ExtType(
            2,
            dump([
                obj.__module__,
                obj.__class__.__name__,
                obj.__dict__,
            ]))
    elif hasattr(obj, '__slots__'):
        return msgpack.ExtType(
            3,
            dump([
                obj.__module__,
                obj.__class__.__name__,
                [getattr(obj, key) for key in obj.__slots__],
            ]))
    return obj


def __ext_hook(code, data):
    if code == 0:
        return set(load(data))
    elif code in (1, 2, 3):
        mod, klass, state = load(data)
        module = __import__(mod, globals(), locals(), [klass])
        obj = getattr(module, klass)()
        if code == 1:
            obj.__setstate__(state)
        elif code == 2:
            obj.__dict__ = state
        elif code == 3:
            for key, value in zip(obj.__slots__, state):
                setattr(obj, key, value)
        return obj
    return msgpack.ExtType(code, data)


def load(chunk, **kwargs):
    return msgpack.unpackb(chunk, ext_hook=__ext_hook, encoding='utf-8', **kwargs)


def dump(o):
    return msgpack.packb(o, default=__encode_hook, use_bin_type=True)

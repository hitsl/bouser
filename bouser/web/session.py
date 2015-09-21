# -*- coding: utf-8 -*-
from twisted.python import components
from twisted.python.components import Componentized, registerAdapter
from twisted.web.server import Session
from zope.interface import implementer
from bouser.web.interfaces import IWebSession

__author__ = 'viruzzz-kun'


@implementer(IWebSession)
class WebSession(components.Componentized):
    def __init__(self, session):
        Componentized.__init__(self)
        self.session = session
        self.flashed_messages = []
        self.back = None

    def get_flashed_messages(self):
        messages, self.flashed_messages = self.flashed_messages, []
        return messages

    def flash_message(self, message):
        self.flashed_messages.append(message)

registerAdapter(WebSession, Session, IWebSession)


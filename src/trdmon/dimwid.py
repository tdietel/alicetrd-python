#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dimwid
"""

import urwid
import pydim
# import trdbox
import logging
import os
import struct
# from pprint import pprint
# import functools
import asyncio


palette = [
    ('state', 'light green', 'black'),

    ('fsm:off',     'dark gray',  'black'),
    ('fsm:static',  'light blue', 'black'),
    ('fsm:ready',   'light green', 'black'),
    ('fsm:trans',   'yellow',     'black'),
    ('fsm:error',   'white',      'light red'),

    ('bg', 'light gray', 'black'),
    ('foo', 'light red', 'black'),
]

urwid_event_loop=urwid.AsyncioEventLoop()
asyncio_event_loop = asyncio.get_event_loop()

def run(top_widget, palette=palette):

    loop = urwid.MainLoop(top_widget, palette, event_loop=urwid_event_loop, 
        unhandled_input=exit_on_enter)

    loop.run()

def call(func):
    def wrapper(*args, **kwargs):
        asyncio_event_loop.call_soon(func, *args, **kwargs)
    return wrapper


def exit_on_enter(key):
    if key=='enter' or key=='q':
        raise urwid.ExitMainLoop()

# def subs(svcname, default_value, timeout=60): #, svcdesc, timeout=60):
#     """Decorate callback function for DIM service."""

#     logging.debug("Getting event loop")
#     print("Getting event loop")
#     evloop = asyncio.get_event_loop()


#     def wrapper(func):

#         # The decorator that will actually decorate the function
#         def decorator():

#             # Define the function that will wrap the decorator during normal 
#             # running.
#             def dim_callback(*args):
#                 # Instead of calling the function, we ask asyncio to call it
#                 evloop.call_soon(func, *args)


#             logging.debug("Subscribe to DIM service")
#             print("Subscribe to DIM service")
#             pydim.dic_info_service(svcname, dim_callback, timeout=timeout, 
#                 default_value=default_value)

#             return dim_callback
#         return decorator
#     return wrapper


# pipefd = None
# callbacks = dict()
# def notify_urwid(func):

#     # Make sure the ID is in the callbacks dict so the nofication handler
#     # knows how to call it
#     if id(func) not in callbacks:
#         callbacks[id(func)] = func
    
#     # Send the ID of the callback func via the Urwid event loop to the 
#     # notification_handler function
#     if pipefd is not None:
#         os.write(pipefd, struct.pack("Q", id(func)))

# def notification_handler(data_from_pipe):
#     for cbid in struct.unpack("Q", data_from_pipe):   
#         callbacks[cbid]()
#         # for c in callbacks[id]:
#         #     c()



#     def receive_output(self, x):
#         for id in struct.iter_unpack("Q", x):
#             self.callbacks[id[0]].refresh()

#     def connect_loop(self, loop):
#         self.pipefd = loop.watch_pipe(self.receive_output)

# def start(top_widget, palette):
#     nonlocal pipefd
#     loop = urwid.MainLoop(top_widget, palette, unhandled_input=exit_on_enter)
#     pipefd = loop.watch_pipe(notification_handler)
#     # pipefd = loop.watch_pipe(self.receive_output)
#     # dimwid.connect_loop(loop)

#     loop.run()

# class subscribe:
#     def __init__(self, svc, desc, timeout):
#         self.service = flag
#     def __call__(self, original_func):
#         decorator_self = self
#         def wrappee( *args, **kwargs):
#             print 'in decorator before wrapee with flag ',decorator_self.flag
#             original_func(*args,**kwargs)
#             print 'in decorator after wrapee with flag ',decorator_self.flag
#         return wrappee


# def classmagic(c):

#     def wrapper(*args, **kwargs):
#         o = c(*args, **kwargs)
#         # logging.debug(dir(c))
#         for m in dir(c):
#             # logging.debug(f"check: {m}")
#             m = getattr(o,m)

#             if callable(m) and hasattr(m,"_dim_service_name"):
#                 logging.debug(repr(m))
#                 svcname = m._dim_service_name
#             else:
#                 continue

#             # # if hasattr(m, "_dim_service_timeout"):
#             # #     timeout = m._dim_service_timeout
#             # # else:
#             # #     timeout = 60


#             logging.debug(f"subscribe: {m} -> {svcname}")
#             pydim.dic_info_service(svcname, m)
#         return o

#     return wrapper

# def subscribe(svcname): #, svcdesc, timeout=60):
#     """Decorate callback function for DIM service.
    
#     This decorator takes the name and description, and an optional timeout
#     argument and subscribes to this DIM service. The decorated function is 
#     used as the callback function for the subscription, and after the 
#     callback executes, Urwid is notified that the class might need to be 
#     refreshed."""

#     # The decorator that will actually decorate the function
#     def decorator(func):

#         # wrapper._dim_service_name = svcname
#         # func._dim_service_name = svcname

#         # Define the function that will wrap the decorator during normal 
#         # running.
#         def wrapper(*args):

#             # logging.debug(repr(func))
#             # logging.debug(*args)

#             # First, we let the callback function handle all the arguments.
#             # func(func, *args)

#             # Then we notify Urwid via a pipe to it's mainloop that this
#             # instance needs to be updated
#             if pipefd is not None:
#                 os.write(pipefd, struct.pack("Q", id(func.__self__)))

#         wrapper._dim_service_name = svcname

#         # pydim.dic_info_service(svcname, svcdesc, wrapper, timeout=timeout)
#         return wrapper
#     return decorator

# def notify(func):
#     """Decorator to register this functions for Urwid callbacks."""

#     # This is an unusual decorator: we just need to register this method
#     # for callbacks, and it's not necessary to modify the behaviour of
#     # the function itself.

#     # First we figure out the ID of the instance that this method belongs
#     # to, and then we ensure that it's in the callbacks dict.
#     # key = id(func.__self__)
#     # if key not in callbacks:
#     #     callbacks[key] = list((func))
#     # else:
#     #     callbacks[key].append(func)

#     func._dim_notify

#     # We do not need to modify the function, so we can just return it.
#     return func


# class dimwid_t:

#     def __init__(self):
#         self.callbacks = dict()
#         self.pipefd = None

#     def register_callback(self, cb):
#         self.callbacks[id(cb)] = cb
#         # print(self.callbacks.keys())
#         # logger.debug(f"registering {id(cb)}")

#     def request_callback(self, cb):
#         if self.pipefd is not None:
#             os.write(self.pipefd, struct.pack("Q", id(cb)))

#     def receive_output(self, x):
#         for id in struct.iter_unpack("Q", x):
#             self.callbacks[id[0]].refresh()

#     def connect_loop(self, loop):
#         self.pipefd = loop.watch_pipe(self.receive_output)

# dimwid = dimwid_t()

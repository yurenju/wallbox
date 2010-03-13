#!/usr/bin/env python

import pygtk
pygtk.require ("2.0")
import gtk
import defs
import logging
import pickle
import os
import facebook
import gettext, locale

logging.basicConfig (level=defs.log_level)
cache_attributes = \
    ["current_status", "notification", "status", \
    "user_ids", "users", "app_ids", "applications"]

def gettext_init ():
    locale_dir = os.path.abspath(os.path.join(defs.DATA_DIR, "locale"))
    for module in (gettext, locale):
        module.bindtextdomain('wallbox', locale_dir)
        module.textdomain('wallbox')

        if hasattr(module, 'bind_textdomain_codeset'):
            module.bind_textdomain_codeset('wallbox','UTF-8')
    return gettext.gettext

def set_scollbar_height (window, treeview, scrollbar):
    (width, height) = window.get_size ()
    (x, y) = window.get_position ()
    treeview_height = treeview.size_request ()[1]
    if height + y > gtk.gdk.screen_height ():
        target_height = gtk.gdk.screen_height () - (height+y-treeview_height) - 20
        treeview.set_size_request (-1, target_height)
        logging.info ("notification height: %d" % target_height)
    else:
        scrollbar.set_size_request (-1, treeview_height)
        logging.info ("notification height: %d" % treeview_height)

def pickle_load (path):
    logging.debug ("pickle_load path: %s" % path)
    cache = None
    if os.path.exists (path):
        f = open (path, 'r')
        try:
            cache = pickle.load (f)
        except:
            logging.debug ("load cache pickle failed")
            return
        f.close ()
        return cache
    else:
        logging.debug ("cache.pickle not found")

    return None

def save_auth_status (path, session):
    auth = {}
    auth["session_key"] = session['session_key']
    auth["secret"] = session['secret']
    output = open (path, 'wb')
    pickle.dump (auth, output)
    output.close ()

def restore_auth_status (path, api_key, secret):
    if os.path.exists (path):
        f = open (path, 'r')
        try:
            auth = pickle.load (f)
        except:
            f.close ()
            logging.debug ("pickle load failed")
            return False

        f.close ()
        fb = facebook.Facebook (api_key, secret)
        fb.session_key = auth["session_key"]
        fb.uid = auth["session_key"].split('-')[1]
        fb.secret = auth["secret"]
        return fb
    else:
        "pickle auth not exist"
        return None

def pickle_dump (post_office, path):
    cache = {}
    for attr_str in cache_attributes:
        attr = getattr (post_office, attr_str)
        cache[attr_str] = attr
    output = open (path, 'wb')
    pickle.dump (cache, output)
    output.close ()

def get_min_monitor_height ():
    min_height = 4096
    screen = gtk.gdk.screen_get_default ()
    monitor_num = screen.get_n_monitors ()
    for i in range (monitor_num):
        rect = screen.get_monitor_geometry (i)
        if rect.height < min_height:
            min_height = rect.height

    return min_height

def suggest_window_position (window, x, y):
    xs = x
    ys = y
    screen = gtk.gdk.screen_get_default ()
    mon_num = screen.get_monitor_at_point (x, y)
    monitor_rect = screen.get_monitor_geometry (mon_num)
    x_left = monitor_rect.x
    x_right = monitor_rect.x + monitor_rect.width
    y_top = monitor_rect.y
    y_bottom = monitor_rect.y + monitor_rect.height
    win_rect = window.get_allocation ()

    if x + win_rect.width >= x_right:
        xs = x_right - win_rect.width
    if x + win_rect.width <= x_left:
        xs = x_left
    if y + win_rect.height >= y_bottom:
        ys = y_bottom - win_rect.height
    if y + win_rect.height <= y_top:
        ys = y_top

    if ys > (y_bottom + y_top) / 2:
        ys += 20
    else:
        ys -= 20
    return (xs, ys)
    

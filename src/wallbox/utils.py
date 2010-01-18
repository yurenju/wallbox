#!/usr/bin/env python

import pygtk
pygtk.require ("2.0")
import gtk
import defs
import logging
import pickle
import os
import facebook
import htmllib

logging.basicConfig (level=defs.log_level)
cache_attributes = \
    ["current_status", "notification", "status", \
    "user_ids", "users", "app_ids", "applications"]

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

def unescape (s):
    try:
        p = htmllib.HTMLParser (None)
        p.save_bgn ()
        p.feed (s)
        return p.save_end ()
    except:
        return p

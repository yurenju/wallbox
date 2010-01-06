#!/usr/bin/env python

import pygtk
pygtk.require ("2.0")
import gtk
import defs
import logging

logging.basicConfig (level=defs.log_level)

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

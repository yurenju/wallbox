#!/usr/bin/env python

import pygtk
pygtk.require ("2.0")
import gtk
import dbus
import dbus.mainloop.glib
import sys
import pango
import defs
import logging
import utils
import gobject
import cgi

COMMENT_ICON_SIZE = 30
MAIN_ICON_SIZE = 50
TEXT_CELL_WIDTH = 200
STATUS_WIDTH = \
    TEXT_CELL_WIDTH + COMMENT_ICON_SIZE - MAIN_ICON_SIZE

class Comment:
    def __init__ (self, post_id):
        logging.basicConfig (level=defs.log_level)
        self.post_id = post_id
        self.builder = gtk.Builder ()

        ui_file =  "%s/comment.ui" % defs.WALLBOX_DATA_DIR

        self.builder.add_from_file (ui_file)
        self.builder.connect_signals (self, None)
        self.window = self.builder.get_object ("comment_window")

        self.entry_comment = self.builder.get_object ("entry_comment")
        self.entry_comment.grab_focus ()

        bus = dbus.SessionBus ()
        obj = bus.get_object ("org.wallbox.PostOfficeService", \
            "/org/wallbox/PostOfficeObject")

        self.office = dbus.Interface \
            (obj, "org.wallbox.PostOfficeInterface")

        liststore = self.builder.get_object ("liststore_comment")
        clist = self.office.get_comments_list (post_id)
        for id in clist:
            comment = self.office.get_comment_entry (post_id, id)
            logging.info ("comment text: %s" % comment['text'])
            liststore.append \
                ([cgi.escape (comment['text']), int (comment['time']), \
                str (comment['fromid'])])

        self.status = self.office.get_status (post_id)
        label_status = self.builder.get_object ("label_status")
        label_status.set_text (self.status['message'])
        label_status.set_size_request (STATUS_WIDTH, -1)

        user = self.office.get_user (self.status['source_id'])
        main_user_icon = self.builder.get_object ("main_pic")
        user_icons_dir = self.office.get_user_icons_dir ()

        if not user.has_key ("pic_square_local"):
            img_file = "%s/images/q_silhouette.gif" % defs.WALLBOX_DATA_DIR
        else:
            img_file = "%s/%s" % (user_icons_dir, user['pic_square_local'])

        main_user_icon.set_from_file (img_file)

        current_pic = self.builder.get_object ("current_user_pic")
        current_user = self.office.get_current_user ()
        if current_user.has_key ("pic_square_local"):
            icon_path = "%s/%s" % \
                (user_icons_dir, current_user['pic_square_local'])
        else:
            icon_path =  "%s/images/q_silhouette.gif" % defs.WALLBOX_DATA_DIR
            
        pixbuf = None
        try:
            pixbuf = gtk.image_new_from_file (icon_path).get_pixbuf ()
        except:
            logging.debug ("no icon: comment.py:59 [%s]" % icon_path)
            img_file =  "%s/images/q_silhouette.gif" % defs.WALLBOX_DATA_DIR
            icon = gtk.image_new_from_file (img_file)
            pixbuf = icon.get_pixbuf ()
            
        scaled_buf = \
            pixbuf.scale_simple \
            (COMMENT_ICON_SIZE, COMMENT_ICON_SIZE, gtk.gdk.INTERP_BILINEAR)
        current_pic = current_pic.set_from_pixbuf (scaled_buf)
        self.user = user

        self.init_view ()

        utils.set_scollbar_height (self.window, self.treeview, self.builder.get_object ("scrolledwindow"))

    def delay_show_window (self):
        gobject.timeout_add (300, self.show_window)

    def show_window (self):
        if self.window.get_property ("visible") == False:
            logging.debug ("delay show window")
            self.window.show ()
        return False

    def on_button_share_clicked (self, button, data=None):
        entry = self.builder.get_object ("entry_comment")
        if entry != None and len (entry.get_text ()) > 0:
            self.office.post_comment (self.post_id, entry.get_text ())
            liststore = self.builder.get_object ("liststore_comment")
            liststore.append ([cgi.escape (entry.get_text()), 0, self.user['uid']])
            entry.set_text ("")

    def on_window_resize (self, widget, event, data=None):
        x = self.window.get_size ()[0]
        self.text_cell.set_property ("wrap-width", x - 50)

    def init_view (self):
        self.treeview = self.builder.get_object ("treeview_comment")
        self.column = gtk.TreeViewColumn ()
        self.treeview.append_column (self.column)
        self.icon_cell = gtk.CellRendererPixbuf ()
        self.text_cell = gtk.CellRendererText ()

        self.icon_cell.set_property ("yalign", 0.1)
        self.text_cell.set_property ("wrap-width", TEXT_CELL_WIDTH)
        self.text_cell.set_property ("wrap-mode", pango.WRAP_WORD_CHAR)
        self.text_cell.set_property ("yalign", 0.1)

        self.column.pack_start (self.icon_cell, False)
        self.column.pack_start (self.text_cell, True)

        self.column.set_cell_data_func (self.icon_cell, self.make_icon)
        self.column.set_cell_data_func (self.text_cell, self.make_text)

    def make_icon (self, column, cell, model, iter):
        icon = None
        uid = model.get_value (iter, 2)
        user = self.office.get_user (long (uid))
        icons_dir = self.office.get_user_icons_dir ()
        if user.has_key ('pic_square_local'):
            icon_path = "%s/%s" % (icons_dir, user['pic_square_local'])
            icon = gtk.image_new_from_file (icon_path)
        else:
            img_file =  "%s/images/q_silhouette.gif" % defs.WALLBOX_DATA_DIR
            icon = gtk.image_new_from_file (img_file)

        try:
            pixbuf = icon.get_pixbuf ()
        except:
            logging.debug ("no icon: comment.py:116 [%s]" % icon_path)
            img_file =  "%s/images/q_silhouette.gif" % defs.WALLBOX_DATA_DIR
            icon = gtk.image_new_from_file (img_file)
            pixbuf = icon.get_pixbuf ()

        scaled_buf = \
            pixbuf.scale_simple \
            (COMMENT_ICON_SIZE, COMMENT_ICON_SIZE, gtk.gdk.INTERP_BILINEAR)
        cell.set_property ('pixbuf', scaled_buf)

    def make_text (self, column, cell, model, iter):
        cell.set_property ('text', cgi.escape (model.get_value (iter, 0)))

if __name__ == "__main__":
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    c = Comment ('700771630_216520838688')
    gtk.main ()


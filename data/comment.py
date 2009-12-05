#!/usr/bin/env python

import pygtk
pygtk.require ("2.0")
import gtk
import dbus
import dbus.mainloop.glib
import sys

COMMENT_ICON_SIZE = 30
MAIN_ICON_SIZE = 50
TEXT_CELL_WIDTH = 200
STATUS_WIDTH = \
    TEXT_CELL_WIDTH - (MAIN_ICON_SIZE - COMMENT_ICON_SIZE)

class Comment:
    def __init__ (self, post_id):
        self.builder = gtk.Builder ()
        self.builder.add_from_file ("comment.glade")
        self.window = self.builder.get_object ("comment_window")
        #self.window.connect ("configure-event", self.on_window_resize)
        self.window.show ()

        bus = dbus.SessionBus ()
        obj = bus.get_object ("org.wallbox.PostOfficeService", \
            "/org/wallbox/PostOfficeObject")

        self.office = dbus.Interface \
            (obj, "org.wallbox.PostOfficeInterface")


        liststore = self.builder.get_object ("liststore_comment")
        clist = self.office.get_comments_list (post_id)
        for id in clist:
            comment = self.office.get_comment_entry (post_id, id)
            liststore.append \
                ([comment['text'], int (comment['time']), \
                str (comment['fromid'])])

        self.status = self.office.get_status (post_id)
        label_status = self.builder.get_object ("label_status")
        label_status.set_text (self.status['message'])
        label_status.set_size_request (STATUS_WIDTH, -1)

        user = self.office.get_user (self.status['uid'])
        main_user_icon = self.builder.get_object ("main_pic")
        user_icons_dir = self.office.get_user_icons_dir ()
        main_user_icon.set_from_file \
            ("%s/%s" % (user_icons_dir, user['pic_square_local']))

        current_pic = self.builder.get_object ("current_user_pic")
        pixbuf = gtk.image_new_from_file \
            ("%s/%s" % (user_icons_dir, user['pic_square_local'])).get_pixbuf ()
        scaled_buf = \
            pixbuf.scale_simple \
            (COMMENT_ICON_SIZE, COMMENT_ICON_SIZE, gtk.gdk.INTERP_BILINEAR)
        current_pic = current_pic.set_from_pixbuf (scaled_buf)

        self.init_view ()

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
            icon = gtk.image_new_from_file \
                ("%s/%s" % (icons_dir, user['pic_square_local']))
        else:
            icon = gtk.image_new_from_file ("images/q_silhouette.gif")

        pixbuf = icon.get_pixbuf ()
        scaled_buf = \
            pixbuf.scale_simple \
            (COMMENT_ICON_SIZE, COMMENT_ICON_SIZE, gtk.gdk.INTERP_BILINEAR)
        cell.set_property ('pixbuf', scaled_buf)

    def make_text (self, column, cell, model, iter):
        cell.set_property ('text', model.get_value (iter, 0))

if __name__ == "__main__":
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    c = Comment ('700771630_216520838688')
    gtk.main ()


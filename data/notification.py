#!/usr/bin/env python

import pygtk
pygtk.require ("2.0")
import gtk
import dbus
import dbus.mainloop.glib

class NotificationView:
    def __init__ (self):
        self.builder = gtk.Builder ()
        self.builder.add_from_file ("notification.glade")
        self.window = self.builder.get_object ("notification_window")
        self.window.show ()

        bus = dbus.SessionBus ()
        obj = bus.get_object ("org.wallbox.PostOfficeService", \
            "/org/wallbox/PostOfficeObject")

        self.office = dbus.Interface \
            (obj, "org.wallbox.PostOfficeInterface")

        self.init_view ()
        self.office.refresh (reply_handler=self.refresh_reply_cb, \
                            error_handler=self.refresh_error_cb)

    def init_view (self):
        self.treeview = self.builder.get_object ("treeview_notification")
        self.treeview.set_hover_selection (True)
        self.icon_column = gtk.TreeViewColumn ("icon")
        self.text_column = gtk.TreeViewColumn ("text")
        self.arrow_column = gtk.TreeViewColumn ("arrow")
        self.treeview.append_column (self.icon_column)
        self.treeview.append_column (self.text_column)
        self.treeview.append_column (self.arrow_column)
        self.icon_cell = gtk.CellRendererPixbuf ()
        self.text_cell = gtk.CellRendererText ()
        self.arrow_cell = gtk.CellRendererText ()

        self.icon_cell.set_property ("yalign", 0.0)
        self.text_cell.set_property ("wrap-width", 150)

        self.icon_column.pack_start (self.icon_cell, False)
        self.text_column.pack_start (self.text_cell, True)
        self.arrow_column.pack_start (self.arrow_cell, False)

        self.icon_column.set_cell_data_func (self.icon_cell, self.make_icon)
        self.text_column.set_attributes (self.text_cell, text=1)
        self.arrow_column.set_cell_data_func (self.arrow_cell, self.make_arrow)

    def make_icon (self, column, cell, model, iter):
        app_id = model.get_value (iter, 0)
        app = self.office.get_application (app_id)
        icons_dir = self.office.get_app_icons_dir ()
        icon = gtk.image_new_from_file ("%s/%s" % (icons_dir, app['icon_name']))
        cell.set_property ('pixbuf', icon.get_pixbuf())

    def make_arrow (self, column, cell, model, iter):
        has_detail = model.get_value (iter, 2)
        arrow = None
        if has_detail == True:
            arrow = ">>"
        cell.set_property ('text', arrow)

    def refresh_reply_cb (self):
        label = self.builder.get_object ("label_current_status")
        status = self.office.get_current_status ()
        label.set_text (status['message'])
        nlist = self.office.get_notification_list ()
        liststore = self.builder.get_object ("list_notification")
        for nid in nlist:
            entry = self.office.get_notification_entry (nid)
            text = None
            if len (entry['body_text']) == 0:
                text = entry['title_text']
            else:
                text = entry['body_text']
            liststore.append ([entry['app_id'], text, True])

    def refresh_error_cb (self, e):
        print e
        pass

if __name__ == "__main__":
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    n = NotificationView ()
    gtk.main ()


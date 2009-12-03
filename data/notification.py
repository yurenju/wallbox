#!/usr/bin/env python

import pygtk
pygtk.require ("2.0")
import gtk
import dbus
import dbus.mainloop.glib
import comment
import sys

class Notification:
    def __init__ (self):
        self.comment = None
        self.builder = gtk.Builder ()
        self.builder.add_from_file ("notification.glade")
        self.window = self.builder.get_object ("notification_window")
        self.window.connect ("configure-event", self.on_window_resize)
        self.window.show ()

        bus = dbus.SessionBus ()
        obj = bus.get_object ("org.wallbox.PostOfficeService", \
            "/org/wallbox/PostOfficeObject")

        self.office = dbus.Interface \
            (obj, "org.wallbox.PostOfficeInterface")

        self.init_view ()
        
        if len (sys.argv) > 1 and sys.argv[1].strip() == "offline":
            self.refresh_reply_cb ()
        else:
            self.office.refresh (reply_handler=self.refresh_reply_cb, \
                error_handler=self.refresh_error_cb)

    def on_window_resize (self, widget, event, data=None):
        x = self.window.get_size ()[0]
        self.text_cell.set_property ("wrap-width", x - 50)

    def on_notification_changed (self, sel):
        list, it=sel.get_selected()
        if it == None:
            return
        nid = list.get (it, 3)[0]
        has_detail = list.get (it, 2)[0]
        print nid
        print has_detail
        if has_detail:
            if self.comment != None:
                self.comment.window.destroy ()
            status = self.office.get_status_with_nid (nid)
            print status
            if status != {}:
                print status
                self.comment = comment.Comment ("%s_%s" % (status['uid'], status['status_id']))
        else:
            if self.comment != None:
                self.comment.window.destroy ()

    def init_view (self):
        self.treeview = self.builder.get_object ("treeview_notification")
        selection = self.treeview.get_selection ()
        selection.connect ("changed", self.on_notification_changed)
        self.column = gtk.TreeViewColumn ("icon")
        self.treeview.append_column (self.column)
        self.icon_cell = gtk.CellRendererPixbuf ()
        self.text_cell = gtk.CellRendererText ()
        self.arrow_cell = gtk.CellRendererText ()

        self.icon_cell.set_property ("yalign", 0.1)
        self.text_cell.set_property ("wrap-width", 150)
        self.text_cell.set_property ("yalign", 0.1)

        self.column.pack_start (self.icon_cell, False)
        self.column.pack_start (self.text_cell, True)
        self.column.pack_start (self.arrow_cell, False)

        self.column.set_cell_data_func (self.icon_cell, self.make_icon)
        self.column.set_attributes (self.text_cell, text=1)
        self.column.set_cell_data_func (self.arrow_cell, self.make_arrow)

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
        user = self.office.get_current_user ()
        pic_square = self.builder.get_object ("image_pic_square")
        user_icon_path = self.office.get_user_icons_dir ()
        pic_square.set_from_file (user_icon_path + '/' + user['pic_square_local'])

        nlist = self.office.get_notification_list ()
        liststore = self.builder.get_object ("list_notification")
        for nid in nlist:
            entry = self.office.get_notification_entry (nid)
            text = None
            has_detail = False
            if len (entry['body_text']) == 0:
                text = entry['title_text']
            else:
                text = entry['body_text']

            if int (entry['app_id']) == 19675640871:
                has_detail = True
            liststore.append ([entry['app_id'], text, has_detail, int(entry['notification_id'])])

    def refresh_error_cb (self, e):
        print e
        pass

if __name__ == "__main__":
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    n = Notification ()
    gtk.main ()


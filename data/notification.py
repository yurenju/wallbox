#!/usr/bin/env python

import pygtk
pygtk.require ("2.0")
import gtk
import dbus

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

        self.office.refresh (reply_handler=self.refresh_reply_cb, \
                            error_handler=self.refresh_error_cb)

    def refresh_reply_cb (self):
        nlist = self.office.get_notification_list ()
        liststore = self.builder.get_object ("list_notification")
        for nid in nlist:
            entry = self.office.get_notification_entry (nid)
            liststore.append ([None, entry[''], False])

    def refresh_error_cb (self, e):
        pass

if __name__ == "__main__":
    n = NotificationView ()
    gtk.main ()


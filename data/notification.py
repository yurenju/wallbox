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


if __name__ == "__main__":
    n = NotificationView ()
    gtk.main ()


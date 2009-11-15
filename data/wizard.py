#!/usr/bin/env python

import pygtk
pygtk.require ("2.0")
import gtk
import dbus

class Wizard:
    def __init__ (self):
        self.builder = gtk.Builder ()
        self.builder.add_from_file ("view.glade")
        self.assistant = self.builder.get_object ("wizard_welcome")
        self.assistant.set_page_complete (self.assistant.get_nth_page (0), True)
        self.assistant.set_page_complete (self.assistant.get_nth_page (3), True)
        self.assistant.show ()

        self.builder.connect_signals (self)

        bus = dbus.SessionBus ()
        obj = bus.get_object ("org.wallbox.PostOfficeService", \
            "/org/wallbox/PostOfficeObject")

        self.office = dbus.Interface \
            (obj, "org.wallbox.PostOfficeInterface")

    def on_button_extra_perm_clicked (self, widget, data=None):
        pass

    def on_button_active_clicked (self, widget, data=None):
        self.office.login ()


if __name__ == "__main__":
    w = Wizard ()
    gtk.main ()


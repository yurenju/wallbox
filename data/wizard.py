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
        print "extra perm"

    def on_button_active_clicked (self, widget, data=None):
        self.office.login ()
        hbox = self.builder.get_object ("hbox_active")
        hbox.remove (widget)
        continue_button = gtk.Button ("Continue")
        hbox.pack_start (continue_button, True, False, 0)
        continue_button.show ()
        continue_button.connect ("clicked", self.on_button_continue_clicked, None)

    def on_button_continue_clicked (self, widget, data=None):
        self.assistant.set_page_complete (self.assistant.get_nth_page (1), True)
        self.assistant.set_current_page (2)

    


if __name__ == "__main__":
    w = Wizard ()
    gtk.main ()


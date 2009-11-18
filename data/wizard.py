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
        self.assistant.connect ("apply", self.apply, None)
        self.assistant.show ()

        self.builder.connect_signals (self)

        bus = dbus.SessionBus ()
        obj = bus.get_object ("org.wallbox.PostOfficeService", \
            "/org/wallbox/PostOfficeObject")

        self.office = dbus.Interface \
            (obj, "org.wallbox.PostOfficeInterface")

    def apply (self, widget, data=None):
        self.assistant.destroy ()

    def show_continue_button (self, remove_widget, page_index, box_name):
        hbox = self.builder.get_object (box_name)
        hbox.remove (remove_widget)
        continue_button = gtk.Button ("Continue")
        hbox.pack_start (continue_button, True, False, 0)
        continue_button.show ()
        self.continue_id = \
            continue_button.connect \
            ("clicked", self.on_button_continue_clicked, page_index)

    def on_button_extra_perm_clicked (self, widget, data=None):
        self.office.get_ext_perm ()
        self.show_continue_button (widget, 2, "hbox_extra_perm")

    def on_button_active_clicked (self, widget, data=None):
        self.office.login ()
        self.show_continue_button (widget, 1, "hbox_active")

    def on_button_continue_clicked (self, widget, data=None):
        self.assistant.set_page_complete \
            (self.assistant.get_nth_page (int (data)), True)

        self.assistant.set_current_page (int(data)+1)
        widget.disconnect (self.continue_id)

    


if __name__ == "__main__":
    w = Wizard ()
    gtk.main ()


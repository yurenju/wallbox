#!/usr/bin/env python

import pygtk
pygtk.require ("2.0")
import gtk
import dbus
import dbus.mainloop.glib
import notification
import comment

def show_notification (icon, n):
    if n.window.get_property ("visible"):
        n.window.hide ()
        if n.comment != None:
            n.comment.window.destroy ()
    else:
        (screen, rect, orientation) = icon.get_geometry ()
        n.window.move (rect.x, rect.y+10)
        n.window.show ()
        n.entry_status.grab_focus ()

if __name__ == "__main__":
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    status_icon = gtk.status_icon_new_from_stock (gtk.STOCK_OPEN)
    n = notification.Notification (True)
    status_icon.connect ("activate", show_notification, n)
    gtk.main ()

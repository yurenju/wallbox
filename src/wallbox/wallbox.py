#!/usr/bin/env python

import pygtk
pygtk.require ("2.0")
import gtk
import dbus
import dbus.mainloop.glib
import notification
import wizard
import comment
import os
import os.path
import ConfigParser
from subprocess import Popen, PIPE
import pkg_resources
import time

def read_all_reply_handler (reply=None):
    pass

def read_all_error_handler (error=None):
    pass

class wallbox:
    config_parser = None

    def __init__ (self):

        bus = dbus.SessionBus ()
        obj = bus.get_object ("org.wallbox.PostOfficeService", \
            "/org/wallbox/PostOfficeObject")

        self.office = dbus.Interface \
            (obj, "org.wallbox.PostOfficeInterface")

        status = self.office.get_office_status ()
        if status == 3:
            w = wizard.Wizard ()
            w.assistant.connect ("destroy", self.wizard_finish)
        else:
            self.post_init ()

    def wizard_finish (self, widget, data=None):
        self.post_init ()

    def post_init (self):
        config_dir = os.path.expanduser ("~/.config")
        if not os.path.exists (config_dir):
            os.mkdir (config_dir)

        self.config_parser = ConfigParser.ConfigParser ()
        self.config_parser.read (config_dir + "/wallbox.conf")
        if not self.config_parser.has_section ("general"):
            self.config_parser.add_section ("general")

        try:
            self.refresh_interval = self.config_parser.getint ("general", "refresh_interval")
        except ConfigParser.NoOptionError:
            self.refresh_interval = 60
            self.config_parser.set ("general", "refresh_interval", 60)

        try:
            self.notification_num = self.config_parser.getint("general", "notification_num")
        except ConfigParser.NoOptionError:
            self.notification_num = 10
            self.config_parser.set ("general", "notification_num", 10)

        self.office.set_refresh_interval (self.refresh_interval)
        self.office.set_notification_num (self.notification_num)

        configfile = open (config_dir + "/wallbox.conf", 'wb')
        self.config_parser.write (configfile)

        status_icon = gtk.status_icon_new_from_stock (gtk.STOCK_OPEN)
        n = notification.Notification ()
        self.status_icon = status_icon
        status_icon.connect ("activate", self.show_notification, n)
        n.connect ("has-unread", self.has_unread)

    def has_unread (self, data=None):
        self.status_icon.set_blinking (True)

    def show_notification (self, icon, n):
        if n.window.get_property ("visible"):
            n.window.hide ()
            if n.comment != None:
                n.comment.window.destroy ()
        else:
            self.status_icon.set_blinking (False)
            self.office.notification_mark_all_read \
                (reply_handler=read_all_reply_handler, error_handler=read_all_error_handler)
            (screen, rect, orientation) = icon.get_geometry ()
            n.window.move (rect.x, rect.y+10)
            n.window.show ()
            n.entry_status.grab_focus ()

def run_post_office ():
    bus = dbus.SessionBus ()
    try:
        obj = bus.get_object ("org.wallbox.PostOfficeService", \
            "/org/wallbox/PostOfficeObject")
    except:
        print "execute post_office.py"
        office = pkg_resources.resource_filename \
                    (__name__, "post_office.py")
        Popen ([office], shell=True)
        time.sleep (1)
        
def run_wallbox ():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    run_post_office ()
    w = wallbox ()
    gtk.main ()

if __name__ == "__main__":
    run_wallbox ()

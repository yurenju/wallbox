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
import defs
import logging

logging.basicConfig (level=defs.log_level)

def reply_handler (reply=None):
    pass

def error_handler (error=None):
    pass

class wallbox:
    config_parser = None

    def __init__ (self):
        self.status_icon = None
        self.activate_id = None
        self.popup_id = None
        bus = dbus.SessionBus ()
        obj = bus.get_object ("org.wallbox.PostOfficeService", \
            "/org/wallbox/PostOfficeObject")

        self.office = dbus.Interface \
            (obj, "org.wallbox.PostOfficeInterface")

        self.builder = gtk.Builder ()
        ui_file = pkg_resources.resource_filename \
                    (__name__, "data/wallbox.ui")
        self.builder.add_from_file (ui_file)
        self.menu = self.builder.get_object ("menu")
        self.about = self.builder.get_object ("aboutdialog")
        self.setting = self.builder.get_object ("dialog_setting")
        self.builder.connect_signals (self, None)

        status = self.office.get_office_status ()
        if status == defs.NO_LOGIN:
            self.wizard = wizard.Wizard ()
            self.wizard.assistant.connect ("apply", self.wizard_finish, None)
        else:
            self.setup_configuration ()
            self.make_ui ()

    def wizard_finish (self, widget, data=None):
        self.wizard.assistant.hide ()
        self.setup_configuration ()
        self.make_ui ()

    def setup_configuration (self):
        config_dir = os.path.expanduser ("~/.config")
        self.config_dir = config_dir
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

    def make_ui (self):
        if self.status_icon != None:
            self.status_icon.set_visible (False)

        self.notification = notification.Notification ()
        self.notification.connect ("has-unread", self.has_unread)
        self.init_status_icon ()

    def init_status_icon (self):
        self.status_icons = {}
        icon_ids = [str(i) for i in range (1, 9)]
        icon_ids.append ("p")
        for num in icon_ids:
            icon_file = pkg_resources.resource_filename \
                        (__name__, "/data/images/wallbox_%s.png" % str (num))
            self.status_icons[str (num)] = gtk.status_icon_new_from_file (icon_file)
            self.status_icons[str (num)].set_visible (False)
            self.status_icons[str (num)].connect ("activate", self.show_notification, self.notification)
            self.status_icons[str (num)].connect ("popup-menu", self.on_right_click)

        icon_file = pkg_resources.resource_filename \
                    (__name__, "/data/images/wallbox.png")
        self.status_icons["normal"] = gtk.status_icon_new_from_file (icon_file)
        self.status_icon = self.status_icons["normal"]
        self.status_icon.connect ("activate", self.show_notification, self.notification)
        self.status_icon.connect ("popup-menu", self.on_right_click)

    def has_unread (self, notification, unread_num):
        self.status_icon.set_visible (False)
        if unread_num < 10:
            self.status_icon = self.status_icons[str (unread_num)]
        else:
            self.status_icon = self.status_icons["p"]

        self.status_icon.set_visible (True)
        self.status_icon.set_blinking (True)

    def on_right_click (self, widget, event_button, event_time):
        self.menu.popup (None, None, gtk.status_icon_position_menu, \
                        event_button, event_time, self.status_icon)

    def on_item_setting_activate (self, item, data=None):
        entry_notification = self.builder.get_object ("entry_notification")
        entry_refresh_interval = self.builder.get_object ("entry_refresh_interval")
        entry_notification.set_text (str (self.notification_num))
        entry_refresh_interval.set_text (str (self.refresh_interval))
        response = self.setting.run ()
        self.setting.hide ()
        if response == 1:
            try:
                notification_num = int (entry_notification.get_text ())
            except:
                notification_num = 10

            try:
                refresh_interval = int (entry_refresh_interval.get_text ())
            except:
                refresh_interval = 60

            self.config_parser.set ("general", "notification_num", notification_num)
            self.config_parser.set ("general", "refresh_interval", refresh_interval)
            self.notification_num = notification_num
            self.refresh_interval = refresh_interval
            self.office.set_notification_num (notification_num)
            self.office.set_refresh_interval (refresh_interval)
            configfile = open (self.config_dir + "/wallbox.conf", 'wb')
            self.config_parser.write (configfile)
    
    def on_item_login_activate (self, item, data=None):
        if self.notification.window.get_property ("visible"):
            self.notification.window.hide ()
            for k in self.notification.comments:
                self.notification.comments[k].window.hide ()
        self.wizard = wizard.Wizard ()
        self.wizard.assistant.connect ("apply", self.wizard_finish, None)

    def on_item_about_activate (self, item, data=None):
        response = self.about.run ()
        if response == gtk.RESPONSE_DELETE_EVENT or response == gtk.RESPONSE_CANCEL:
            self.about.hide ()

    def on_item_quit_activate (self, item, data=None):
        self.office.kill (reply_handler=reply_handler, error_handler=error_handler)
        gtk.main_quit ()

    def on_item_show_notification_activate (self, item, data=None):
        self.show_notification (self.status_icon, self.notification)

    def show_notification (self, icon, n):
        self.status_icon.set_blinking (False)
        self.office.notification_mark_all_read \
            (reply_handler=reply_handler, error_handler=error_handler)

        if n.window.get_property ("visible"):
            n.window.hide ()
            for k in n.comments:
                n.comments[k].window.hide ()
        else:
            (screen, rect, orientation) = icon.get_geometry ()
            n.window.move (rect.x, rect.y+10)
            n.window.show ()
            n.entry_status.grab_focus ()

        if self.status_icon != self.status_icons["normal"]:
            self.status_icon.set_visible (False)
            self.status_icon = self.status_icons["normal"]
            self.status_icon.set_visible (True)

def run_post_office ():
    bus = dbus.SessionBus ()
    try:
        obj = bus.get_object ("org.wallbox.PostOfficeService", \
            "/org/wallbox/PostOfficeObject")
        office = dbus.Interface \
            (obj, "org.wallbox.PostOfficeInterface")
        office.kill ()
        time.sleep (0.5)
    except:
        logging.info ("execute post_office.py")

    office = pkg_resources.resource_filename \
                (__name__, "post_office.py")
    Popen (["python %s" % office], shell=True)
    time.sleep (1)
        
def run_wallbox ():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    run_post_office ()
    w = wallbox ()
    gtk.main ()

if __name__ == "__main__":
    run_wallbox ()

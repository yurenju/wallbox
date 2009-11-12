#!/usr/bin/env python

import unittest
import dbus
import time
import sys
import os
import dbus.mainloop.glib
import random

IS_LOGIN = 0
LOADING = 1
WAITING_LOGIN = 2
NO_LOGIN = 3
STANDBY = 4

class TestDbusPostOffice (unittest.TestCase):
    def setUp (self):
        bus = dbus.SessionBus ()

        obj = bus.get_object ("org.wallbox.PostOfficeService", \
            "/org/wallbox/PostOfficeObject")

        self.office = dbus.Interface \
            (obj, "org.wallbox.PostOfficeInterface")

        if self.office.get_office_status () == NO_LOGIN:
            self.office.login ()

    def refresh_reply_handler (self):
        pass
    def refresh_error_handler (self, e):
        pass

    def test_get_notification (self):
        time.sleep (3)
        if self.office.get_office_status () == WAITING_LOGIN:
            self.office.login_completed ()
        self.office.refresh (reply_handler=self.refresh_reply_handler, \
                            error_handler=self.refresh_error_handler)
        time.sleep (10)

        ns = self.office.get_notification_list ()
        for n in ns:
            entry = self.office.get_notification_entry (n)
            self.assert_ ("test" in entry['body_text'])

    def test_post_status (self):
        time.sleep (3)
        if self.office.get_office_status () == WAITING_LOGIN:
            self.office.login_completed ()
        text1 = "post test status %d" % random.randrange (100) 
        self.office.post_status (text1)
        self.office.refresh (reply_handler=self.refresh_reply_handler, \
                            error_handler=self.refresh_error_handler)
        time.sleep (10)
        status = self.office.get_current_status ()
        self.assert_ (text1 in status['message'])

    def test_comment (self):
        time.sleep (3)
        if self.office.get_office_status () == WAITING_LOGIN:
            self.office.login_completed ()
        text1 = "post test comment %d" % random.randrange (100)

        self.office.refresh (reply_handler=self.refresh_reply_handler, \
                            error_handler=self.refresh_error_handler)
        time.sleep (10)
        status = self.office.get_current_status ()
        post_id = "%d_%s" % (status['uid'], status['status_id'])

        self.office.post_comment (post_id, text1)
        self.office.refresh (reply_handler=self.refresh_reply_handler, \
                            error_handler=self.refresh_error_handler)
        time.sleep (10)
        status = self.office.get_current_status ()
        comments_list = self.office.get_comments_list (post_id)
        xid = comments_list.pop ()
        c = self.office.get_comment_entry (post_id, xid)
        print c['text']
        self.assert_ (c['text'] == text1)

if __name__ == "__main__":
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    unittest.main ()

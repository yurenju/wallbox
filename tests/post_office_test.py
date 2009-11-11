#!/usr/bin/env python

import unittest
import dbus
import time
import sys
import os

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

    def test_get_notification (self):
        time.sleep (3)
        if self.office.get_office_status () == WAITING_LOGIN:
            self.office.login_completed ()
        self.office.refresh ()
        time.sleep (10)

        ns = self.office.get_notification ()
        for n in ns:
            self.assert_ ("test" in n['body_text'])

'''
    def test_post_status (self):
        time.sleep (3)
        if self.office.get_office_status () == WAITING_LOGIN:
            self.office.login_completed ()
        text1 = "post test status"
        self.office.post_status (text1)
        self.office.refresh ()
        self.sleep (5)
        status = self.get_current_status ()
        self.assert_ (text1 == status['message'])

    def test_comment (self):
        time.sleep (3)
        if self.office.get_office_status () == WAITING_LOGIN:
            self.office.login_completed ()
        text1 = "post test comment"

        status = self.office.get_current_status ()
        post_id = "%d_%s" % (status['uid'], status['status_id'])

        self.office.post_comment (post_id)
        time.sleep (5)
        status = self.office.get_current_status ()

        comments = self.office.get_comments (post_id)
        c = comments.pop ()
        self.assert_ (c['text'] == text1)
'''
if __name__ == "__main__":
    unittest.main ()

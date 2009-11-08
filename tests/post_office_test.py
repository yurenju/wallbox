#!/usr/bin/env python
import unittest
import dbus
import wallbox
import time

class TestDbusPostOffice (unittest.TestCase):
    def setUp (self):
        bus = dbus.SessionBus ()

        obj = bus.get_object ("org.wallbox.PostOfficeService", \
            "/org/wallbox/PostOfficeObject")

        self.office = dbus.Interface \
            (obj, "org.wallbox.PostOfficeInterface")

        self.login ()

    def get_notification_test (self):
        while self.office.get_office_status () != wallbox.STANDBY:
            time.sleep (5)

        ns = self.office.get_notification ()
        for n in ns:
            self.assert_ ("test" in n['body_text'])

    def post_status_test (self):
        


if __name__ == "__main__":
    unittest.main ()

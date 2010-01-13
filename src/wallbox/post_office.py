#!/usr/bin/env python

import dbus
import gobject
import dbus.service
import dbus.mainloop.glib
import facebook
import subprocess
import os
import defs
import logging
import utils

__author__ = 'Yuren Ju <yurenju@gmail.com>'

IS_LOGIN = 0
REFRESHING = 1
WAITING_LOGIN = 2
NO_LOGIN = 3

GET_ICON_TIMEOUT = 3

logging.basicConfig (level=defs.log_level)

class PostOffice (dbus.service.Object):
    def __init__ (self, bus_name, bus_path):
        self.current_status = None
        self.app_ids = []
        self.applications = {}
        self.user_ids = []
        self.users = []
        self.status = {}
        self.updated_timestamp = None
        self.notification_num = 10 
        self.refresh_interval = 60
        self.notification = []
        self.session = None
        self.session_code = None
        self.api_key = '9103981b8f62c7dbede9757113372240'
        self.secret = '4cd1dffd6bf0d466bf9ffcf2dcf7805c'
        self.office_status = NO_LOGIN
        self.last_nid = 0
        self.prepare_directories ()

        path = self.local_data_dir + "/cache.pickle"
        cache = utils.pickle_load (path)
        if cache != None:
            for skey in cache:
                setattr (self, skey, cache[skey])

        try:
            dbus.service.Object.__init__ (self, bus_name, bus_path)
        except KeyError:
            logging.debug ("DBus interface registration failed - other wallbox running somewhere")
            pass

        path = self.local_data_dir + "/auth.pickle"
        fb = utils.restore_auth_status (path, self.api_key, self.secret)
        if fb != None:
            self.uid = fb.uid
            self.status_changed (IS_LOGIN)
            self.fb = fb

            if self.uid not in self.user_ids:
                self.user_ids.append (self.uid)

            gobject.timeout_add (self.refresh_interval * 1000, self._refresh)
        else:
            self.status_changed (NO_LOGIN)

        gobject.timeout_add (self.refresh_interval * 1000, self._refresh)


    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='s', out_signature='')
    def set_session_code (self, session_code):
        self.session_code = session_code.strip ()

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='s')
    def get_secret (self):
        return self.secret

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='s')
    def get_api_key (self):
        return self.api_key

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='')
    def notification_mark_all_read (self):
        logging.debug ("notification_mark_all_read")
        ids = []
        for entry in self.notification:
            if entry['is_unread']:
                entry['is_unread'] = False
                ids.append (entry['notification_id'])
        if len (ids) == 0:
            logging.debug ("no need to notification mark all read")
            return
        self.fb ("notifications_markRead", \
            {"session_key": self.session['session_key'], "notification_ids": ids})

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='i')
    def get_office_status (self):
        return self.office_status

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='')
    def login (self):
        self.fb = facebook.Facebook (self.api_key, self.secret, self.session_code)
        self.session = self.fb.auth.getSession ()
        self.uid = self.fb.users.getInfo ([self.fb.uid])[0]['uid']
        path = self.local_data_dir + "/auth.pickle"
        utils.save_auth_status (path, self.session)
        if self.uid not in self.user_ids:
            self.user_ids.append (self.uid)
        self.status_changed (IS_LOGIN)

        gobject.timeout_add (self.refresh_interval * 1000, self._refresh)

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='')
    def get_ext_perm (self):
        ext_perm_url = "http://www.facebook.com/" + \
            "connect/prompt_permissions.php" + \
            "?api_key=%s&fbconnect=true&v=1.0&display=popup" % self.api_key + \
            "&extern=1&ext_perm=publish_stream,read_stream" 
        import webbrowser
        webbrowser.open (ext_perm_url)

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='')
    def login_completed (self):
        self.session = self.fb.auth.getSession ()
        self.uid = self.fb.users.getInfo ([self.fb.uid])[0]['uid']
        self.user_ids.append (self.uid)
        self.status_changed (IS_LOGIN)

        gobject.timeout_add (self.refresh_interval * 1000, self._refresh)

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='a{sv}')
    def get_session (self):
        if self.session == None:
            return {}
        return self.session

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='ai')
    def get_notification_list (self):
        nlist = []
        for n in self.notification:
            nlist.append (int (n['notification_id']))
        return nlist

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='i', out_signature='a{sv}')
    def get_notification_entry (self, notification_id):
        for n in self.notification:
            if int (n['notification_id']) == notification_id:
                return n
        else:
            return {}

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='ss', out_signature='')
    def post_comment (self, post_id, comment):
        cid = self.fb.stream.addComment (post_id=post_id, comment=comment)
        self.status[post_id]['comments'].append ({'text': comment, 'fromid': self.uid, 'time': 0, 'id': cid})

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='i', out_signature='')
    def set_notification_num (self, num):
        self.notification_num = num

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='i', out_signature='')
    def set_refresh_interval (self, interval):
        self.refresh_interval = interval

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='s', out_signature='as')
    def get_comments_list (self, post_id):
        clist = []
        for s in self.status:
            logging.debug ("post_id: %s" % s)
        for c in self.status[post_id]['comments']:
            clist.append (c['id'])
            logging.debug ("\t%s" % c['id'])
        print
        return clist

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='ss', out_signature='a{sv}')
    def get_comment_entry (self, post_id, id):
        comments = self.status[post_id]['comments']
        for c in comments:
            if c['id'] == id:
                return c
        return {}


    def check_refresh_complete (self):
        if self.rs.isAlive ():
            return True

        if self.last_nid == self.rs.last_nid:
            self.status_changed (self.orig_office_status)
            return False

        self.last_nid = self.rs.last_nid
        self.current_status = self.rs.current_status
        self.notification = self.rs.notification
        self.status = self.rs.status
        self.user_ids = self.rs.user_ids
        self.users = self.rs.users
        self.app_ids = self.rs.app_ids
        self.applications = self.rs.applications
        path = self.local_data_dir + "/cache.pickle"
        utils.pickle_dump (self, path)

        self.status_changed (self.orig_office_status)
        return False

    def _refresh (self):
        logging.debug ("refresh start")
        if self.office_status != IS_LOGIN:
            logging.info ("not IS_LOGIN")
            return True

        self.orig_office_status = self.office_status
        self.status_changed (REFRESHING)
        logging.info ("notification_num: %s" % self.notification_num)
        self.rs = RefreshProcess \
            (self.notification_num, self.fb, self.uid, self.user_icons_dir, self.app_icons_dir, self.user_ids, self.last_nid)
        self.rs.start ()
        gobject.timeout_add (1000, self.check_refresh_complete)

        return True

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='')
    def refresh (self):
        self._refresh ()

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='s', out_signature='')
    def post_status (self, text):
        self.fb.users.setStatus (status=text, clear=False, status_includes_verb=True, uid=self.uid)

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='a{sv}')
    def get_current_status (self):
        if self.current_status == None or len (self.current_status) < 1:
            return {}
        logging.debug ("%s\n" % self.current_status['message'])
        return self.current_status

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='s', out_signature='a{sv}')
    def get_status (self, post_id):
        result = self.status[post_id].copy ()
        logging.debug (result)
        if result.has_key ('comments'):
            del result['comments']
        if len (result) < 1:
            return {}
        return result

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='i', out_signature='a{sv}')
    def get_status_with_nid (self, nid):
        logging.debug ("get_status_with_nid: %s" % nid)
        result = None
        logging.debug ("status len: %s" % len(self.status))
        for key in self.status:
            logging.debug ("looking id: %s\n" % self.status[key]['notification_ids'])

            if self.status[key].has_key ('notification_ids') and \
                str (nid) in self.status[key]['notification_ids']:
                result = self.status[key].copy ()
                if result.has_key ('comments'):
                    del result ['comments']
                logging.debug ("status: %s\n" % self.status[key]['message'])
                return result
        logging.debug ("get_status_with_nid: no result")
        return {}
    

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='x', out_signature='a{sv}')
    def get_application (self, app_id):
        return self.applications[app_id]

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='a{sv}')
    def get_current_user (self):
        logging.debug ("get current user: %s" % int (self.uid))
        for u in self.users:
            logging.debug ("search %s" % u['uid'])
            if int (u['uid']) == int (self.uid):
                return u
        logging.debug ("no current user")
        return {}

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='x', out_signature='a{sv}')
    def get_user (self, uid):
        for u in self.users:
            if int (u['uid']) == int (uid):
                return u
        return {}

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='s')
    def get_app_icons_dir (self):
        return self.app_icons_dir

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='s')
    def get_user_icons_dir (self):
        return self.user_icons_dir

    @dbus.service.signal ("org.wallbox.PostOfficeInterface", signature='i')
    def status_changed (self, status):
        self.office_status = status
        logging.debug ("emit signal: %s" % status)

    def prepare_directories (self):
        self.local_data_dir = \
            "%s/.local/share/wallbox" % os.getenv ("HOME")

        self.user_icons_dir = \
            "%s/user_icons" % self.local_data_dir

        self.app_icons_dir = \
            "%s/app_icons" % self.local_data_dir

        for d in [self.user_icons_dir, self.app_icons_dir]:
            if not os.path.exists (d):
                subprocess.call (['mkdir', '-p', d])

def main ():
    dbus.mainloop.glib.DBusGMainLoop (set_as_default=True)

    bus = dbus.SessionBus ()
    name = dbus.service.BusName ("org.wallbox.PostOfficeService", bus)
    obj = PostOffice (bus, "/org/wallbox/PostOfficeObject")

    mainloop = gobject.MainLoop ()
    mainloop.run ()

if __name__ == "__main__":
    main ()

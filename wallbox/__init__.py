#!/usr/bin/env python

import dbus
import gobject
import dbus.service
import dbus.mainloop.glib
import facebook
import subprocess
import os
import urllib
import urlparse
import time
import re
import datetime
import secert

__author__ = 'Yuren Ju <yurenju@gmail.com>'

IS_LOGIN = 0
LOADING = 1
WAITING_LOGIN = 2
NO_LOGIN = 3
STANDBY = 4

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
        self.refresh_interval = 5
        self.notification = []
        self.api_key = '9103981b8f62c7dbede9757113372240'
        self.office_status = NO_LOGIN
        self.prepare_directories ()

        # wallbox auth
        self.fb = facebook.Facebook (self.api_key, secert.key)

        try:
            dbus.service.Object.__init__ (self, bus_name, bus_path)
        except KeyError:
            print "DBus interface registration failed - other wallbox running somewhere"
            pass

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='i')
    def get_office_status (self):
        return self.office_status

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='')
    def login (self):
        self.fb.auth.createToken ()
        self.fb.login ()
        self.office_status = WAITING_LOGIN

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='')
    def get_ext_perm (self):
        ext_perm_url = "http://www.facebook.com/" + \
            "connect/prompt_permissions.php" + \
            "?api_key=%s&fbconnect=true&v=1.0&display=popup" % self.api_key + \
            "&extern=1&ext_perm=publish_stream" 
        import webbrowser
        webbrowser.open (ext_perm_url)

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='')
    def login_completed (self):
        self.session = self.fb.auth.getSession ()
        self.uid = self.fb.users.getInfo ([self.fb.uid])[0]['uid']
        self.user_ids.append (self.uid)
        self.office_status = IS_LOGIN

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

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='ss', out_signature='')
    def post_comment (self, post_id, comment):
        self.fb.stream.addComment (post_id=post_id, comment=comment)

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
            print "post_id: %s" % s
        for c in self.status[post_id]['comments']:
            clist.append (c['id'])
            print "\t%s" % c['id']
        print
        return clist

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='ss', out_signature='a{sv}')
    def get_comment_entry (self, post_id, id):
        comments = self.status[post_id]['comments']
        for c in comments:
            if c['id'] == id:
                return c
        return {}

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='')
    def refresh (self):
        print "refresh start"
        self.get_remote_current_status ()
        print "get remote current status"
        self.get_remote_notification ()
        print "get remote notification"
        self.get_remote_comments ()
        print "get remote comments"
        self.get_remote_users_icon ()
        print "get remote users icon"
        self.get_remote_applications_icon ()
        print "get remote applications icon"
        self.updated_timestamp = datetime.date.today ()
        print "updated finish"

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='s', out_signature='')
    def post_status (self, text):
        self.fb.users.setStatus (status=text, clear=False, status_includes_verb=True, uid=self.uid)

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='a{sv}')
    def get_current_status (self):
        print "get current status"
        print "%s\n" % self.current_status['message']
        return self.current_status

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='s', out_signature='a{sv}')
    def get_status (self, post_id):
        result = self.status[post_id].copy ()
        if result.has_key ('comments'):
            del result['comments']
        return result

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='i', out_signature='a{sv}')
    def get_status_with_nid (self, nid):
        print "get_status_with_nid: %s" % nid
        result = None
        for key in self.status:
            print "id: ",
            for id in self.status[key]['notification_ids']:
                print "%s, " % id,
            print
            if self.status[key].has_key ('notification_ids') and \
                nid in self.status[key]['notification_ids']:
                result = self.status[key].copy ()
                del result ['comments']
                print "%s\n" % result['message']
                return result
        return {}
    

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='s', out_signature='a{sv}')
    def get_application (self, app_id):
        return self.applications[int (app_id)]

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='a{sv}')
    def get_current_user (self):
        for u in self.users:
            if u['uid'] == self.uid:
                return u

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='x', out_signature='a{sv}')
    def get_user (self, uid):
        for u in self.users:
            if u['uid'] == uid:
                return u

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='s')
    def get_app_icons_dir (self):
        return self.app_icons_dir

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='s')
    def get_user_icons_dir (self):
        return self.user_icons_dir

    def get_remote_current_status (self):
        status = \
            self.fb.fql.query \
            ("SELECT uid, status_id, message, source FROM status WHERE uid='%s' LIMIT 1" % \
            self.uid)

        self.current_status = status[0]

    def get_remote_notification (self):
        notification = self.fb.fql.query \
            ("SELECT notification_id, title_text, body_text, is_unread, " + \
            "is_hidden, href, app_id, sender_id " + \
            "FROM notification WHERE recipient_id = '%d' LIMIT %d" % \
            (self.uid, self.notification_num))
        self.notification = notification

    def _dump_comments (self, post_id):
        print "status: %s: %s" % (post_id, self.status[post_id]['message'])
        print "comments:"
        for c in self.status[post_id]['comments']:
            print "\t%s" % c['text']

    def get_remote_comments (self):
        pattern_id = re.compile ("&id=(\d+)")
        pattern_fbid = re.compile ("story_fbid=(\d+)")
        for n in self.notification:
            print "app_id: %d: %s" % (n['app_id'], n['body_text'])
            if n['app_id'] == 19675640871:
                #get post_id
                post_id = None
                m_id = pattern_id.search (n['href'])
                m_fbid = pattern_fbid.search (n['href'])
                if m_id != None and m_fbid != None:
                    id = m_id.group (1)
                    status_id = m_fbid.group (1)
                    post_id = "%s_%s" % (id, status_id)
                    if not self.status.has_key (post_id):
                        self.status[post_id] = {}
                        self.status[post_id] = self.fb.fql.query \
                            ("SELECT uid, time, message, status_id FROM status " + \
                            "WHERE uid = %s AND status_id = %s LIMIT 1" % \
                            (id, status_id))[0]

                        comments = self.fb.fql.query \
                            ("SELECT id, fromid, text, time FROM comment WHERE post_id='%s'" \
                            % post_id)

                        self.status[post_id]['comments'] = comments
                        self._dump_comments (post_id)
                    if not self.status[post_id].has_key ('notification_ids'):
                        self.status[post_id]['notification_ids'] = []
                    if not int (n['notification_id']) in self.status[post_id]['notification_ids']:
                        self.status[post_id]['notification_ids'].append (int (n['notification_id']))

        '''
        current_post_id = "%s_%s" % (self.current_status['uid'], self.current_status['status_id'])
        self.status[current_post_id] = {}
        self.status[current_post_id]['message'] = self.current_status['message']
        comments = self.fb.fql.query \
            ("SELECT id, fromid, text, time FROM comment WHERE post_id='%s'" \
            % current_post_id)

        self.status[current_post_id]['comments'] = comments
        self._dump_comments (current_post_id)
        self.status[post_id]['notification_id'] = int (n['notification_id'])
        '''

    def get_remote_users_icon (self):
        for n in self.notification:
            if not n['sender_id'] in self.user_ids:
                self.user_ids.append (n['sender_id'])
        for skey in self.status:
            for c in self.status[skey]['comments']:
                if not c['fromid'] in self.user_ids:
                    self.user_ids.append (c['fromid'])
        self.users = \
            self.fb.users.getInfo (self.user_ids, ["name", "pic_square"])

        for u in self.users:
            if (len (u['pic_square']) > 0):
                icon_name = \
                    os.path.basename \
                    (urlparse.urlsplit (u['pic_square']).path)

                urllib.urlretrieve \
                    (u['pic_square'], "%s/%s" % \
                    (self.user_icons_dir, icon_name))
                u['pic_square_local'] = icon_name

    def get_remote_applications_icon (self):
        for n in self.notification:
            if not n['app_id'] in self.app_ids:
                self.app_ids.append (n['app_id'])

        for app_id in self.app_ids:
            app = self.fb.fql.query \
                ("SELECT icon_url FROM application WHERE app_id='%d'" % \
                app_id)[0]

            icon_name = os.path.basename \
                (urlparse.urlsplit (app['icon_url']).path)
                
            urllib.urlretrieve \
                (app['icon_url'], "%s/%s" % (self.app_icons_dir, icon_name))
            self.applications[app_id] = {'icon_name': icon_name}

    def prepare_directories (self):
        self.user_icons_dir = \
            "%s/.local/share/wallbox/user_icons" % os.getenv ("HOME")

        self.app_icons_dir = \
            "%s/.local/share/wallbox/app_icons" % os.getenv ("HOME")

        for d in [self.user_icons_dir, self.app_icons_dir]:
            if not os.path.exists (d):
                subprocess.call (['mkdir', '-p', d])

if __name__ == "__main__":
    dbus.mainloop.glib.DBusGMainLoop (set_as_default=True)

    bus = dbus.SessionBus ()
    name = dbus.service.BusName ("org.wallbox.PostOfficeService", bus)
    obj = PostOffice (bus, "/org/wallbox/PostOfficeObject")

    mainloop = gobject.MainLoop ()
    mainloop.run ()

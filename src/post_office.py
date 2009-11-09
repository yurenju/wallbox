import dbus
import gobject
import dbus.service
import dbus.mainloop.glib
import facebook
import wallbox
import subprocess
import os
import urllib
import urlparse

class PostOffice (dbus.service.Object):
    def __init__ (self):
        self.current_status = None
        self.app_ids = []
        self.user_ids = []
        sefl.users = []
        self.status = {}
        self.updated_timestamp = None
        self.notification_num = 5
        self.refresh_interval = 5
        self.notification = []
        self.api_key = '54b855c6ea87048447e76bdae2cef007'
        self.office_status = wallbox.NO_LOGIN
        self.prepare_directories ():

        #social contact auth
        self.fb = facebook.Facebook \
            (self.api_key, \
            '8f9ed80bb60b3e8efae2efb48e07bb96')
        # wallbox auth
        '''
        self.fb = facebook.Facebook \
            ('9103981b8f62c7dbede9757113372240', \
            'eba250ae124ceaba837fc2f72709fb9f')
        '''

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', outsignature='')
    def login (self):
        self.fb.auth.createToken ()
        self.fb.login ()
        self.session = self.fb.getSession ()
        self.uid = fb.users.getInfo ([fb.uid])[0]['uid']
        self.office_status = wallbox.WAITING_LOGIN
        self.user_ids.append (uid)

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', outsignature='v')
    def get_notification (self):
        return self.notification

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='s', outsignature'')
    def post_comment (self, post_id, comment):
        self.fb.stream.addComment (post_id=post_id, comment=comment)

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='i', outsignature'')
    def set_notification_num (self, num):
        self.notification_num = num

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='i', outsignature'')
    def set_refresh_interval (self, interval):
        self.refresh_interval = interval

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='s', outsignature'')
    def get_comments (self, post_id):
        return self.status[post_id]

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', outsignature'')
    def refresh (self):
        self.get_remote_current_status (self)
        self.get_remote_notification (self)
        self.get_remote_comments (self)
        self.get_remote_users_icon (self)
        self.get_remote_applications_icon (self)
        self.update_timestamp (self)

    def get_ext_perm (self):
        ext_perm_url = "http://www.facebook.com/connect/prompt_permissions.php" + \
            "?api_key=%s&fbconnect=true&v=1.0&display=popup&extern=1&ext_perm=publish_stream" % \
            self.api_key
        import webbrowser
        webbrowser.open (ext_perm_url)

    def get_remote_current_status (self):
        status = self.fb.status.get (limit=1)
        self.current_status = status

    def get_remote_notification (self):
        notification = self.fb.fql.query \
            ("SELECT title_text, body_text, is_unread, is_hidden, href, app_id, sender_id " + \
            "FROM notification WHERE recipient_id = '%d' LIMIT %d" % \
            (self.uid, self.notification_num))
        self.notification = notification

    def get_remote_comments (self):
        pattern = re.compile ("id=(\d+).*story_fbid=(\d+)")
        for n in self.notification:
            if n['app_id'] == 2719290516L:
                #get post_id
                post_id = None
                m = pattern.search (msg['href'])
                if m != None:
                    post_id = "%s_%s" % (m.group (1), m.group (2))
                self.status[post_id] = {}
                self.status[post_id]['message'] = n['body_text']
                comments = self.fb.fql.query \
                    ("SELECT fromid, text FROM comment WHERE post_id='%s'" % post_id)
                self.status[post_id]['comments'] = comments

    def get_remote_users_icon (self):
        for n in self.notification:
            if not n['sender_id'] in self.user_ids:
                self.user_ids.append (n['sender_id'])
        for s in self.status:
            for c in s['comments']:
                if not c['fromid'] in self.user_ids:
                    self.user_ids.append (c['fromid'])
        self.users = self.fb.users.getInfo (self.user_ids, ["name", "pic_square"])
        for u in self.users:
            if (len (u['pic_square']) > 0):
                icon_name = os.path.basename (urlparse.urlsplit (u['pic_square']).path)
                urllib.urlretrieve (u['pic_square'], "%s/%s" % (self.user_icons_dir, icon_name))

    def get_remote_applications_icon (self):
        for n in self.notification:
            if not n['app_id'] in self.app_ids:
                self.app_ids.append (n['app_id'])

        for app_id in self.app_ids:
            app = self.fb.fql.query ("SELECT icon_url FROM application WHERE app_id='%d'" % app_id)[0]
            icon_name = os.path.basename (urlparse.urlsplit (app['icon_url']).path)
            urllib.urlretrieve (app['icon_url'], "%s/%s" % (self.app_icons_dir, icon_name))

    def prepare_directories (self):
        self.user_icons_dir = "%s/.local/share/wallbox/user_icons" % os.getenv ("HOME")
        self.app_icons_dir = "%s/.local/share/wallbox/app_icons" % os.getenv ("HOME")
        for d in [user_icons_dir, app_icons_dir]:
            if not os.path.exists (d):
                subprocess.call (['mkdir', '-p', d])


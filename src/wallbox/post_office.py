#!/usr/bin/env python

import dbus
import gobject
import dbus.service
import dbus.mainloop.glib
import facebook
import os
import urllib
import urllib2
import urlparse
import time
import re
import datetime
import threading
import gtk
import socket
import defs
import logging
import utils
import pickle
import sys

__author__ = 'Yuren Ju <yurenju@gmail.com>'

GET_ICON_TIMEOUT = 3
QUERY_TIMEOUT = 15

gtk.gdk.threads_init()
logging.basicConfig (level=defs.log_level)

def touch(fname, times = None):
    fhandle = file(fname, 'a')
    try:
        os.utime(fname, times)
    finally:
        fhandle.close()

class TimeoutError(Exception):
    def __init__ (self, value):
        self.value = value
    def __str__ (self):
        return repr (self.value)

class NoUpdateError(Exception):
    def __init__ (self, value):
        self.value = value
    def __str__ (self):
        return repr (self.value)

class RefreshError(Exception):
    def __init__ (self, value):
        self.value = value
    def __str__ (self):
        return repr (self.value)


class RefreshProcess (threading.Thread):
    def __init__ (self, notification_num, fb, uid, user_icons_dir, app_icons_dir, user_ids, last_nid):
        threading.Thread.__init__ (self)
        self.uid = uid
        self.notification_num = notification_num
        self.fb = fb
        self.current_status = None
        self.app_ids = []
        self.applications = {}
        self.user_ids = user_ids
        self.users = []
        self.status = {}
        self.updated_timestamp = None
        self.refresh_interval = 60
        self.notification = []
        self.user_icons_dir = user_icons_dir
        self.app_icons_dir = app_icons_dir
        self.last_nid = last_nid
        self.refresh_status = {"current_status": False, \
                                "notification": False, \
                                "comments": False, \
                                "users_icon": False, \
                                "apps_icon": False, \
                                "last_notification": False, \
                                "no_need_update": False}

    def _dump_notification (self):
        dump_str = "notification_id, title_text, body_text, is_unread" + \
            ", is_hidden, href, app_id, sender_id\n"
        for n in self.notification:
            dump_str += "%s,%s,%s,%s,%s,%s,%s,%s\n" % \
                (n['notification_id'], n['title_text'], n['body_text'], \
                n['is_unread'], n['is_hidden'], n['href'], n['app_id'], n['sender_id'])
        logging.debug (dump_str)

    def _dump_comments (self):
        for post_id in self.status:
            logging.debug ("status: %s: %s" % (post_id, self.status[post_id]['message']))
            logging.debug ("comments:")
            for c in self.status[post_id]['comments']:
                logging.debug ("\t%s: %s" % (c['id'], c['text']))

    def _dump_status (self):
        for skey in self.status:
            if self.status[skey].has_key ('message'):
                logging.debug ("status: %s" % self.status[skey]['message'])
            else:
                logging.debug ("ERROR status key: %s has no message" % skey)
                logging.debug ("detail:\n%s" % self.status[skey])
            if not self.status[skey].has_key ('notification_ids'):
                logging.debug ("NO notification_ids")
                continue
            nids_log = "nids: "
            for n in self.status[skey]['notification_ids']:
                nids_log += "%s, " % n
            logging.debug (nids_log)

    def dict_to_str (self, result):
        for res in result:
            print res
            for k in res:
                if type (res[k]) != list and type (res[k]) != dict:
                    res[k] = str (res[k])
        return result

    def _query (self, query_str):
	logging.debug ("_query: %s" % query_str)
        default_timeout = socket.getdefaulttimeout ()
        socket.setdefaulttimeout (QUERY_TIMEOUT)
        for i in range (3):
            try:
                result = self.fb.fql.query (query_str)
                if result != None:
                    socket.setdefaulttimeout (default_timeout)
                    result = self.dict_to_str (result)
                    return result
            except:
                logging.debug ("URLError, Sleep 3 sec: %s" % query_str)
                time.sleep (3)
        socket.setdefaulttimeout (default_timeout)
        return None
            
    def get_remote_current_status (self):
        logging.info ("get remote current status")
        qstr = "SELECT uid, status_id, message, " + \
                "source FROM status WHERE uid='%s' LIMIT 1" % self.uid
        status = self._query (qstr)

        if status != None and len (status) > 0:
            self.current_status = status[0]
        else:
            self.current_status = None
        self.refresh_status["current_status"] = True

    def _filter_none (self, items):
        for item in items:
            for k in item:
                if item[k] == None:
                    item[k] = ""

    def get_remote_notification (self):
        logging.info ("get remote notification")
        notification = self._query \
            ("SELECT notification_id, title_text, body_text, is_unread" + \
            ", is_hidden, href, app_id, sender_id " + \
            "FROM notification WHERE recipient_id = '%s' LIMIT %s" % \
            (self.uid, self.notification_num))
        self._filter_none (notification)
        self.last_nid = notification[0]['notification_id']
        self.notification = notification
        self._dump_notification ()
        self.refresh_status["notification"] = True

    def slow_get_streams (self, pattern_id, matched_ns):
        total_result = []
        logging.debug ("fast get stream failed, try slow get stream")
        for n in matched_ns:
            m_id = pattern_id.search (n['href'])
            if m_id != None:
                uid = m_id.group (1)
                logging.debug ("try href: %s" % n['href'])
                for i in range (1, 4):
                    qstr = "SELECT source_id, post_id, message, permalink FROM stream WHERE " + \
                            "source_id = %s AND permalink = '%s' LIMIT %d" % (uid, n['href'], 10**i)
                    logging.debug (qstr)
                    result = self._query (qstr)
                    logging.debug (result)
                    if len (result) > 0:
                        total_result.append (result[0])
                        break
                        
        return total_result

    def get_remote_comments (self):
        logging.info ("get remote comments (fast)")
        new_status = {}
        post_ids = []
        subquery = []
        pattern_id = re.compile ("&id=(\d+)")

        matched_ns = [n for n in self.notification \
            if n['app_id'] == '19675640871' or n['app_id'] == '2309869772']

        if len (matched_ns) == 0:
            return

        for n in matched_ns:
            m_id = pattern_id.search (n['href'])
            if m_id != None:
                uid = m_id.group (1)
                _str = "(source_id = %s AND permalink = '%s')" % (uid, n['href'])
                if _str not in subquery:
                    subquery.append (_str)

        substr = " OR ".join (subquery)
        qstr = "SELECT source_id, post_id, message, permalink FROM stream " + \
            "WHERE %s" % substr
        result = self._query (qstr)

        if len (result) < len (subquery):
            result = self.slow_get_streams (pattern_id, matched_ns)

        # Relating notification and status
        for r in result:
            new_status[r['post_id']] = r
            nids = [n['notification_id'] for n in matched_ns if n['href'] == r['permalink']]
            new_status[r['post_id']]['notification_ids'] = nids
        
        # get comments
        post_ids = ["'%s'" % r['post_id'] for r in result]
        substr = ", ".join (post_ids)
        qstr = "SELECT fromid, text, post_id, id, time FROM comment WHERE post_id IN (%s)" % substr
        comment_result = self._query (qstr)
        for r in result:
            comment_list = [c for c in comment_result if c['post_id'] == r['post_id']]
            new_status[r['post_id']]['comments'] = comment_list

        self.status = new_status
        self._dump_status ()
        self._dump_comments ()
        self.refresh_status["comments"] = True

    def get_remote_icon (self, url, local_path):
        logging.debug ("get_remote_icon: %s" % url)
        local_size = 0

        icon_name = os.path.basename \
            (urlparse.urlsplit (url).path)

        full_path = "%s/%s" % (local_path, icon_name)

        if os.path.exists (full_path) and os.path.isfile (full_path):
            #if modification time < 24hr, ignore update
            mtime = os.path.getmtime (full_path)
            if time.time() - mtime < 60 * 60 * 24: #24hr
                raise NoUpdateError ("mtime is %s, ignore update icon: %s" % (mtime, icon_name))

            local_size = os.path.getsize (full_path)

        try:
            logging.debug ("urlopen: %s" % url)
            remote_icon = urllib2.urlopen (url)
        except:
            raise TimeoutError ("urlopen timeout")

        info = remote_icon.info ()
        remote_size = int (info.get ("Content-Length"))
        remote_icon.close ()

        if remote_size != local_size or not os.path.exists (full_path):
            logging.debug ("size different remote/local: %d/%d, start dwonload icon" % \
                            (remote_size, local_size))
            try:
                urllib.urlretrieve (url, full_path)
                return icon_name
            except:
                raise TimeoutError ("urlretrieve timeout")
        else:
            logging.debug ("icon already exist: %s" % icon_name)
            touch (full_path)
            return icon_name

    def get_remote_users_icon (self):
        logging.info("get remote users icon")
        for n in self.notification:
            if not n['sender_id'] in self.user_ids:
                self.user_ids.append (n['sender_id'])
        for skey in self.status:
            if self.status[skey].has_key ('comments'):
                for c in self.status[skey]['comments']:
                    if not c['fromid'] in self.user_ids:
                        self.user_ids.append (c['fromid'])
        self.users = \
            self.fb.users.getInfo (self.user_ids, ["name", "pic_square"])

        self._filter_none (self.users)

        default_timeout = socket.getdefaulttimeout ()
        socket.setdefaulttimeout (GET_ICON_TIMEOUT)
        logging.debug ("socket timeout: %s" % socket.getdefaulttimeout ())
        timeout_count = 0
        for u in self.users:
            logging.debug ("user: %s, pic_square: %s" % (u['name'], u['pic_square']))
            if (u['pic_square'] != None and len (u['pic_square']) > 0):
                if timeout_count < 3:
                    try:
                        u['pic_square_local'] = \
                            self.get_remote_icon \
                            (u['pic_square'], self.user_icons_dir)
                    except TimeoutError:
                        timeout_count += 1
                        logging.debug ("timeout")
                        u['pic_square_local'] = ""
                    except NoUpdateError:
                        icon_name = os.path.basename \
                            (urlparse.urlsplit (u['pic_square']).path)
                        logging.debug ("No need update: %s" % icon_name)
                        u['pic_square_local'] = icon_name
                        
                else:
                    logging.debug ("timeout 3 times")
                    u['pic_square_local'] = ""
            else:
                u['pic_square_local'] = ""
                
        socket.setdefaulttimeout (default_timeout)
        self.refresh_status["users_icon"] = True

    def get_remote_applications_icon (self):
        logging.info ("get remote applications icon")
        for n in self.notification:
            if not str (n['app_id']) in self.app_ids:
                self.app_ids.append (str (n['app_id']))

        ids_str = ", ".join (self.app_ids)
        qstr = "SELECT icon_url, app_id FROM application WHERE app_id IN (%s)" % ids_str
        apps = self._query (qstr)

        default_timeout = socket.getdefaulttimeout ()
        socket.setdefaulttimeout (GET_ICON_TIMEOUT)
        logging.debug ("socket timeout: %s" % socket.getdefaulttimeout ())
        timeout_count = 0
        for app in apps:
            if timeout_count < 3:
                try:
                    icon_name = self.get_remote_icon \
                        (app['icon_url'], self.app_icons_dir)
                except TimeoutError:
                    logging.debug ("timeout")
                    timeout_count += 1
                    icon_name = ""
                except NoUpdateError:
                    logging.debug ("No need update")
                    icon_name = os.path.basename \
                            (urlparse.urlsplit (app['icon_url']).path)
            else:
                icon_name = ""
            self.applications[app['app_id']] = {'icon_name': icon_name}
        socket.setdefaulttimeout (default_timeout)
        self.refresh_status["apps_icon"] = True

    def get_remote_last_nid (self):
        logging.info ("get_remote_last_nid")
        qstr = "SELECT notification_id FROM notification " + \
                "WHERE recipient_id = %d LIMIT 1" % int (self.uid)
        result = self._query (qstr)
        if result != None and len (result) > 0:
            logging.debug ("get last nid: %d" % int (result[0]['notification_id']))
            logging.debug ("orignal nid: %d" % int (self.last_nid))
            return result[0]['notification_id']
        else:
            return 0

    def run (self):
        last_nid = self.get_remote_last_nid ()
        if last_nid == self.last_nid:
            logging.debug ("no need to update notification")
            self.refresh_status["no_need_update"] = True
            return
        self.last_nid = last_nid
        self.refresh_status["last_notification"] = True
        self.get_remote_current_status ()
        time.sleep (1)
        self.get_remote_notification ()
        time.sleep (1)
        self.get_remote_comments ()
        time.sleep (1)
        self.get_remote_users_icon ()
        time.sleep (1)
        self.get_remote_applications_icon ()
        time.sleep (1)
        self.updated_timestamp = datetime.date.today ()
        logging.debug ("updated finish")


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
        self.refresh_hanedler = None
        self.notification = []
        self.session = None
        self.session_code = None
        self.api_key = '9103981b8f62c7dbede9757113372240'
        self.secret = '4cd1dffd6bf0d466bf9ffcf2dcf7805c'
        self.office_status = defs.NO_LOGIN
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
            self.status_changed (defs.IS_LOGIN)
            self.fb = fb

            if self.uid not in self.user_ids:
                self.user_ids.append (self.uid)

            self.refresh_hanedler = gobject.timeout_add (self.refresh_interval * 1000, self._refresh)
        else:
            self.status_changed (defs.NO_LOGIN)

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
        self.status_changed (defs.IS_LOGIN)

        self.refresh_hanedler = gobject.timeout_add (self.refresh_interval * 1000, self._refresh)

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
        self.status_changed (defs.IS_LOGIN)

        self.refresh_hanedler = gobject.timeout_add (self.refresh_interval * 1000, self._refresh)

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='a{sv}')
    def get_session (self):
        if self.session == None:
            return {}
        return self.session

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='as')
    def get_notification_list (self):
        nlist = [n['notification_id'] for n in self.notification]
        return nlist

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='s', out_signature='a{sv}')
    def get_notification_entry (self, notification_id):
        for n in self.notification:
            if n['notification_id'] == notification_id:
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
        self.last_nid = 0

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='i', out_signature='')
    def set_refresh_interval (self, interval):
        self.refresh_interval = interval
        if self.refresh_hanedler != None:
            gobject.source_remove (self.refresh_hanedler)
            self.refresh_hanedler = gobject.timeout_add (self.refresh_interval * 1000, self._refresh)

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='s', out_signature='as')
    def get_comments_list (self, post_id):
        clist = [c['id'] for c in self.status[post_id]['comments']]
        for s in self.status:
            logging.debug ("post_id: %s" % s)
        return clist

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='ss', out_signature='a{sv}')
    def get_comment_entry (self, post_id, id):
        comments = self.status[post_id]['comments']
        for c in comments:
            if c['id'] == id:
                return c
        return {}

    def check_refresh_complete (self):
        if self.rs.refresh_status["no_need_update"]:
            self.status_changed (self.orig_office_status)
            return False

        if self.rs.refresh_status["last_notification"] == False:
            return True

        if self.last_nid == self.rs.last_nid and int (self.last_nid) != 0:
            logging.debug ("self.last_nid == self.rs.last_nid")
            self.status_changed (self.orig_office_status)
            return False

        if self.rs.refresh_status["current_status"] == True:
            self.rs.refresh_status["current_status"] = False
            self.current_status = self.rs.current_status
            self.refresh_status_changed (defs.CURRENT_STATUS_COMPLETED)

        if self.rs.refresh_status["notification"] == True and \
                self.rs.refresh_status["comments"] == True:
            self.rs.refresh_status["notification"] = False
            self.rs.refresh_status["comments"] = False
            self.notification = self.rs.notification
            self.status = self.rs.status
            self.refresh_status_changed (defs.NOTIFICATION_COMMENTS_COMPLETED)

        if self.rs.refresh_status["users_icon"] == True:
            self.rs.refresh_status["users_icon"] = False
            self.user_ids = self.rs.user_ids
            self.users = self.rs.users
            self.refresh_status_changed (defs.USERS_ICON_COMPLETED)

        if self.rs.refresh_status["apps_icon"] == True:
            self.rs.refresh_status["apps_icon"] = False
            self.app_ids = self.rs.app_ids
            self.applications = self.rs.applications
            self.refresh_status_changed (defs.APPS_ICON_COMPLETED)

        if self.rs.isAlive ():
            return True

        logging.debug ("completed")
        self.last_nid = self.rs.last_nid
        for k in self.rs.refresh_status:
            self.rs.refresh_status[k] = False

        path = self.local_data_dir + "/cache.pickle"
        utils.pickle_dump (self, path)

        self.status_changed (self.orig_office_status)
        return False

    def _refresh (self):
        logging.debug ("refresh start")
        if self.office_status != defs.IS_LOGIN:
            logging.info ("not IS_LOGIN")
            return True

        self.orig_office_status = self.office_status
        self.status_changed (defs.REFRESHING)
        logging.info ("notification_num: %s" % self.notification_num)
        self.rs = RefreshProcess \
            (self.notification_num, self.fb, self.uid, self.user_icons_dir, self.app_icons_dir, self.user_ids, self.last_nid)
        self.rs.start ()
        self.refresh_status_changed (defs.REFRESH_START)
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

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='s', out_signature='a{sv}')
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
    

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='s', out_signature='a{sv}')
    def get_application (self, app_id):
        if self.applications.has_key (app_id):
            return self.applications[app_id]
        return {}

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
        logging.info ("not find user: %d" % uid)
        usernames = [u['name'] for u in self.users]
        logging.info (usernames)
        return {}

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='s')
    def get_app_icons_dir (self):
        return self.app_icons_dir

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='s')
    def get_user_icons_dir (self):
        return self.user_icons_dir

    @dbus.service.method ("org.wallbox.PostOfficeInterface", in_signature='', out_signature='')
    def kill (self):
        sys.exit (0)

    @dbus.service.signal ("org.wallbox.PostOfficeInterface", signature='i')
    def status_changed (self, status):
        self.office_status = status
        logging.debug ("emit signal: %s" % status)

    @dbus.service.signal ("org.wallbox.PostOfficeInterface", signature='i')
    def refresh_status_changed (self, status):
        logging.info ("refresh emit signal: %s" % status)

    def prepare_directories (self):
        self.local_data_dir = \
            "%s/.local/share/wallbox" % os.getenv ("HOME")
        self.user_icons_dir = \
            "%s/user_icons" % self.local_data_dir
        self.app_icons_dir = \
            "%s/app_icons" % self.local_data_dir
        for d in [self.user_icons_dir, self.app_icons_dir]:
            if not os.path.exists (d):
                os.makedirs (d)

def main ():
    dbus.mainloop.glib.DBusGMainLoop (set_as_default=True)

    bus = dbus.SessionBus ()
    name = dbus.service.BusName ("org.wallbox.PostOfficeService", bus)
    obj = PostOffice (bus, "/org/wallbox/PostOfficeObject")

    mainloop = gobject.MainLoop ()
    mainloop.run ()

if __name__ == "__main__":
    main ()

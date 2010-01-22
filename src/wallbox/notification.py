#!/usr/bin/env python

import pygtk
pygtk.require ("2.0")
import gtk
import dbus
import dbus.mainloop.glib
import comment
import sys
import time
import gobject
import pkg_resources
import pango
import defs
import logging
import utils
import webbrowser
import os
import cgi

class Notification (gobject.GObject):

    def __init__ (self, offline=False):
        logging.basicConfig (level=defs.log_level)
        gobject.GObject.__init__(self)
        self.builder = gtk.Builder ()

        ui_file = pkg_resources.resource_filename \
                    (__name__, "data/notification.ui")

        self.builder.add_from_file (ui_file)
        self.builder.connect_signals (self, None)
        self.window = self.builder.get_object ("notification_window")
        self.window.connect ("configure-event", self.on_window_resize)
        self.entry_status = self.builder.get_object ("entry_status")
        self.scrolledwindow = self.builder.get_object ("scrolledwindow")
        self.comments = {}
        self.comment_handler_id = None
        self.progressbar_refresh = self.builder.get_object ("progressbar_refresh")

        gobject.signal_new \
            ("has-unread", Notification, gobject.SIGNAL_RUN_LAST, \
            gobject.TYPE_NONE, (gobject.TYPE_INT,))

        bus = dbus.SessionBus ()
        obj = bus.get_object ("org.wallbox.PostOfficeService", \
            "/org/wallbox/PostOfficeObject")

        self.office = dbus.Interface \
            (obj, "org.wallbox.PostOfficeInterface")

        self.office.connect_to_signal \
            ("status_changed", self.on_office_status_changed, \
            dbus_interface="org.wallbox.PostOfficeInterface")
        self.office.connect_to_signal \
            ("refresh_status_changed", self.on_refresh_status_changed, \
            dbus_interface="org.wallbox.PostOfficeInterface")

        self.init_view ()
        self.office.refresh ()
        self.on_office_status_changed (1)
        self.view_refresh ()

    def on_link_refresh_clicked (self, link, data=None):
        logging.debug ("on_link_refresh_clicked")
        self.office.refresh ()

    def on_button_share_clicked (self, button, data=None):
        logging.debug ("on_button_share_clicked")
        entry_status = self.builder.get_object ("entry_status")
        if entry_status != None and len (entry_status.get_text ()) > 0:
            self.office.post_status (entry_status.get_text ())
            current_status = self.builder.get_object ("label_current_status")
            current_status.set_text (entry_status.get_text())
            entry_status.set_text ("")

    def on_window_resize (self, widget, event, data=None):
        x = self.window.get_size ()[0]
        self.text_cell.set_property ("wrap-width", x - 50)

    def _refresh_animation (self):
        self.progressbar_refresh.pulse ()
        return True

    def refresh_notification_comments (self):
        nlist = self.office.get_notification_list ()
        liststore = self.builder.get_object ("list_notification")
        liststore.clear ()
        has_unread = False
        unread_num = 0
        for nid in nlist:
            entry = self.office.get_notification_entry (nid)
            text = None
            has_detail = False

            if len (entry['body_text']) == 0:
                text = entry['title_text']
            else:
                text = entry['body_text']

            text = cgi.escape (text)

            if entry['is_unread'] == True:
                has_unread = True
                text = "<b>%s</b>" % text
                unread_num += 1

            status = self.office.get_status_with_nid (int (entry['notification_id']))
            if len (status) != 0:
                has_detail = True
            liststore.append \
                ([entry['app_id'], text, has_detail, int(entry['notification_id'])])

        if has_unread == True:
            self.emit ("has-unread", unread_num)

    def refresh_users_icon (self):
        user = self.office.get_current_user ()
        pic_square = self.builder.get_object ("image_pic_square")
        user_icon_path = self.office.get_user_icons_dir ()

        if len (user) != 0:
            pic_square.set_from_file (user_icon_path + '/' + user['pic_square_local'])
        else:
            img_file = pkg_resources.resource_filename \
                        (__name__, "data/images/q_silhouette.gif")
            pic_square.set_from_file (img_file)

    def refresh_current_status (self):
        logging.debug ("CURRENT_STATUS_COMPLETED")
        label = self.builder.get_object ("label_current_status")
        status = self.office.get_current_status ()
        if len (status) != 0:
            label.set_text (status['message'])

    def on_refresh_status_changed (self, status):
        if status == defs.REFRESH_START:
            self.progressbar_refresh.set_text ("getting current status")
        if status == defs.CURRENT_STATUS_COMPLETED:
            self.progressbar_refresh.set_text ("getting notifications")
            self.refresh_current_status ()
        if status == defs.NOTIFICATION_COMMENTS_COMPLETED:
            self.progressbar_refresh.set_text ("downloading users icon")
            self.refresh_notification_comments ()
        if status == defs.USERS_ICON_COMPLETED:
            self.progressbar_refresh.set_text ("downloading apps icon")
            self.refresh_users_icon ()
        if status == defs.APPS_ICON_COMPLETED:
            self.progressbar_refresh.set_text ("")
            self.refresh_notification_comments ()

    def on_office_status_changed (self, status):
        link_refresh = self.builder.get_object ("link_refresh")
        if status == 1:
            #refresh
            link_refresh.set_label ("Refreshing....")
            self.progressbar_refresh.show ()
            self.refresh_handler_id = gobject.timeout_add (150, self._refresh_animation)
        else:
            self.view_refresh ()
            link_refresh.set_label ("Refresh")
            self.progressbar_refresh.hide ()
            gobject.source_remove (self.refresh_handler_id)
            self.refresh_handler_id = None
            (width, height) = self.builder.get_object ("aspectframe").size_request ()
            self.scrolledwindow.set_size_request (-1, utils.get_min_monitor_height() / 3 * 2)

    def delay_show_comment (self, post_id):
        self.comments[post_id].window.show ()
        self.comment_handler_id = None

    def on_notification_changed (self, sel):
        rect = self.treeview.get_allocation ()
        (origin_x, origin_y) = self.treeview.window.get_origin ()

        candidate_x = int (origin_x + rect.width - 10)
        candidate_y = int (self.cursor_y - 50)
        
        comment_width = comment.STATUS_WIDTH + comment.MAIN_ICON_SIZE
        if candidate_x > gtk.gdk.screen_width () - comment_width - 100:
            candidate_x = origin_x - comment_width - 20
        
        tlist, it = sel.get_selected()
        if it == None:
            return
        nid = tlist.get (it, 3)[0]
        entry = self.office.get_notification_entry (nid)
        logging.info ("herf: " + entry['href'])
        has_detail = tlist.get (it, 2)[0]
        logging.debug ("nid: %s" % nid)
        logging.debug ("has_detail: %s" % has_detail)

        if self.comment_handler_id != None:
            gobject.source_remove (self.comment_handler_id)
            self.comment_handler_id = None

        for k in self.comments:
            if self.comments[k].window.get_property ("visible") == True:
                self.comments[k].window.hide ()
        if has_detail:
            status = self.office.get_status_with_nid (nid)
            if status != {}:
                logging.debug ("status: %s" % status['message'])
                if not self.comments.has_key (status['post_id']):
                    self.comments[status['post_id']] = comment.Comment (status['post_id'])

                rect = self.comments[status['post_id']].window.get_allocation ()
                if candidate_y + rect.height > utils.get_min_monitor_height () - 30 :
                    logging.debug ("orig candidate_y: %d" % candidate_y)
                    candidate_y = utils.get_min_monitor_height () - rect.height - 30
                    logging.debug ("modify candidate_y: %d" % candidate_y)

                logging.debug ("x, y: (%d, %d)" % (candidate_x, candidate_y))
                self.comments[status['post_id']].window.move (candidate_x, candidate_y)
                self.comment_handler_id = \
                    gobject.timeout_add (300, self.delay_show_comment, status['post_id'])

    def on_row_activated (self, treeview, path, view_column, data=None):
        selection = treeview.get_selection ()
        tlist, it = selection.get_selected()
        nid = tlist.get (it, 3)[0]
        entry = self.office.get_notification_entry (nid)
        if len (entry['href']) > 0:
            webbrowser.open (entry['href'])
        else:
            webbrowser.open ("http://www.facebook.com/notifications.php")

    def on_mouse_motion (self, tree, event):
        (tree_x, tree_y) = tree.window.get_origin ()
        self.cursor_y = tree_y + event.y
        
    def init_view (self):
        self.treeview = self.builder.get_object ("treeview_notification")
        rect = self.treeview.get_allocation ()
        self.cursor_y = rect.y - 50
        self.treeview.connect ("motion_notify_event", self.on_mouse_motion)
        selection = self.treeview.get_selection ()
        selection.connect ("changed", self.on_notification_changed)
        self.column = gtk.TreeViewColumn ("icon")
        self.treeview.append_column (self.column)
        self.icon_cell = gtk.CellRendererPixbuf ()
        self.text_cell = gtk.CellRendererText ()
        self.arrow_cell = gtk.CellRendererText ()

        self.icon_cell.set_property ("yalign", 0.1)
        self.text_cell.set_property ("wrap-width", 150)
        self.text_cell.set_property ("yalign", 0.1)
        self.text_cell.set_property ("wrap-mode", pango.WRAP_WORD_CHAR)

        self.column.pack_start (self.icon_cell, False)
        self.column.pack_start (self.text_cell, True)
        self.column.pack_start (self.arrow_cell, False)

        self.column.set_cell_data_func (self.icon_cell, self.make_icon)
        self.column.set_attributes (self.text_cell, markup=1)
        self.column.set_cell_data_func (self.arrow_cell, self.make_arrow)

    def _get_empty_image (self):
        img_file = pkg_resources.resource_filename \
                    (__name__, "data/images/empty.gif")
        return gtk.image_new_from_file (img_file)

    def make_icon (self, column, cell, model, iter):
        app_id = model.get_value (iter, 0)
        app = self.office.get_application (int(app_id))
        icons_dir = self.office.get_app_icons_dir ()
        icon = None

        if len (app) == 0:
            icon = self._get_empty_image ()
        else:
            img_file = "%s/%s" % (icons_dir, app['icon_name'])
            if app['icon_name'] != "" and os.path.exists (img_file):
                icon = gtk.image_new_from_file (img_file)
            else:
                icon = self._get_empty_image ()

        try:    
            pixbuf = icon.get_pixbuf ()
        except:
            pixbuf = None
        cell.set_property ('pixbuf', pixbuf)

    def make_arrow (self, column, cell, model, iter):
        has_detail = model.get_value (iter, 2)
        arrow = None
        if has_detail == True:
            arrow = ">>"
        cell.set_property ('text', arrow)

    def view_refresh (self, data=None):
        self.refresh_current_status ()
        self.refresh_users_icon ()
        self.refresh_notification_comments ()

        keys = [k for k in self.comments]
        for k in keys:
            self.comments[k].window.destroy ()
            del self.comments[k]

        self.scrolledwindow.set_size_request (-1, utils.get_min_monitor_height () / 3 * 2)

    def refresh_error_cb (self, e):
        logging.debug (e)
        pass

if __name__ == "__main__":
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    offline = False
    if len (sys.argv) > 1 and sys.argv[1].strip() == "offline":
        offline = True
    else:
        offline = False

    n = Notification (offline)
    gtk.main ()


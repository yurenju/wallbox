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

class Notification (gobject.GObject):

    def __init__ (self, offline=False):
        gobject.GObject.__init__(self)
        self.comment = None
        self.builder = gtk.Builder ()

        ui_file = pkg_resources.resource_filename \
                    (__name__, "data/notification.ui")

        self.builder.add_from_file (ui_file)
        self.builder.connect_signals (self, None)
        self.window = self.builder.get_object ("notification_window")
        self.window.connect ("configure-event", self.on_window_resize)
        self.entry_status = self.builder.get_object ("entry_status")

        gobject.signal_new \
            ("has-unread", Notification, gobject.SIGNAL_RUN_LAST, \
            gobject.TYPE_NONE, ())

        bus = dbus.SessionBus ()
        obj = bus.get_object ("org.wallbox.PostOfficeService", \
            "/org/wallbox/PostOfficeObject")

        self.office = dbus.Interface \
            (obj, "org.wallbox.PostOfficeInterface")

        self.init_view ()

        self.office.refresh ()
        self.on_office_status_changed (1)
        self.refresh_reply_cb ()

        self.office.connect_to_signal \
            ("status_changed", self.on_office_status_changed, \
            dbus_interface="org.wallbox.PostOfficeInterface")

    def on_link_refresh_clicked (self, link, data=None):
        print "on_link_refresh_clicked"
        self.office.refresh ()

    def on_button_share_clicked (self, button, data=None):
        print "on_button_share_clicked"
        entry_status = self.builder.get_object ("entry_status")
        if entry_status != None and len (entry_status.get_text ()) > 0:
            self.office.post_status (entry_status.get_text ())
            current_status = self.builder.get_object ("label_current_status")
            current_status.set_text (entry_status.get_text())
            entry_status.set_text ("")

    def on_window_resize (self, widget, event, data=None):
        x = self.window.get_size ()[0]
        self.text_cell.set_property ("wrap-width", x - 50)

    def on_office_status_changed (self, status):
        link_refresh = self.builder.get_object ("link_refresh")
        if status == 1:
            #refresh
            link_refresh.set_label ("Refreshing....")
        else:
            self.refresh_reply_cb ()
            link_refresh.set_label ("Refresh")

    def on_notification_changed (self, sel):
        rect = self.treeview.get_allocation ()
        (origin_x, origin_y) = self.treeview.window.get_origin ()

        candidate_x = int (origin_x + rect.width - 10)
        candidate_y = int (self.cursor_y - 50)
        
        comment_width = comment.STATUS_WIDTH + comment.MAIN_ICON_SIZE
        if candidate_x > gtk.gdk.screen_width () - comment_width - 100:
            candidate_x = origin_x - comment_width - 20
        
        list, it=sel.get_selected()
        if it == None:
            return
        nid = list.get (it, 3)[0]
        has_detail = list.get (it, 2)[0]
        print "nid: %s" % nid
        print "has_detail: %s" % has_detail
        if has_detail:
            if self.comment != None:
                self.comment.window.destroy ()
            status = self.office.get_status_with_nid (nid)
            if status != {}:
                print "status: %s" % status['message']
                self.comment = comment.Comment (status['post_id'])
                self.comment.window.move (candidate_x, candidate_y)
        else:
            if self.comment != None:
                self.comment.window.destroy ()

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

        self.column.pack_start (self.icon_cell, False)
        self.column.pack_start (self.text_cell, True)
        self.column.pack_start (self.arrow_cell, False)

        self.column.set_cell_data_func (self.icon_cell, self.make_icon)
        self.column.set_attributes (self.text_cell, text=1)
        self.column.set_cell_data_func (self.arrow_cell, self.make_arrow)

    def make_icon (self, column, cell, model, iter):
        app_id = model.get_value (iter, 0)
        app = self.office.get_application (int(app_id))
        icons_dir = self.office.get_app_icons_dir ()
        icon = None
        if app['icon_name'] != "":
            icon = gtk.image_new_from_file ("%s/%s" % (icons_dir, app['icon_name']))
        else:
            icon = gtk.image_new_from_stock (gtk.STOCK_MISSING_IMAGE, 32)
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

    def refresh_reply_cb (self, data=None):
        label = self.builder.get_object ("label_current_status")
        status = self.office.get_current_status ()
        label.set_text (status['message'])
        user = self.office.get_current_user ()
        pic_square = self.builder.get_object ("image_pic_square")
        user_icon_path = self.office.get_user_icons_dir ()
        pic_square.set_from_file (user_icon_path + '/' + user['pic_square_local'])

        nlist = self.office.get_notification_list ()
        liststore = self.builder.get_object ("list_notification")
        liststore.clear ()
        has_unread = False
        for nid in nlist:
            entry = self.office.get_notification_entry (nid)
            text = None
            has_detail = False
            
            if entry['is_unread'] == True:
                has_unread = True

            if len (entry['body_text']) == 0:
                text = entry['title_text']
            else:
                text = entry['body_text']

            if int (entry['app_id']) == 19675640871:
                has_detail = True
            liststore.append \
                ([entry['app_id'], text, has_detail, int(entry['notification_id'])])

        if has_unread == True:
            self.emit ("has-unread")

    def refresh_error_cb (self, e):
        print e
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


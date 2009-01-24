#!/usr/bin/env python

# Copyright (C) 2008 Chris Dekter

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.


import pygtk
pygtk.require("2.0")
import sys, gtk, os.path, threading, gobject, time, pynotify, subprocess
from configobj import ConfigObj
import expansionservice, iomediator

ICON_FILE = "../../config/autokeyicon.svg"
NO_ICON_ARG = "notray"
EDITOR_OPTION = "editor"

def gthreaded(f):
    
    def wrapper(*args):
        gtk.gdk.threads_enter()
        #t = threading.Thread(target=f, args=args)
        #t.setDaemon(True)
        #t.start()
        f(*args)
        gtk.gdk.threads_leave()
        
    wrapper.__name__ = f.__name__
    wrapper.__dict__ = f.__dict__
    wrapper.__doc__ = f.__doc__
    return wrapper
    
class AutoKeyTrayIcon(gobject.GObject):

    __gsignals__ = { "show-notify" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                      (gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)) }    
    
    def __init__(self, icon=True):
        try:
            self.initialise(icon)
        except Exception, e:
            self.__showErrorDialog("Unable to start expansion service.\n" + str(e))
            sys.exit(1)
        
    def initialise(self, icon):
        gobject.GObject.__init__(self)
        pynotify.init("AutoKey")
        
        self.service = expansionservice.ExpansionService(self)
        
        if not icon:
            self.icon = None
        else:
            
            # Main Menu items
            self.enableMenuItem = gtk.CheckMenuItem("Enable expansions")
            #methodMenuItem = gtk.MenuItem("Expansion method")
            editMenuItem = gtk.ImageMenuItem("Edit abbreviations file")
            editMenuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_EDIT, gtk.ICON_SIZE_MENU))
            self.removeMenuItem = gtk.ImageMenuItem("Remove tray icon")
            self.removeMenuItem.set_image(gtk.image_new_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU))
            quitMenuItem = gtk.ImageMenuItem(gtk.STOCK_QUIT)
            aboutMenuItem = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
            
            # Sub-menu items
            #self.xlibMethodRadioItem = gtk.RadioMenuItem(None, iomediator.XLIB_INTERFACE)
            #self.pyAtspiMethodRadioItem = gtk.RadioMenuItem(self.xlibMethodRadioItem, iomediator.ATSPI_INTERFACE)
                
            self.ignoreToggle = False
            self.enableMenuItem.set_active(True)
                    
            # Menu signals
            self.enableMenuItem.connect("toggled", self.on_enable_toggled)
            self.removeMenuItem.connect("activate", self.on_remove_icon)
            quitMenuItem.connect("activate", self.on_destroy_and_exit)
            aboutMenuItem.connect("activate", self.on_show_about)
            editMenuItem.connect("activate", self.on_edit_config)
            
            # Construct sub menu
            #methodMenu = gtk.Menu()
            #methodMenu.append(self.xlibMethodRadioItem)
            #methodMenu.append(self.pyAtspiMethodRadioItem)
            #methodMenuItem.set_submenu(methodMenu)
            
            # Construct main menu
            self.menu = gtk.Menu()
            self.menu.append(self.enableMenuItem)
            #self.menu.append(methodMenuItem)
            self.menu.append(editMenuItem)
            self.menu.append(self.removeMenuItem)
            self.menu.append(quitMenuItem)
            self.menu.append(gtk.SeparatorMenuItem())
            self.menu.append(aboutMenuItem)
            self.menu.show_all()
            
            #self.icon = gtk.status_icon_new_from_stock(gtk.STOCK_INFO)
            self.icon = gtk.status_icon_new_from_file(ICON_FILE)
            self.icon.set_tooltip("AutoKey")
            self.icon.connect("popup_menu", self.on_popup_menu)
            
            self.connect("show-notify", self.on_show_notify)
        
            #if self.service.interfaceType == iomediator.XLIB_INTERFACE:
            #    self.xlibMethodRadioItem.set_active(True)
            #else:
            #    self.pyAtspiMethodRadioItem.set_active(True)
            # connect now that initial state has been set
            #self.xlibMethodRadioItem.connect("activate", self.on_method_changed)
            
        self.start_service()
    
    def start_service(self):
        try:
            self.service.start()
        except Exception, e:
            self.__showErrorDialog("Unable to start expansion service.\n" + str(e))
            if self.icon is not None:
                self.ignoreToggle = True
                self.enableMenuItem.set_active(False)
                self.removeMenuItem.set_sensitive(False)
                self.ignoreToggle = False
                        
        else:
            if self.icon is not None:
                self.removeMenuItem.set_sensitive(True)                        
    
    def stop_service(self):
        self.service.pause()
        if self.icon is not None:
            self.removeMenuItem.set_sensitive(False)
            
    def show_notify(self, message, isError=False, details=''):
        if isError:
            self.emit("show-notify", message, details, gtk.STOCK_DIALOG_ERROR)
        else:
            self.emit("show-notify", message, details, gtk.STOCK_DIALOG_INFO)
        
    def main(self):
        gtk.main()        
    
    # Signal Handlers ----
        
    def on_popup_menu(self, status_icon, button, activate_time, data=None):
        self.menu.popup(None, None, None, button, activate_time)
        
    def on_enable_toggled(self, widget, data=None):
        if self.ignoreToggle:
            self.ignoreToggle = False
        else:
            if self.enableMenuItem.active:
                self.start_service()
            else:
                self.stop_service()
            
    def on_remove_icon(self, widget, data=None):
        self.icon.set_visible(False)
        self.icon = None
                
    def on_destroy_and_exit(self, widget, data=None):
        self.service.shutdown()
        gtk.main_quit()
        
    def on_show_about(self, widget, data=None):        
        dlg = gtk.AboutDialog()
        dlg.set_name("AutoKey")
        dlg.set_comments("A text expansion/replacement utility for Linux and X11\nKeystrokes saved: "
                           + str(self.service.keystrokesSaved))
        dlg.set_version("0.40.3")
        p = gtk.gdk.pixbuf_new_from_file(ICON_FILE)
        dlg.set_logo(p)
        dlg.run()
        dlg.destroy()
        
    def on_edit_config(self, widget, data=None):
        config = ConfigObj(expansionservice.CONFIG_FILE, list_values=False)
        editor = config[expansionservice.CONFIG_SECTION][EDITOR_OPTION]
        subprocess.Popen([editor, expansionservice.CONFIG_FILE])
        
    #def on_method_changed(self, widget, data=None):
    #    if self.enableMenuItem.active:
    #        try:
    #            self.service.switch_method(self.__getSelectedMethod())
    #        except Exception, e:
    #            self.__showErrorDialog("Unable to switch expansion method.\n" + str(e))
    
    @gthreaded
    def on_show_notify(self, widget, message, details, iconName):
        n = pynotify.Notification("Autokey", message, iconName)
        n.set_urgency(pynotify.URGENCY_LOW)
        if self.icon is not None:
            n.attach_to_status_icon(self.icon)
        #if details != '':
        #    n.add_action("details", "Details", self.__notifyClicked, details)
        # This doesn't seem to work at all. Bug in pynotify???

        n.show()
                    
    # Utility methods ----
    
    def __notifyClicked(self, notification, action, details):
        dlg = gtk.MessageDialog(type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_OK,
                                 message_format=details)
        dlg.connect("close", lambda x: x.destroy())
        dlg.show()
                
    #def __getSelectedMethod(self):
    #    if self.xlibMethodRadioItem.active:
    #        return iomediator.XLIB_INTERFACE
    #    else:
    #        return iomediator.ATSPI_INTERFACE
        
    def __showErrorDialog(self, message):
        dlg = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK,
                                 message_format=message)
        dlg.run()
        dlg.destroy()

# End class AutoKeyTrayIcon

gobject.type_register(AutoKeyTrayIcon)

if __name__ == "__main__":
    showIcon = True
    if len(sys.argv) == 2:
        # received a positional argument
        showIcon = (sys.argv[1] == NO_ICON_ARG)
    
    a = AutoKeyTrayIcon(showIcon)
    gtk.gdk.threads_init()
    a.main()
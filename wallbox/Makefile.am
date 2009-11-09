
# primary file (executable python script) placed in /usr/bin
bin_SCRIPTS = wallbox

# Utility files
# create .pyc and .pyo (byte-compile) 
# and place files in /usr/lib/python<ver>/<pkg>/site-packages
python_PYTHON = wallbox_utils.py

desktopentry_DATA = wallbox.desktop
icon_DATA = wallbox32.png

#TBD: how to tell Python app where ${pkgdatadir} is?

#supporting files to place in /usr/share/wallbox
pkgdata_DATA = wallbox_data.conf 
##sample script to customize copy more data to /usr/share/wallbox
#install-data-hook:
#	$(MKDIR_P) ${pkgdatadir}
#	cp -R foo/* ${pkgdatadir}

# Replace @PKGDATADIR@ in script with path to pkgdatadir post installation:
install-exec-hook:
	sed -i "s|@PKGDATADIR@|${pkgdatadir}|g" \
		$(DESTDIR)$(bindir)/wallbox

CLEANFILES = *~ wallbox.desktop




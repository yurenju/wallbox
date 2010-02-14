SUBDIRS = wallbox

# primary file (executable python script) placed in /usr/bin
bin_SCRIPTS = wallbox-applet


# Replace @PKGDATADIR@ in script with path to pkgdatadir post installation:
install-exec-hook:
	sed -i "s|@PKGDATADIR@|${pkgdatadir}|g" \
		$(DESTDIR)$(bindir)/wallbox-applet





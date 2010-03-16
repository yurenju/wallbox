AC_PREREQ(2.61)
AC_CONFIG_MACRO_DIR([m4])
GNOME_COMMON_INIT


# package version number (not shared library version)
# odd micro numbers indicate in-progress development
# even micro numbers indicate released versions
m4_define(wallbox_version_major, 0)
m4_define(wallbox_version_minor, 1)
m4_define(wallbox_version_micro, 0)

m4_define([wallbox_version],
          [wallbox_version_major.wallbox_version_minor.wallbox_version_micro])
m4_define([wallbox_api_version],
          [wallbox_version_major.wallbox_version_minor])

#the name in AC_INIT is the project name and used in many
# configure variables.  (e.g. pkgdatadir == /usr/share/<name>)
AC_INIT(wallbox, wallbox_version)
AM_INIT_AUTOMAKE(wallbox, wallbox_version)

#Look for python version listed
#AM_PATH_PYTHON(version,action-if-found,action-if-not-found)
#e.g. AM_PATH_PYTHON([2.5.2],, [:])
AM_PATH_PYTHON([2.5.2])

# Checks for programs.
AC_PROG_LIBTOOL
AC_PROG_INSTALL

# Checks for libraries.

# Checks for typedefs, structures, & compiler characteristics

# Checks for library functions.
# AC_CHECK_FUNCS([memset])

# enable pkg-config
PKG_PROG_PKG_CONFIG

# Check for function availability
# AC_CHECK_FUNCS([memset])

# all libraries listed are associated with "WALLBOX" tag
#PKG_CHECK_MODULES(WALLBOX, glib-2.0)
#AC_SUBST(WALLBOX_CFLAGS)
#AC_SUBST(WALLBOX_LIBS)



# i18n
AC_SUBST(ACLOCAL_AMFLAGS, "$ACLOCAL_FLAGS -I m4")
GETTEXT_PACKAGE=wallbox
AC_SUBST(GETTEXT_PACKAGE)
AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE, "$GETTEXT_PACKAGE", [Gettext package])
AM_GLIB_GNU_GETTEXT
IT_PROG_INTLTOOL([0.37.1])

desktopentrydir=${datadir}/applications
AC_SUBST(desktopentrydir)

AS_AC_EXPAND(DATADIR, $datarootdir)
AC_SUBST(DATADIR)

AS_AC_EXPAND(PYEXECDIR, $pyexecdir)
AC_SUBST(PYEXECDIR)

AS_AC_EXPAND(WALLBOXDIR, $wallboxdir)
AC_SUBST(WALLBOXDIR)

AS_AC_EXPAND(LIBDIR, $libdir)
AC_SUBST(LIBDIR)

icondir=${datadir}/icons/hicolor/32x32/apps
AC_SUBST(icondir)

AC_CONFIG_FILES([
po/Makefile.in
])

# Output files
AC_OUTPUT([Makefile
src/Makefile
src/wallbox/Makefile
src/wallbox/defs.py
data/Makefile
data/images/Makefile
data/wallbox.desktop
])

echo ""
echo "   wallbox $VERSION"
echo "   ====================="
echo "   Documentation: ${enable_gtk_doc}"
echo ""
echo "   To build the project, run \"make\""
echo ""


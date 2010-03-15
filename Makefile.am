SUBDIRS = src data po
ACLOCAL_AMFLAGS = -I m4

DISTCHECK_CONFIGURE_FLAGS=

#include license since source is often part of python distribution
pkgdata_DATA = COPYING

DISTCLEANFILES =		\
	intltool-extract	\
	intltool-merge		\
	intltool-update

EXTRA_DIST = autogen.sh \
	intltool-extract.in	\
	intltool-merge.in	\
	intltool-update.in

CLEANFILES = *~

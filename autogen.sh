#!/bin/sh
[ -e config.cache ] && rm -f config.cache

#set -x
#intltoolize --force || exit 1
libtoolize --automake
gtkdocize || exit 1
aclocal
autoconf
automake -a
./configure $@
exit

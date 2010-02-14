#!/bin/sh
[ -e config.cache ] && rm -f config.cache

#set -x
#intltoolize --force || exit 1
libtoolize --automake

aclocal
autoconf
automake -a
./configure $@
exit

#!/bin/sh

# Include varnish defaults if available
if [ -f /etc/default/varnish ] ; then
        . /etc/default/varnish
fi

# Open files (usually 1024, which is way too small for varnish)
ulimit -n ${NFILES:-131072}

# Maxiumum locked memory size for shared memory log
ulimit -l ${MEMLOCK:-82000}

# If $DAEMON_OPTS is not set at all in /etc/default/varnish, use minimal useful
# defaults (Backend at localhost:8080, a common place to put a locally
# installed application server.)
DAEMON_OPTS=${DAEMON_OPTS:--b localhost}

/usr/sbin/varnishd -F ${DAEMON_OPTS}

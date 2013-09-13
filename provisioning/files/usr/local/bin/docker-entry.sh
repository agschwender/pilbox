#!/bin/sh

case "$1" in
    web)
        if [ ! -f /usr/bin/supervisord ]; then
            echo "Could not run web, see documentation for provisioning instructions"
            exit 0
        fi

        echo "Starting web..."
        /usr/bin/supervisord -n
        ;;
    ssh)
        echo "Starting sshd..."
        /usr/sbin/sshd -D
        ;;
    shell)
        /bin/bash
        ;;
    *)
        echo "Usage: "$1" {web|ssh|shell}"
        exit 1
esac

exit 0

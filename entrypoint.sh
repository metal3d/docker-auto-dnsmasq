#!/bin/sh

dnsmasq --no-daemon -p 53 &

exec $@


""" Record docker domain names in dnsmasq over NetworkManager

Licent: MIT
Author: Patrice Ferlet <metal3d@gmail.com>

This script is part of the docker-auto-dns project that requires
systemd service. It listens to docker events and records DNS entries
in a file that can read dnsmasq.

Each FQDN are prefixed by a dot to make it possible to respond to
subdomains.

The requirements are:
    - make NetworkManager using dnsmasq
    - configure dnsmasq to listen on docker0 ip address
    - setup docker service to use the dnsmasq interface ip
    - if systemd-resolved is used, add dnsmasq ip to the DNS list
    - create firewall rules to allow any docker sub-network to contact
      docker0 interface with DNS service (port 53)

The entire installation is described in the project repository
that you can visit here:
- https://github.com/metal3d/docker-auto-dnsmasq
"""

import os
import re
import signal
import sys
import typing

import docker
from docker.types.daemon import CancellableStream
from requests.exceptions import StreamConsumedError
from systemd import journal

cli = docker.from_env()
TEST = False
DNS_FILE = "/etc/NetworkManager/dnsmasq.d/docker-auto-dns.conf"
RESOLVE_CONF = "/etc/systemd/resolved.conf.d/docker-auto-dns.conf"
DOCKER0 = "docker0"


def get_ip_of_interface(interface) -> str:
    """Get the ip address of an interface"""
    cmd = "ip addr show dev %s | grep -oP '(?<=inet ).*(?=/)' | head -1" % interface
    return os.popen(cmd).read().strip()


def configure_docker_dnsmasq():
    """Configure resolved to hit docker0 interface"""
    # get docker0 ip
    docker0_ip = get_ip_of_interface(DOCKER0)
    journal.send("Configure docker to use dnsmasq ip %s" % docker0_ip)

    # configure /etc/resolv.conf.d/docker-auto-dns.conf
    # to use docker0 ip
    # [Resolve]
    # DNS=docker0 interface ip
    with open(RESOLVE_CONF, "w", encoding="utf-8") as conf:
        conf.write("[Resolve]\n")
        conf.write("DNS=%s\n" % docker0_ip)
        # conf.write("DNS=127.0.0.1")

    # reload services
    os.system("systemctl restart systemd-resolved")
    os.system("systemd-resolve --flush-caches")


def drop_dns_conf():
    """Remove docker dns configuration"""
    if os.path.exists(RESOLVE_CONF):
        os.unlink("/etc/systemd/resolved.conf.d/docker-auto-dns.conf")
    journal.send("Reload NetworkManager and Resolved")
    os.system("systemctl restart systemd-resolved")
    journal.send("... Resolved")
    os.system("systemd-resolve --flush-caches")
    journal.send("... Cache flushed")
    journal.send("Reload done")


def write_dns(domains: typing.List[str], resolvename: bool = False):
    """Write domain names in NetworkManager dnsmasq configuration"""

    dnsconf = []
    for container in cli.containers.list():
        if container is None:
            continue
        if container.attrs is None:
            continue
        dnsconf += manage_container(domains, container, resolvename)

    if not TEST:
        journal.send("Reload DNS records for Docker containers...")
        # open the docker-auto-dns.conf file to add addresses
        with open(DNS_FILE, "w") as conf:
            conf.write("\n".join(dnsconf))

        # TODO: check if there is no better solution
        # reload to refresh dnsmasq names
        os.system("systemd-resolve --flush-caches")
        os.system("systemctl reload NetworkManager")
        journal.send("DNS refreshed")
    else:
        # only print results in TEST mode
        print("-" * 80)
        print("\n".join(dnsconf))


def manage_container(domains, container, resolvename) -> typing.List[str]:
    """Manage a container"""

    # the records
    domain_records = {}

    container_id = container.attrs["Id"]
    hostname = container.attrs["Config"]["Hostname"]
    domain = container.attrs["Config"].get("Domainname")

    # complete the name if needed
    if len(domain) > 0:
        hostname += "." + domain

    # get container name
    name = container.attrs["Name"][1:]

    # now read network settings
    settings = container.attrs["NetworkSettings"]
    for netname, network in settings.get("Networks", {}).items():
        ipaddress = network.get("IPAddress", False)
        if not ipaddress or ipaddress == "":
            continue

        record = domain_records.get(ipaddress, [])
        # record the container name DOT network
        # eg. container is named "foo", and network is "demo",
        #     so create "foo.demo" domain name
        # (avoiding default network named "bridge")
        if netname != "bridge":
            record.append(".%s.%s" % (name, netname))
        # if user allow to resolve the container name without
        # domain, so just accept...
        elif resolvename:
            if os.environ.get("DOCKER_FORCE_DOMAIN", False):
                record.append(".%s.%s" % (name, os.environ["DOCKER_FORCE_DOMAIN"]))
            else:
                record.append(name)

        # check if the hostname if allowed and add it on
        # dnsmasq configuration.
        for domain in domains:
            if (
                domain in hostname
                and hostname not in container_id
                and domain != os.environ.get("DOCKER_FORCE_DOMAIN")
            ):
                record.append("." + hostname)

        # manage traefik hostname
        _ = [record.append("." + domain) for domain in get_traefik_domains(container)]

        # do not append record if it's empty
        if len(record) > 0:
            domain_records[ipaddress] = record

    # now, create the file content
    dnsconf = []
    for ipaddress, hosts in domain_records.items():
        if not TEST:
            journal.send(
                "New host(s) %s on address %s "
                "to add on dnsmasq" % (",".join(hosts), ipaddress)
            )

        dnsconf.append("address=/%s/%s" % ("/".join(hosts), ipaddress))

    return dnsconf


def get_traefik_domains(container) -> typing.List[str]:
    """Get traefik domains from container labels"""
    labels = container.attrs["Config"].get("Labels", {})
    traefik_domains = []
    for key, value in labels.items():
        if "traefik.http.routers" not in key:
            continue
        # Get "Host(s)" value
        traefik_domains += [
            s.replace("`", "")
            for s in re.findall(r"Host\((.+?)\)", value)[0].split(",")
        ]
    return traefik_domains


def run():
    """Run service"""

    configure_docker_dnsmasq()

    tld = os.environ.get("DOCKER_DOMAIN", "")
    resolve_name = os.environ.get("DOCKER_RESOLVE_NAME", "false") == "true"
    domains = tld.split(",")

    # make the first pass
    write_dns(domains, resolve_name)

    # then for each docker event
    events = cli.events(decode=True)

    # unlit SIGTERM happens...
    signal.signal(signal.SIGTERM, stop)

    try:
        for event in events:
            if "status" not in event:
                continue
            status = event["status"]
            if status in ("die", "start"):
                write_dns(domains, resolve_name)
    except KeyboardInterrupt:
        stop(15, None)


def stop(signum, frame):
    """Stop service"""

    journal.send("Stop service... Signal %d, frame %s" % (signum, frame))
    drop_dns_conf()
    sys.exit(0)


if __name__ == "__main__":
    run()

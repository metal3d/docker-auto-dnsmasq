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
import typing

import docker
from systemd import journal

cli = docker.from_env()
TEST = False
DNS_FILE = "/etc/NetworkManager/dnsmasq.d/docker-auto-dns.conf"


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
            record.append(name)

        # check if the hostname if allowed and add it on
        # dnsmasq configuration.
        for domain in domains:
            if domain in hostname and hostname not in container_id:
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
    tld = os.environ.get("DOCKER_DOMAIN", "")
    resolve_name = os.environ.get("DOCKER_RESOLVE_NAME", "false") == "true"
    domains = tld.split(",")

    # make the first pass
    write_dns(domains, resolve_name)

    # then for each docker event
    for event in cli.events(decode=True):
        status = event.get("status", False)
        if status in ("die", "start"):
            write_dns(domains, resolve_name)


if __name__ == "__main__":
    run()

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
import docker

cli = docker.from_env()
TEST = False
DNS_FILE = '/etc/dnsmasq.d/docker-auto-dns.conf'


def write_dns(domains=[], resolvename=False):
    """ Write domain names in NetworkManager dnsmasq configuration """

    dnsconf = []
    for c in cli.containers.list():
        # the records
        domain_records = {}

        container_id = c.attrs['Id']
        hostname = c.attrs['Config']['Hostname']
        domain = c.attrs['Config'].get('Domainname')

        # complete the name if needed
        if len(domain) > 0:
            hostname += '.' + domain

        # get container name
        name = c.attrs['Name'][1:]

        # now read network settings
        settings = c.attrs['NetworkSettings']
        for netname, network in settings.get('Networks', {}).items():
            ip = network.get('IPAddress', False)
            if not ip or ip == "":
                continue

            record = domain_records.get(ip, [])
            # record the container name DOT network
            # eg. container is named "foo", and network is "demo",
            #     so create "foo.demo" domain name
            # (avoiding default network named "bridge")
            if netname != "bridge":
                record.append('.%s.%s' % (name, netname))
            # if user allow to resolve the container name without
            # domain, so just accept...
            elif resolvename:
                record.append(name)

            # check if the hostname if allowed and add it on
            # dnsmasq configuration.
            for domain in domains:
                if domain in hostname and hostname not in container_id:
                    record.append('.' + hostname)

            # do not append record if it's empty
            if len(record) > 0:
                domain_records[ip] = record

        # now, create the file content
        for ip, hosts in domain_records.items():
            print('address=/%s/%s' % ("/".join(hosts), ip))
            dnsconf.append('address=/%s/%s' % ("/".join(hosts), ip))

    if not TEST:
        # open the docker-auto-dns.conf file to add addresses
        with open(DNS_FILE, 'w') as conf:
            conf.write("\n".join(dnsconf))

    else:
        # only print results in TEST mode
        print("-" * 80)
        print("\n".join(dnsconf))


if __name__ == '__main__':

    tld = os.environ.get('DOCKER_DOMAIN', '')
    resolve_name = os.environ.get('DOCKER_RESOLVE_NAME', 'false')
    resolve_name = True if resolve_name == 'true' else False
    domains = tld.split(',')

    # make the first pass
    write_dns(domains, resolve_name)

    # then for each docker event
    for e in cli.events(decode=True):
        status = e.get('status', False)
        if status in ('die', 'start'):
            write_dns(domains, resolve_name)

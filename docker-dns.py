import docker
import os

cli = docker.from_env()


def write_dns(domains=[], resolvename=False):
    """ Write domain names in NetworkManager dnsmasq configuration """

    dnsconf = ''
    for c in cli.containers.list():
        cid = c.attrs['Id']

        hostname = c.attrs['Config']['Hostname']
        domain = c.attrs['Config'].get('Domainname')
        if len(domain) > 0:
            hostname += '.' + domain

        name = c.attrs['Name'][1:]

        settings = c.attrs['NetworkSettings']

        # get standard ip
        ip = settings.get('IPAddress', False)

        ips = []
        if ip:
            ips.append(ip)

        # get ip from networks
        for _, network in settings.get('Networks', {}).items():
            ip = network.get('IPAddress', False)
            if ip:
                ips.append(ip)

        # now, get hostname
        hname = []
        for d in domains:
            if cid in hostname:
                # we don't want ids in dnsmasq, only the name
                continue

            if d in hostname:
                print("add container host %s %s in dnsmasq file" % (
                    hostname, ", ".join(ips)))
                hname.append('.' + hostname)

        # make ip uniques
        ips = list(set(ips))

        if resolvename and name:
            print("add container name %s %s in dnsmasq file" % (
                name, ", ".join(ips)))
            hname.append(name)

        if len(hname) > 0 and len(ips) > 0:
            for ip in ips:
                dnsconf += 'address=/%s/%s\n' % ("/".join(hname), ip)

    # open the docker.conf file to add addresses
    with open('/etc/NetworkManager/dnsmasq.d/docker.conf', 'w') as conf:
        conf.write(dnsconf)

    # reload to refresh dnsmasq names
    os.system('systemctl reload NetworkManager')


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

import docker
import os

cli = docker.from_env()


def write_dns(domains=[]):
    """ Write domain names in NetworkManager dnsmasq configuration """

    dnsconf = ''
    for c in cli.containers.list():
        hostname = c.attrs['Config']['Hostname']
        ip = c.attrs['NetworkSettings']['IPAddress']
        for d in domains:
            if d in hostname:
                print("add %s %s in dnsmasq file" % (hostname, ip))
                dnsconf += 'address=/%s/%s\n' % (hostname, ip)

    # open the docker.conf file to add addresses
    with open('/etc/NetworkManager/dnsmasq.d/docker.conf', 'w') as conf:
        conf.write(dnsconf)

    # reload to refresh dnsmasq names
    os.system('systemctl reload NetworkManager')


if __name__ == '__main__':

    tld = os.environ.get('DOCKER_DOMAIN', '')
    domains = tld.split(',')

    # make the first pass
    write_dns(domains)

    # then for each docker event
    for e in cli.events(decode=True):
        status = e.get('status', False)
        if status in ('die', 'start'):
            write_dns(domains)

import docker
import json
import os

cli = docker.from_env()
tld = os.environ.get('DOCKER_DOMAIN', '.docker')


def write_dns():
    dnsconf = ''
    for c in cli.containers.list():
        hostname = c.attrs['Config']['Hostname']
        ip = c.attrs['NetworkSettings']['IPAddress']
        if tld in hostname:
            print("add %s %s in dnsmasq file" % (hostname, ip))
            dnsconf += 'address=/%s/%s\n' % (hostname, ip)

    with open('/etc/NetworkManager/dnsmasq.d/docker.conf', 'w') as conf:
        conf.write(dnsconf)

    os.system('systemctl reload NetworkManager')


if __name__ == '__main__':

    # all once
    write_dns()

    # then for each docker event
    for e in cli.events():
        e = json.loads(e)
        status = e.get('status', False)
        if status in ('die', 'start'):
            write_dns()

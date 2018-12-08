import json
import subprocess
import re
import os
import sys

INTERFACE = 'docker0'
DAEMONFILE = '/etc/docker/daemon.json'
NM_DOCKER_CONFIG = '/etc/NetworkManager/dnsmasq.d/docker-bridge.conf'

CIDR = os.environ.get('CIDR', '172.0.0.0/8')

# find docker0 ip
ipa = subprocess.run(['ip', 'a', 'show', INTERFACE], stdout=subprocess.PIPE)
ipa = ipa.stdout.decode()
ipa = re.findall(r'inet ([0-9\.]+)', ipa)

assert len(ipa) > 0

ipa = ipa[0]

# load daemon.json file
daemon = {}
if os.path.exists(DAEMONFILE):
    try:
        with open(DAEMONFILE, 'r') as d:
            daemon = json.load(d)
    except Exception:
        print(
            '%s file seems to be invalid, '
            'please take a look and retry later' % DAEMONFILE
        )
        os.exit(1)
else:
    print('docker daemon configuration not found, we will create it')


# find dns configuration
dns = daemon.get('dns', [])

if "remove" in sys.argv:
    # if we want to remove dns,
    # so we remove the entry in dns list
    if ipa in dns:
        del(dns[dns.index(ipa)])

    # remove the NetworkManager file
    # that activates dnsmasq on docker0 interface
    try:
        os.unlink(NM_DOCKER_CONFIG)
    except FileNotFoundError:
        # already removed
        pass

else:
    # prepend dnsmasq interface
    dns = [ipa] + dns if ipa not in dns else dns

    # write configuration to NetworkManager
    # to listen on docker0
    with open(NM_DOCKER_CONFIG, 'w') as nm:
        conf = 'listen-address=%s' % ipa
        nm.write(conf)

# replace dns list
if len(dns) > 0:
    daemon['dns'] = dns
else:
    # no dns, remove the option
    del(daemon['dns'])

# write configuration
with open(DAEMONFILE, 'w') as d:
    json.dump(daemon, d, indent='    ')

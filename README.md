# Docker container DNS entry with NetworkManager and dnsmasq

This is a simple service that will add DNS entries corresponding to your containers hostnames. 
It creates a file in your NetworkManager configuration and manipulate the content when docker start or stop containers.

TL;DR It create DNS entries to contact your containers:
```
docker run --hostname="webapp.docker" nginx:alpine

# Then go to http://webapp.docker and voilà !
```

And to make it great, it also makes containers able to hit that DNS entries internally, whatever the "network" it is running.

Note: filtering ".docker" domains (or any others you've configured, see last section) is a wanted behavior. It's useless to resolve the entire docker containers names. So, you only need to add "hostname" option (or "hostname" in docker-compose files) to allow the containers to have a **local** domain name. Future versions can change to use option to choose the behavior.

To make it working, you need to configure NetworkManager to use dnsmasq and add a special configuration to let it listening docker interface. And afterward, you may install our docker-dns service.

## Requirements

- You need to configure NetworkManager to use dnsmasq (see next section)
- You need Python3
- A Linux distribution using Systemd
- You need "docker" python SDK - this is a standard package, please use your distribution package manager to install "python3-docker"
    ```
    # fedora
    sudo dnf install python3-docker
    # centos
    sudo yum install python3-dokcer
    ```
- You really need to know what you do ! Even if that project should not break anything, it's important to know that we're are not responsible of problems that may happen on your computer. Keep in mind that we will add a service, and we will need to open one port. So, check twice what you do.


## NetworkManager configuration

Open `/etc/NetworkManager/NetworkManager.conf` file and add dns option in the `[main]` section:

```ini
[main]
...
dns=dnsmasq
```

That enables dnsmasq resolution with NetworkManager. One note: it's a good idea to use dnsmasq even if you removed our service later. Dnsmasq is a really nice service.

Now, restart NetworkManager and make some checks:

```bash
$ sudo systemctl restart NetworkManager

# check if 127.0.0.1 is responding
# eg. ping with ipv4 on google server
# and check if it's ok
$ ping -4 -c1 google.com

# dig can confirm that 127.0.0.1 is the DNS server
$ dig google.com | grep SERVER
;; SERVER: 127.0.0.1#53(127.0.0.1)
```

That doesn't work ? you want to abandon ? Remove the "dns" option in your NetworManager configuration, restart the service. But you will not be able to make our docker-dns service working.

## Make Docker interface using dnsmasq

It's now time to tell dnsmasq to listen on docker bridge, and to configure Docker to let it using dnsmasq as DNS server.

Open `/etc/NetworkManager/dnsmasq.d/docker-bridge` file (create it) and put the content:

```
listen-address=172.17.0.1
```

**Of course, replace 172.17.0.1 by your own `docker0` ip address.**
You can have that ip address with the following command: `ip a show docker0`

Then, we need to tell Docker to use that interface as DNS server. 
Simply add dns entry in `/etc/docker/daemon.json` (create the file if it doesn't exist):

```json
{
	"dns": ["172.17.0.1"]
}
```

One more time... use your docker0 address if it's not the same that mine.

Then, restart NetworkManager and docker:

```bash
systemctl restart NetworkManager
systemctl restart docker
```

**Firewall changes can be needed**

Now, it's possible that you may need to add some rules in your firewall configuration to allow incoming connection on DNS service for docker0 interface. 
If you're using firewalld (CentOS, Fedora...), there are several possibilities.

**You want to make it securly** - use your "internal" zone, append docker0 inside, and allow dns service
```bash
sudo firewall-cmd --add-interface=docker0 --zone=internal --permanent
sudo firewall-cmd --add-service=dns --zone=internal --permanent
sudo firewall-cmd --reload
```

**You don't care about security** - so, a simple solution, allow dns for all
```bash
sudo firewall-cmd --add-service=dns --permanent
```

Others can use their own iptables rules or firewall tools.


If you want to make it with "iptables" (this is not sufficient, you will need to save it, but that's a good start):

```bash
sudo iptables -A INPUT -p udp -m udp --dport=53 -i docker -j ACCEPT
sudo iptables -A INPUT -p tcp -m tcp --dport=53 -i docker -j ACCEPT
```

## Test Docker with dnsmasq

Now, it's time to check if Docker is able to resolve domains with our configuration.

```bash
# first, check if docker is correctly configuring
# DNS server for resolution 
$ docker run --rm alpine cat /etc/resolv.conf
nameserver 172.17.0.1

## RIGHT !

# Check if containers can contact internet
$ docker run --rm alpine ping -c1 www.google.com
```

That's fine.


## Finally Install the service

**Do that only if previous configuration is OK**, if not, retry...

Clone that repository, and then:

```bash
sudo make install activate
```

What does the Makefile is:

- copy the python script at `/usr/local/libexec/docker-dns.py`
- copy the service in `/etc/systemd/system/docker-dns.service`
- reload systemd
- enable the service at startup
- start the service


Now, you should be able to make tests:

```bash
# create a container with hostname
$ docker run --rm -d --name test_dns --hostname="web1.docker" nginx:alpine

# you can now navigate to web1.docker

# remove the container
$ docker stop test_dns
$ docker rm test_dns

# now, web1.docker should not be resolved
```

If everything is OK for you, congrats !


## Configuration

At this time, the service only create DNS entry for ".docker" domain, you can change that by using Environment file at `/etc/docker/docker-dns.conf` (create it) containing:

```
DOCKER_DOMAIN=.other.domain
```

Note: yes, you must put a dot as first letter.

Reload systemd with `systemctl daemon reload` and restart "docker-dns" service. That's all !


## Uninstall

You can remove the service with:

```bash
sudo make uninstall
```

It removes the python script and service. Also, the service is disabled before to be removed. Take a look on the Makefile, it's not so complicated.


## Future

There are several things I want to do, if you want to help, you're welcome:

- [ ] Avoid reloading NetworkManager to refresh DNS entries, but how ?
- [ ] Journalctl is not showing my logs... why ?
- [ ] Check for docker events is not "sure", I probably missed good practices
- [ ] Wizzard to configure NetworkManager, docker and the service
- [ ] Give me ideas...



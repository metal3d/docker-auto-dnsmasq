# Docker container DNS entry with NetworkManager and dnsmasq

This is a simple service that will add DNS entry for containers. It create a file in your NetworkManager configuration and manipulate the content when docker start or stop containers.

And to make it great, it also make containers able to hit that dns entries, whatever the "network" it is running.

Note: filtering ".docker" domain (or any others you've configured, see last section) is a wanted behavior. It's not useful to make domains with "name.docker" for containers we don't want to serve with domain name. So, you only need to add "hostname" option (or "hotname" in docker-compose files) to allow the container to have a **local** domain name. Future versions can change to use option to choose the behavior.

To make it working, you need to configure NetworkManager to use dnsmasq and add a special configuration to let it listen docker interface.

## NetworkManager configuration

Open `/etc/NetworkManager/dnsmasq.d/docker-bridge` file (create it) and put the content:

```
listen-address=172.17.0.1
```

**Of course, change it with your own `docker0` ip address.**
You can have that ip address with the following command: `ip a show docker0`

Open `/etc/NetworkManager/NetworkManager.conf` file and add dns option in the `[main]` section:

```ini
[main]
...
dns=dnsmasq
```

That enable dnsmasq resolution. Now, restart NetworkManager and make some checks:

```bash
$ sudo systemctl restart NetworkManager
$ sudo netstat -taupen | grep 53
# ... you MUST see 172.17.0.1
```

Now, the problem is that you may need to add some rule in firewall to allow incoming connection on DNS service for docker0 interface. 
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

## Configure docker

Simply add dns entry in `/etc/docker/daemon.json` (create the file if it doesn't exist):

```json
{
	"dns": ["172.17.0.1"]
}
```

One more time, change it using the correct docker0 ip address.


## Install the service

Clone that repository, and then:

```
make install activate
```

What does the Makefile is:

- copy the python script at `/usr/local/libexec/docker-dns.py`
- copy the service in `/etc/systemd/system/docker-dns.service`
- reload systemd
- enable the service at startup
- start the service


Now, you should be able to make tests:

```bash
# check if containers can contact internet
$ docker run --rm alpine ping -c1 www.google.com

# create a container with hostname
docker run --rm -d --name test_dns --hostname="web1.docker" nginx:alpine

# you can now navigate to web1.docker

# remove the container
docker stop test_dns
docker rm test_dns

# now, web1.docker should not be resolved
```

If everything is OK for you, congrats !


## Configuration

At this time, the service only create DNS entry for ".docker" domain, you can change that using Environment file that you can put at `/etc/docker/docker-dns.conf` containing:

```
DOCKER_DOMAIN=.other.domain
```

Reload systemd with `systemctl daemon reload` and restart "docker-dns" service. That's all !

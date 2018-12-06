# Docker container DNS entry with NetworkManager and dnsmasq

This is a simple service that will add DNS entries corresponding to your containers hostnames. 
It creates a file in your NetworkManager configuration and manipulate the content when docker start or stop containers.

TL;DR It create DNS entries to contact your containers:

```
docker run --hostname="webapp.docker" nginx:alpine

# Then go to http://webapp.docker and voilà !
```

And to make it great, it also makes containers able to hit that DNS entries from "default" docker network.

Docker-dns service is also able to filter hostnames to avoid DNS resolution to other containers names if the container is not in a "docker network".

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

# Automatic Installation

The provided makefile can make the full required installation. There are options to affine your needs.

## The basic and working installation

```bash
sudo make install
```

Thats configure NetworkManager to use dnsmasq, and install "docker-dns" service that registers domains.

This simple installation provides DNS resolution to you host only, docker containers continue to use the internal DNS in "networks"

Note: the service will filter the default domain name ".docker", any others domains set to the containers will not be resolved on host. If you want to filter others domains, or to deactivate filtering, please use the `DOMAIN`option (see below) or change the `/etc/docker/docker-dns.conf`file.

## Install with specific domain filters

If you want to filter others domains than ".docker", you may give the `DOMAINS` option to specify comma separated domains names:

```bash
sudo make install DOMAINS=".docker,.dck,.foo"
```

If you want to not filter domains, you can set the `DOMAIN`value as empty string - note that the entire docker containers will add DNS entry with their hostname and name.

```bash
sudo make install DOMAINS=""
```

You can alos change the filtering in `/etc/docker/docker-dns.conf`file and restart the service.

## Let docker using dnsmasq

It's possible to share dnsmasq resolution to docker containers. That way, you can add specific domains in your dnsmasq configuration that docker containers can use.

Also, it activate the resolution between containers that are not in the same "docker network". To make it working:

```bash
sudo make install USE_DNSMASQ_IN_DOCKER=true
```

**Warning** this configuration is a bit "strong". It does the following action:

- bind docker0 interface address in dnsmasq configuration in NetworkManager

- add the address in the daemon.json file (your own configuration will ne change, it only add the dns address)

For secured systems, you will need to change iptables rules to let docker0 interface accepting dns requests. If you're using firewalld (CentOS, Fedora...), there are several possibilities.

**You want to make it securly** - use your "internal" zone, append docker0 inside, and allow dns service

```bash
sudo firewall-cmd --add-interface=docker0 --zone=internal --permanent
sudo firewall-cmd --add-service=dns --zone=internal --permanent
sudo firewall-cmd --reload
```

**You don't care about security** - so, a simple solution, allow dns for all

```bash
sudo firewall-cmd --add-service=dns --permanent
sudo firewall-cmd --reload
```

Others can use their own iptables rules or firewall tools.

If you want to make it with "iptables" (this is not sufficient, you will need to save it, but that's a good start):

```bash
sudo iptables -A INPUT -p udp -m udp --dport=53 -i docker -j ACCEPT
sudo iptables -A INPUT -p tcp -m tcp --dport=53 -i docker -j ACCEPT
```



# Test the installation

If you've successfully installed docker-dns, you can now try if it works.

## Test NetworkManager

First, check if NetworkManager uses dnsmasq and didn't break internet connection, DNS resolution, and so on...

```bash
# check if 127.0.0.1 is resolving domains
# eg. ping with ipv4 on google server
# and check if it's ok
$ ping -4 -c1 google.com

# dig can confirm that 127.0.0.1 is the DNS server
$ dig google.com | grep SERVER
;; SERVER: 127.0.0.1#53(127.0.0.1)
```

If it breaks, either you can search what's wrong, or uninstall the installation by using `sudo make ininstall`- everything should be back to the normal.

## Test Docker with dnsmasq

To do if you used `USE_DNSMASQ_IN_DOCKER=true` - that have configured docker to resolve names with the hosts dnsmasq.

Check if Docker is able to resolve domains with our configuration.

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

## Finally test the service

If everything is OK, you can now create containers with specific hostname and try to resolve the name.

```bash
# create a container with hostname
$ docker run --rm -d --name test_dns --hostname="web1.docker" nginx:alpine
```

Then navigate to http://web1.docker - you shoud see the nginx default page.



If you used `USE_DNSMASQ_IN_DOCKER`option, so you can try to create a second container and try to resolve the previous domain:

```bash
$ docker run --rm alpine ping -c1 web1.docker
```

Finally, you can stop the previous container.

```bash
# you can now navigate to web1.docker
# remove the container
$ docker stop test_dns
```

Then, now that the container is stopped (and removed because we use `--rm` option), the resolution shoud disapear.



## Configuration

At this time, the service only create DNS entry for ".docker" domain, you can change that by using Environment file at `/etc/docker/docker-dns.conf` (create it) containing:

```
DOCKER_DOMAIN=.other.domain
```

Note: yes, you must put a dot as first letter.

Reload systemd and restart the service:

```bash
systemctl daemon reload
systemctl restart docker-dns
```

And now the new domains are resolved, even if you started docker containers before the configuration change.

## Uninstall

You can remove the service with:

```bash
sudo make uninstall
```

It removes NetworkManager dnsmasq configuration, stop the docker-dns service and removes it.

If you used `USE_DNSMASQ_IN_DOCKER`at installation step, so the Makefile also removes the DNS entry from `daemon.json` file, and the "docker-bridge" configuration.

Everything should now be back to the normal.

# Difference with docker-listen ?

I already used docker-listen years ago. That works, yes.

There is not so many differences, I just prefer the way I manage dns entries, how I can activate the domain resolution from docker and how the script for service is "simple".

I don't want to let you thinking that I do better than others. Maybe you want to use docker-listen, maybe you prefer my service. That's up to you.

# Give me a hand

You probably can help me to enchance the project, or maybe you found a bug. Open an issue, make pull-requests, give me ideas... I'm open to discuss.

# Future

There are several things I want to do, if you want to help, you're welcome:

- [ ] Avoid reloading NetworkManager to refresh DNS entries, but how ?
- [ ] Journalctl is not showing my logs... why ?
- [ ] Check for docker events is not "sure", I probably missed good practices
- [x] Wizzard to configure NetworkManager, docker and the service 
- [ ] Give me ideas...

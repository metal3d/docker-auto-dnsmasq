# Docker container DNS entry with NetworkManager and dnsmasq

This is a simple service that will add DNS entries corresponding to your containers hostnames. 
It creates a file in your NetworkManager configuration and manipulate the content when docker start or stop containers.

TL;DR It creates DNS entries to contact your containers:

```
docker run --hostname="webapp.docker" nginx:alpine
# Then go to http://webapp.docker and voilà !

docker run --name="foo" nginx:alpine
# and go to http://foo also

# and more...
```

And to make it great, it also makes containers able to hit that DNS entries from "default" docker network.

Docker-dns service is also able to filter hostnames to avoid DNS resolution to other containers names if the container is not in a "docker network".

**For Ubuntu users**, and all others who's using **systemd-resolved**:
This branch is a test that is configuring systemd-resolved to use dnsmasq as secondary DNS server. For now, it's working but there is a "little" problem: name resolution is not quickly refreshed and you may need to wait several seconds (sometimes more than 30s) to be able to resolve names. I don't know why and I will make some tests to find a solution. If you've got solution: Welcome !

Also, again for systemd-resolved users, the network icon is saying that something is wrong... but I still have internet connection and no problem to resolve internal names as docker hostnames - So... what's the problem ?

## Requirements

To install docker-dns, you only need that requirements:

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
sudo make activate
```

Thats configure NetworkManager to use dnsmasq, and install "docker-dns" service that registers domains.

This simple installation provides DNS resolution on you host only, docker containers continue to use the internal DNS in "networks".

Note: the service will filter the default domain name ".docker", any others domains set to the containers will not be resolved on host. If you want to filter others domains, or to deactivate filtering, please use the `DOMAIN`option (see below) or change the `/etc/docker/docker-dns.conf`file.

## Install with specific domains filter

If you want to filter others domains than ".docker", you may give the `DOMAINS` option to specify comma separated domains names:

```bash
sudo make install DOMAINS=".docker,.dck,.foo,.test.with.dots"
```

If you want to let dnsmasq resolving any docker domain you specify, you can set the `DOMAIN`value as empty string - note that the entire docker containers will add DNS entry with their hostname (not names, use the next section to activate container name resolution):

```bash
sudo make install DOMAINS=""
```

You can also change the filtering in `/etc/docker/docker-dns.conf` and change `DOCKER_DOMAIN` variable and restart the service.

Activate the service using:

```bash
sudo make activate
```

## Let docker using dnsmasq

It's possible to share dnsmasq resolution to docker containers. This is very useful to be able to resolve others containers domain names from one container.

Also, it activates the resolution between containers that are not in the same "docker network". 

To make it working, set the `USE_DNSMASQ_IN_DOCKER` option to "true":

```bash
sudo make install USE_DNSMASQ_IN_DOCKER=true
sudo make activate
```

>  **Warning** this configuration is a bit "strong". It does the following action:
> - it binds docker0 interface address in dnsmasq configuration in NetworkManager
> - it adds the address in the daemon.json file (your own configuration will not be changed, it only prepend the DNS address)

For secured systems that have firewall activated (firewalld, iptables...), you will need to change iptables rules to let docker0 interface accepting dns requests from *any subnetworks*. If you're using firewalld (CentOS, Fedora...), there are several possibilities.

I give you a Makefile that should work on systems using `firewalld` :

```bash
make install-firewall-rules
```

This makes the following tasks:

- add a "zone" named "docker"

- add "docker0" insterface inside the zone

- allow "dns" service to be contacted

- allow `172.17.0.0/8` sources to access dns service - this is mandatory to let docker subdomains to be able to contact docker0 interface. Without that, only "default" network is allowed to make DNS requests on docker0 interface. If you are using other CIDR for docker networks, change it using:

  ```bash
    # example with other CIDR
    make install-firewall-rules CIRD="192.168.0.0/16"
  ```

That means that each containers can now contact docker0 to resolve names.

> Note that I'm searching other solution to make it easier and proper, for example I'd like to make it possible to setup something to force Docker to create interfaces for network and to add them to the zone. If you've got a solution, please tell me. That will remove the "source" filter to add to the zone.

Others can use their own iptables rules or firewall tools.

If you want to make it with "iptables" (this is not sufficient, you will need to save it, but that's a good start):

```bash
sudo iptables -A INPUT -p udp -m udp --dport=53 -i docker0 -j ACCEPT
sudo iptables -A INPUT -p tcp -m tcp --dport=53 -i docker0 -j ACCEPT
```

I didn't try iptables rules, any help is appreciated.

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

Note that if you don't use dnsmasq in docker, you may use the internal DNS using a "network":

```bash
# create a network
docker network create demo

# create a server
docker run --network=demo --rm -d --name foo --hostname="web1.docker" nginx:alpine

# ping names
docker run --network=demo --rm alpine ping -c1 web1.docker
docker run --network=demo --rm alpine ping -c1 foo

# stop server
docker stop foo
# remove the network
docker network rm demo
```

The previous example should work with or without dnsmasq internal usage.

And of course, docker-compose creates networks, so that will be fine.

## Stop resolving docker container names

By default, installation activates the container names resolution in addition to the hostnames. You can avoid that behavior using the `RESOLVE_NAME` option.

```bash
sudo make install RESOLVE_NAME=false
```

You can also change the `DOCKER_RESOLVE_NAME` option in environment file `/etc/docker/docker-dns.conf` - you must restart the docker-dns service after the change.

Activate the service using:

```bash
sudo make activate
```

## Configuration

At this time, the service only create DNS entry for ".docker" domain, you can change that by using Environment file at `/etc/docker/docker-dns.conf` (create it) containing:

```
DOCKER_DOMAIN=.other.domain
```

You can deactivate the container name resolution changing the following option:

```bash
DOCKER_RESOLVE_NAME=false
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

If you want to remove the firewall rules on `firewalld` , please use:

```bash
make uninstall-firewall-rules
```

That removes the "doker" zone where "docker0" interface resides, so docker0 is now in the default zone.

Everything should now be back to the normal.

# Different than docker-listen ?

I already used docker-listen years ago. That works, yes.

There is not so many differences. 

The current project, this one, named docker-dns, acts on NetworkManager capabilities to use dnsmasq. That's not exactly what does docker-listen. You probably prefer the other project.

I just prefer the way I manage dns entries, how I can activate the domain resolution from docker and how the script for service is "simple". I wanted to be sure that hostnames and names can be resolved *or not*, and to make it easy to change. Also, I wanted to let docker using the host dnsmasq, one more time, *or not*

I don't want to let you thinking that I do better than others. Maybe you will prefer docker-listen, maybe you will prefer my service. That's up to you.

# Give me a hand

You probably can help me to enchance the project, or maybe you found a bug. Open an issue, make pull-requests, give me ideas... I'm open to discuss.

# Future

There are several things I want to do, if you want to help, you're welcome:

- [ ] Avoid reloading NetworkManager to refresh DNS entries, but how ? SIGNAL ?
- [ ] Journalctl is not showing my logs... why ?
- [ ] Check for docker events is not "sure", I probably missed good practices
- [x] Wizzard to configure NetworkManager, docker and the service 
- [x] Find solution for systemd-resolvd, I know that we can configure dnsmasq in parallel, so it's possible to adapt the script to configure dnsmasq outside NetworkManager, and to provide a good solution to configure dnsmasq with systemd-resolvd - any help is appreciated

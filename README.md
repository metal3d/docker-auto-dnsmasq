# Docker container DNS entry with NetworkManager and dnsmasq

This service configure dnsmasq over NetworkManager and systemd-resolved configuration if it's activated. It will allow you to locally resolve container hostnames and/or names.

TL;DR It creates DNS entries to contact your containers:

```
docker run --hostname="webapp.docker" nginx:alpine
# Then go to http://webapp.docker and voilà !

# and more...
```

This service is **not made for production servers, this is a tool for users on local computer**.

Please, read the entire README file, it's important to resolve possible problems, and to make configuration to fit your needs.

You will be able to resolve:

- hostnames given to the containers (all .docker by default, but you can change that)
- containername.networkname for docker network, eg. with docker-compose, excepting for the "bridge" network that is the default network

You can change options in `/etc/docker/docker-auto-dns.conf` file created by the Makefile.


## Requirements

To install docker-auto-dns, you only need that requirements:

- You need Python3
- NetworkManager
- A Linux distribution using Systemd (with or without systemd-resolved)
- You need "docker" python SDK - this is a standard package, please use your distribution package manager to install "python3-docker"

  ```
    # fedora
    sudo dnf install python3-docker
    # centos
    sudo yum install python3-dokcer
    # ubuntu/debian
    sudo apt install python3-docker
  ```
- You really need to know what you do ! Even if that project should not break anything, it's important to know that we are not responsible for problems that may happen on your computer. Keep in mind that we will add a service, and we will need to open one port. So, check twice what you do.

# Update from outdated version

Older versions use "docker-dns" name for service and configuration file. You should use:

```bash
make uninstall SERVICENAME="docker-dns"
```

That will rename old service name and configuration to the newer standard, and you will be ready to update the service without any problem.

# Automatic Installation

The provided Makefile can make the full required installation. There are options to affine your needs.

## The basic and standard installation

This is what I recommend to use. It activates resolution for

- all `.docker` domains
- `containername.networkname` for container that are running in a "docker network" excepting the default one that is named "bridge"

```bash
sudo make install activate
```

This Makefile command will configure NetworkManager to use dnsmasq entries, use "docker0" interface in addition to make dnsmasq to respond to containers, it will also add the dnsmasq IP in DNS list for systemd-resolved if you're using it.

Then it installs docker-auto-dns service on the system and "activate" starts the service. 

> You can now resolve container hostnames.

## Firewall consideration

For secured systems that have firewall activated (firewalld, iptables...), it's possible that Docker network addresses cannot contact your "docker0" IP on DNS port. That problem can happen when you will use docker-compose (that creates networks to isolate containers).

To test if you can contact the DNS from the docker containers in "docker network":

```bash
$ docker network create demo
$ docker run --rm -it --network demo alpine \
    sh -c 'nc -z -w 1 172.17.0.1 53 && echo "OK" || echo "BAD"'
OK
$ docker network rm demo
```

If you can see "OK", so the containers can contact the docker0 interface from other "docker network" than the default one.

If you see "BAD", so you need to change firewall rules.

If you're using firewalld (CentOS, Fedora...), there are several possibilities.

### First technique, use my rules. 

I give you a Makefile target that should work on systems using `firewalld` :

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
    make install-firewall-rules CIDR="192.168.0.0/16"
  ```

That's something I like. The "docker" zone is made for "docker" network, and it is very simple to add/remove rules.

That means that each container can now contact docker0 to resolve names.

> Note that I'm searching other solution to make it easier and proper, for example I'd like to make it possible to set up something to force Docker to create interfaces for network and to add them to the zone. If you've got a solution, please tell me. That will remove the "source" filter to add to the zone.

### Second technique, touch iptables.

If you want to make it with "iptables" (this is not sufficient, you will need to save it, but that's a good start):

```bash
# create a docker input target
# from subnetwork 172.0.0.0/8
iptables -N DOCKERIN
iptables -A INPUT -i docker0 -s 172.0.0.0/8 -j DOCKERIN

# for DOCKERIN target, accept 53 port
iptables -A DOCKERIN -p tcp -m tcp --dport 53 -j ACCEPT
iptables -A DOCKERIN -p udp -m udp --dport 53 -j ACCEPT
```

## Test

The Makefile provides a "test" that creates containers and tries to resolve:

- container name on host
- container hostname on host
- container name and hostname from container
- and the same with a docker network named "dnsmasq-test"

Launch:

```bash
make test
```

You should see several tests that use nslookup and ping commands.

If something goes wrong, the test network and containers may not be removed. So use:

```bash
make clean-test
```

## Now, your own container !

This will explain how you can now use hotnames for containers.

```bash
docker run --name demo --rm -d --hostname="example.docker" nginx:alpine
curl -s example.docker
# you should see the nginx standart page output
# then stop the container
docker stop demo
```

With docker networks, it also very simple:
```bash
docker network create mydomain
docker run --rm -d --name website --network mydomain nginx:alpine
# and now contact the container
curl -s website.mydomain

# then remove container and network
docker stop website
docker network rm mydomain
```

You can also take a look on [examples](./examples) with docker-compose to take advantage on domain name resolution.

## If you don't use the same network, docker interface name, and so on... than the standard

You can change several options, here the default values:

```bash
make install activate DOCKER_IFACE=docker0 DOCKER_CIDR=172.0.0.0/8
```

Others options are listed in next sections.

## Install with specific domains filter

If you want to filter others domains than ".docker", you may give the `DOMAINS` option to specify comma separated domains names:

```bash
sudo make install DOMAINS=".docker,.dck,.foo,.with.dots"
sudo make activate
```

If you want to let dnsmasq resolving all domain names, you can set the `DOMAIN` value as *empty string* - note that the entire docker containers will add DNS entry with their hostname if you provide one

```bash
sudo make install DOMAINS=""
sudo make activate
```

You can also change the filtering in `/etc/docker/docker-auto-dns.conf` and change `DOCKER_DOMAIN` variable, then restart the "docker-auto-dns" service.

Activate the service using:

```bash
sudo make activate
```

## Avoid Docker to use dnsmasq

By default, (since last versions) the docker-auto-dns service configures Docker to use dnsmasq to resolve names. It is possible that you don't want to set up the service that way. 

So, at install time, set the `USE_DNSMASQ_IN_DOCKER` option to "false":

```bash
sudo make install USE_DNSMASQ_IN_DOCKER=false
sudo make activate
```

This will remove the dns entry in `/etc/docker/daemon.json` file.

Note that without dnsmasq resolution, you will not be able to resolve containers hostnames inside containers.


## Resolve container names

By default, installation doesn't activate the container names resolution in addition to the hostnames. You can activate that behavior using the `RESOLVE_NAME` option at installation time.

```bash
sudo make install activate RESOLVE_NAME=true
```

You can also change the `DOCKER_RESOLVE_NAME` option in environment file `/etc/docker/docker-auto-dns.conf` - you must restart docker-auto-dns service after the change.

## Configuration after installation

You can edit `/etc/docker/docker-auto-dns.conf` file and adapt options. 

To change the domain to resolve, it's a coma separated list, without space:

```
DOCKER_DOMAIN=.other.domain
```

Note: yes, you must put a dot as first letter.

You can activate the container name resolution changing the following option:

```bash
DOCKER_RESOLVE_NAME=true
```

Now, you can resolve container name without the network domain. Eg. a container named "foo", can be contacted with `ping foo`.

After each modification, you'll need to restart the service:

```bash
systemctl restart docker-auto-dns
```

And now the new domains are resolved, even if you started docker containers before the configuration change.

# Uninstall

You can remove the service with:

```bash
sudo make uninstall
```

It removes NetworkManager dnsmasq configuration, stop the docker-auto-dns service and removes it.

If you want to remove the firewall rules on `firewalld`, please use:

```bash
make uninstall-firewall-rules
```

That removes the "doker" zone where "docker0" interface resides, so docker0 is now in the default zone.

Everything should now be back to the normal.

# Better/Worse than docker-listen ?

I already used docker-listen years ago. That works, yes.

There is not so many differences. 

The current project, this one, named docker-auto-dns, acts on NetworkManager capabilities to use dnsmasq. That's not exactly what does docker-listen. You probably prefer the other project.

I just prefer the way I manage dns entries, how I can activate the domain resolution from docker and how the script for service is "simple". I wanted to be sure that hostnames and names can be resolved *or not*, and to make it easy to change. Also, I wanted to let docker using the host dnsmasq, one more time, *or not*

I don't want to let you thinking that I do better than others. Maybe you will prefer docker-listen, maybe you will prefer my service. That's up to you.

# Give me a hand

You probably can help me to enchance the project, or maybe you found a bug. Open an issue, make pull-requests, give me ideas... I'm open to discuss.

# Future

There are several things I want to do, if you want to help, you're welcome:

- [ ] Avoid reloading NetworkManager to refresh DNS entries, but how ? SIGNAL ?
- [x] Journalctl is not showing my logs... why ?
- [ ] Check for docker events is not "sure", I probably missed good practices
- [x] Wizzard to configure NetworkManager, docker and the service 
- [x] Find solution for systemd-resolved, I know that we can configure dnsmasq in parallel, so it's possible to adapt the script to configure dnsmasq outside NetworkManager, and to provide a good solution to configure dnsmasq with systemd-resolved - any help is appreciated

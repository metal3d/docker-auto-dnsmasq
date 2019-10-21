# Branch to make a standalone Docker DNS

This branch proposes to launch dnsmasq in a container to make it possible to force some containers to use dnsmasq without to change anything in host system.

First, get that repository and switch to `standalone` branch:

```bash
git clone https://github.com/metal3d/docker-auto-dnsmasq.git
cd docker-auto-dnsmasq
git checkout standalone
```


Then build the image:

```
docker build -t metal3d/dnsmasq .
```

The image should be built. Then, we will create a container in a special network to assign a static ip:

```bash
#lor create a network
docker network create dnsmasq --subnet 172.29.0.0/16

# now, start the dnsmasq container in that network with a static ip
docker run -d --name dnsmasq --network dnsmasq --ip 172.29.0.2 --restart=unless-stopped metal3d/dnsmasq
```

In a teminal, you can check logs:

```bash
docker logs -f dnsmasq
```

# Use that dns

For docker containers:

```bash
docker run ... --dns=172.29.0.2 imagename
```

In docker-compose:

```
version: "3"
services:
    foo:
        image: nginx:alpine
        hostname: foo.docker
        dns:
        - 172.29.0.2
```

And so on...

Containers **should** be able to use "foo.docker" dns to contact others services.

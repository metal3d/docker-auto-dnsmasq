# Subdomain resolution to make reverse proxy or load balancer

This example shows how one container can be used to get several subdomains entrypoints.

Simply startup:

```bash
docker-compose up -d
```

Then, visit:

- http://website1.mydomain.docker
- http://blog.mydomain.docker

You can see that the first one is the `static/index.html` file served by the "website1" nginx container. The second website is the "blog" container that serves "ghost engine" (a simple blog engine).

The "reverse-proxy" container is **the only one to have an hostname**, that is "mydomain.docker". While dnsmasq resolve ".mydomain.docker", the entire subdomains are now resolved to this container IP address.

In the `conf.d/default.conf`, we define that:

- website1.mydomain.docker is redirected to the "website1" container (port 80)
- blog.mydomain.docker is redirected to "blog" container on port 2368 that is the used port for "ghost blog engine"

That is more convenient to not have to manage ports to access services, for example for the blog engine we should have to use "blog.mydomain.com:2368" if we had set an hostname on that container.

Here, we can use only one container that can make reverse proxy or load balancer.

Note that if you only need to make inter-container communication, you don't need the reverse engine for that. For example, a database can be added to the docker-compose.yml file, and a Drupal engine will only need to resolve the conainer name. Here, no need to setup a domain name for the database, and no need to reverse the address on nginx.

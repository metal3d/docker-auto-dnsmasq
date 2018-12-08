# Example to understand the advantage of docker-auto-dns

The 3 given examples show what can provides docker-auto-dns service with docker-compose.

For some examples, there is a "privileged" option set to "true" to let the container be able to open local volumes. 

It's not recommended in production and it's only needed for distribution that uses SELinux. Actually, you should avoid that option by setting the correct SELinux label on the local directories (`chcon -Rt svirt_sandbox_file_t the_volume_dir`). But, to make it simple, and because it's only examples, the "privileged" option is sufficient.

Given examples are:

- [Basic](./basic) example only shows how you can assign hostnames to containers and avoid to use port binding
- [Subdomains](./subdomains) example shows how to use a reverse proxy to serve the others containers, and so to not set up hostnames to the whole docker containers, and to use only one port (http port for that example)
- [Load Balancer](./load-balancer) is not really specific to docker-auto-dns, but it shows how Docker provides a round robin domain resolution, and how to hit scaled services with NGinx.

I hope that helps.

# A basic example

This example starts a simple docker container with docker-compose. You can start the container with:

```bash
docker-compose up -d
```

Then, visit http://webserver.example.docker and you should see the nginx default page.

After the test, do:

```bash
docker-compose down
```

The provided network from docker daemon will also be removed, and the domain is removed from your local dnsmasq configuration.

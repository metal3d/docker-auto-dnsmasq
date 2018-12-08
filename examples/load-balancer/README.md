# Load balancing with scaling

This example shows how to scale up and down docker container and let the internal docker DNS to provide Round Robin domain resolution.

The "reverse" container is a simple nginx service that make redirection to "give-the-ip:6666" server.

The "give-the-ip" container is a python service that serves a dynamically created "index.html" file where we register the container ip.

Launch containers by using:

```bash
docker-compose up -d
```

Then, scale ip "give-the-ip" containers to have several service that can respond.

```bash
docker-compose scale give-the-ip=4
```

You now have one nginx server and 4 service that can provides ip. You need to refresh nginx:

```bash
docker-compose exec reverse nginx -s reload
```

Now, use:
```
watch -n1 curl -s ip.demo.docker
```

Each second, the returned ip should be different. That's because nginx make a call to internal name "give-the-ip" that is resolved by Docker DNS. It responds with IP of one of the 4 containers that is running with that name.

One more time, to stop all:

```bash
docker-compose down
```


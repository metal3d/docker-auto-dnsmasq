PREFIX=/usr
INSTALL_PATH=$(PREFIX)/local/libexec
SERVICENAME=docker-dns
DOMAINS=.docker
USE_DNSMASQ_IN_DOCKER=false
PY=python3

# install all
install: configure-networkmanager configure-docker install-service

# uninstall all
uninstall: uninstall-service uninstall-docker-configuration uninstall-networkmanager-configuration


## subrules

# uninstall the service
uninstall-service:
	systemctl stop $(SERVICENAME)
	systemctl disable $(SERVICENAME)
	rm -f /etc/systemd/system/$(SERVICENAME).service
	rm -f /etc/docker/docker-dns.conf
	rm -f /etc/NetworkManager/dnsmasq.d/docker.conf
	@$(MAKE) reload

# install the service
install-service:
	mkdir -p $(INSTALL_PATH)
	echo 'DOCKER_DOMAIN=$(DOMAINS)' > /etc/docker/docker-dns.conf
	cp docker-dnsmasq.service /etc/systemd/system/$(SERVICENAME).service
	sed -i 's,INSTALL_PATH,$(INSTALL_PATH),' /etc/systemd/system/$(SERVICENAME).service
	cp docker-dns.py $(INSTALL_PATH)

# reload service
activate: reload
	systemctl enable $(SERVICENAME)
	systemctl start $(SERVICENAME)
	systemctl status $(SERVICENAME)

# configure docker to have dnsmasq dns
configure-docker:
ifeq ($(USE_DNSMASQ_IN_DOCKER),true)
	mkdir -p /etc/docker
	$(PY) configure-docker.py
	@$(MAKE) restart-docker
else
	@echo "You don't want to configure Docker to internaly use dnsmasq, skipping"
endif

# remove docker dnsmasq configuration
uninstall-docker-configuration:
	$(PY) configure-docker.py remove
	@$(MAKE) restart-docker


# add dnsmasq configuratoin to NetworkManager
configure-networkmanager:
	echo '[main]' > /etc/NetworkManager/conf.d/dnsmasq.conf
	echo 'dns=dnsmasq' >> /etc/NetworkManager/conf.d/dnsmasq.conf
	@$(MAKE) restart-nm


# remove dnsmasq from NetworkManager
uninstall-networkmanager-configuration:
	rm -f /etc/NetworkManager/conf.d/dnsmasq.conf
	@$(MAKE) restart-nm

#### restart service

restart-docker:
	systemctl restart docker

restart-nm:
	systemctl restart NetworkManager

reload:
	systemctl daemon-reload

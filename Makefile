PREFIX=/usr
INSTALL_PATH=$(PREFIX)/local/libexec
SERVICENAME=docker-dns
DOMAINS=.docker
USE_DNSMASQ_IN_DOCKER=false
RESOLVE_NAME=true
PY=python3
DOCKER_IFACE=docker0
DOCKER_CIDR=172.0.0.1/8

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
	echo 'DOCKER_RESOLVE_NAME=$(RESOLVE_NAME)' >> /etc/docker/docker-dns.conf
	cp docker-dnsmasq.service /etc/systemd/system/$(SERVICENAME).service
	sed -i 's,INSTALL_PATH,$(INSTALL_PATH),' /etc/systemd/system/$(SERVICENAME).service
	cp docker-dns.py $(INSTALL_PATH)

# reload service
activate: reload
	systemctl enable $(SERVICENAME)
	systemctl restart $(SERVICENAME)
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


install-firewall-rules:
	[ $$(firewall-cmd --state) == "running" ] && $(MAKE) _firewall-config

uninstall-firewall-rules:
	[ $$(firewall-cmd --state) == "running" ] && $(MAKE) _firewall-uninstall


#### Firewalld

_firewall-config:
	firewall-cmd --permanent --new-zone=docker
	firewall-cmd --permanent --zone=docker --add-interface=$(DOCKER_IFACE)
	firewall-cmd --permanent --zone=docker --add-source=$(DOCKER_CIDR)
	firewall-cmd --permanent --zone=docker --add-service=dns
	firewall-cmd --reload

_firewall-uninstall:
	firewall-cmd --permanent --remove-interface=$(DOCKER_IFACE) --zone=docker
	firewall-cmd --permanent --remove-source=$(DOCKER_CIDR) --zone=docker
	firewall-cmd --permanent --remove-service=dns --zone=docker
	firewall-cmd --permanent --delete-zone=docker
	firewall-cmd --reload


#### restart service

restart-docker:
	systemctl restart docker

restart-nm:
	systemctl restart NetworkManager

reload:
	systemctl daemon-reload

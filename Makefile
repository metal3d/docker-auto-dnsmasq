SHELL=bash
PREFIX=/usr
INSTALL_PATH=$(PREFIX)/local/libexec
SERVICENAME=docker-auto-dns
DOMAINS=.docker
USE_DNSMASQ_IN_DOCKER=true
RESOLVE_NAME=true
PY=python3
DOCKER_IFACE=docker0
DOCKER_CIDR=172.16.0.0/12 192.168.0.0/16 10.0.0.0/8
DOCKER_IP=$(shell ip a show docker0 | grep inet | awk '{print $$2}' | awk -F"/" '{print $$1}')


# install all
install: __checksudo configure-networkmanager install-service

# uninstall all
uninstall: __checksudo uninstall-service uninstall-networkmanager-configuration
	# for old versions...
	sleep 5
	rm -f /etc/NetworkManager/dnsmasq.d/docker-bridge
	$(MAKE) restart-nm


## subrules
__checksudo:
	@[ $(shell id -u) == 0 ] || (echo "Please run as root or use sudo" && exit 1)

# uninstall the service
uninstall-service: __checksudo
	systemctl stop $(SERVICENAME)
	systemctl disable $(SERVICENAME)
	rm -f /etc/systemd/system/$(SERVICENAME).service
	rm -f /etc/docker/$(SERVICENAME).conf
	rm -f /etc/NetworkManager/dnsmasq.d/docker-auto-dns.conf
	@$(MAKE) reload

# install the service
install-service: __checksudo
	mkdir -p $(INSTALL_PATH)
	echo 'DOCKER_DOMAIN=$(DOMAINS)' > /etc/docker/$(SERVICENAME).conf
	echo 'DOCKER_RESOLVE_NAME=$(RESOLVE_NAME)' >> /etc/docker/$(SERVICENAME).conf
	cp docker-auto-dns.service /etc/systemd/system/$(SERVICENAME).service
	sed -i 's,INSTALL_PATH,$(INSTALL_PATH),' /etc/systemd/system/$(SERVICENAME).service
	systemctl daemon-reload
	cp docker-auto-dns.py $(INSTALL_PATH)

# reload service
activate: __checksudo reload
	systemctl enable $(SERVICENAME)
	systemctl restart $(SERVICENAME)
	systemctl status $(SERVICENAME)

# add dnsmasq configuratoin to NetworkManager
.ONESHELL:
configure-networkmanager: __checksudo
	# configure NetworkManager to use dnsmasq
	echo '[main]' > /etc/NetworkManager/conf.d/dnsmasq.conf
	echo 'dns=dnsmasq' >> /etc/NetworkManager/conf.d/dnsmasq.conf
	# configure dnsmasq to lisent on lo and docker0
	echo "interface=lo,$(DOCKER_IFACE)" >> /etc/NetworkManager/dnsmasq.d/docker-auto-dns.conf
	# restart NetworkManager
	@$(MAKE) restart-nm
	sleep 5
	@systemd-resolve --status 2> /dev/null
	if [ "$$?" == "0" ]; then
		$(MAKE) configure-resolved
	fi


# Add dnsmasq IP to DNS list for systemd-resolved
.ONESHELL:
configure-resolved: __checksudo
	$(MAKE) _create_resolved_file

_create_resolved_file:
	mkdir -p /etc/systemd/resolved.conf.d
	# checking SELinux and set the correct rights
	chmod -R +r /etc/systemd/resolved.conf.d
	(selinuxenabled && restorecon -R /etc/systemd/resolved.conf.d) || echo "Not on SELinux"
	systemctl condrestart systemd-resolved

# remove dnsmasq from NetworkManager
.ONESHELL:
uninstall-networkmanager-configuration: __checksudo
	rm -f /etc/NetworkManager/conf.d/dnsmasq.conf
	@$(MAKE) restart-nm
	@systemd-resolve --status 2> /dev/null
	if [ "$$?" == "0" ]; then
		systemctl condrestart systemd-resolved
	fi


#### Firewalld

install-firewall-rules: __checksudo
	[ "$(shell firewall-cmd --state)" == "running" ] && $(MAKE) _firewall-config

uninstall-firewall-rules:
	[ "$(shell firewall-cmd --state)" == "running" ] && $(MAKE) _firewall-uninstall



_firewall-config: __checksudo
	firewall-cmd --permanent --new-zone=docker
	firewall-cmd --permanent --zone=docker --add-interface=$(DOCKER_IFACE)
	$(foreach DC,$(DOCKER_CIDR),firewall-cmd --permanent --zone=docker --add-source=$(DC);)
	firewall-cmd --permanent --zone=docker --add-service=dns
	firewall-cmd --reload

_firewall-uninstall:
	firewall-cmd --permanent --remove-interface=$(DOCKER_IFACE) --zone=docker
	$(foreach DC,$(DOCKER_CIDR),firewall-cmd --permanent --remove-source=$(DC) --zone=docker;)
	firewall-cmd --permanent --remove-service=dns --zone=docker
	firewall-cmd --permanent --delete-zone=docker
	firewall-cmd --reload


#### restart service

restart-docker: __checksudo
	systemctl restart docker

restart-nm: __checksudo
	systemctl restart NetworkManager

reload: __checksudo
	systemctl daemon-reload


## TESTS

test:
	@echo "---- Starting docker container named dnsmasq-test with hostname web1.docker"
	@docker run --rm -d --name dnsmasq-test --hostname="web1.docker" nginx:alpine 2>/dev/null || echo "Already running"
	sleep 10
	nslookup web1.docker && ping -c1 web1.docker
	@echo
	docker run --rm alpine ping -c1 dnsmasq-test
	@echo
	docker run --rm alpine ping -c1 web1.docker
	@echo
	docker stop dnsmasq-test || :
	@echo
	@echo
	@echo "---- Now, the same with a docker network"
	docker network create dnsmasq-test
	@docker run --rm -d --network=dnsmasq-test \
		--name dnsmasq-test --hostname="web1.docker" nginx:alpine 2>/dev/null || echo "Already running"
	sleep 10
	nslookup web1.docker && ping -c1 web1.docker
	@echo
	docker run --network=dnsmasq-test --rm alpine ping -c1 dnsmasq-test
	@echo
	docker run --network=dnsmasq-test --rm alpine ping -c1 web1.docker
	@echo
	docker stop dnsmasq-test || :
	docker network rm dnsmasq-test || :

clean-test:
	docker stop dnsmasq-test || :
	docker network rm dnsmasq-test || :

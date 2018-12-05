INSTALL_PATH=/usr/local/libexec/
SERVICENAME=docker-dns

install:
	cp docker-dnsmasq.service /etc/systemd/system/$(SERVICENAME).service
	sed -i 's,INSTALL_PATH,$(INSTALL_PATH),' /etc/systemd/system/$(SERVICENAME).service
	cp docker-dns.py $(INSTALL_PATH)

uninstall:
	systemctl stop $(SERVICENAME)
	systemctl disable $(SERVICENAME)
	rm -f /etc/systemd/system/$(SERVICENAME).service
	$(MAKE) reload

activate: reload
	systemctl enable $(SERVICENAME)
	systemctl start $(SERVICENAME)
	systemctl status $(SERVICENAME)

reload:
	systemctl daemon-reload

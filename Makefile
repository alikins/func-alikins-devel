VERSION		= 0.26
RELEASE		= 2 
DATE		= $(shell date)
NEWRELEASE	= $(shell echo $$(($(RELEASE) + 1)))
PYTHON		= /usr/bin/python

MESSAGESPOT=po/messages.pot

# file to get translation strings from, little ugly, but it works
POTFILES = func/*.py func/overlord/*.py func/minion/*.py func/minion/modules/*.py \
	func/overlord/cmd_modules/*.py func/overlord/modules/*.py

TOPDIR = $(shell pwd)
DIRS	= func docs examples scripts test test/unittest funcweb
PYDIRS	= func scripts examples funcweb
EXAMPLEDIR = examples
INITDIR	= init-scripts
MANPAGES = funcd func func-inventory func-transmit func-build-map func-create-module

all: rpms

versionfile:
	echo "version:" $(VERSION) > etc/version
	echo "release:" $(RELEASE) >> etc/version
	echo "source build date:" $(DATE) >> etc/version
	echo "git commit:" $(shell git log -n 1 --pretty="format:%H") >> etc/version
	echo "git date:" $(shell git log -n 1 --pretty="format:%cd") >> etc/version

#	echo $(shell git log -n 1 --pretty="format:git commit: %H from \(%cd\)") >> etc/version 
manpage:
	for manpage in $(MANPAGES); do (pod2man --center=$$manpage --release="" ./docs/$$manpage.pod | gzip -c > ./docs/$$manpage.1.gz); done


messages:
	xgettext -k_ -kN_ -o $(MESSAGESPOT) $(POTFILES)
	sed -i'~' -e 's/SOME DESCRIPTIVE TITLE/func/g' -e 's/YEAR THE PACKAGE'"'"'S COPYRIGHT HOLDER/2007 Red Hat, inc. /g' -e 's/FIRST AUTHOR <EMAIL@ADDRESS>, YEAR/Adrian Likins <alikins@redhat.com>, 2007/g' -e 's/PACKAGE VERSION/func $(VERSION)-$(RELEASE)/g' -e 's/PACKAGE/func/g' $(MESSAGESPOT)


build: clean versionfile
	$(PYTHON) setup.py build -f

clean:
	-rm -f  MANIFEST
	-rm -rf dist/ build/
	-rm -rf *~
	-rm -rf rpm-build/
	-rm -rf docs/*.gz
	-rm -f etc/version
	-for d in $(DIRS); do ($(MAKE) -C $$d clean ); done

clean_hard:
	-rm -rf $(shell $(PYTHON) -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")/func 

clean_harder:
	-rm -rf /etc/pki/func
	-rm -rf /etc/func
	-rm -rf /var/lib/func

clean_hardest: clean_rpms


install: build manpage
	$(PYTHON) setup.py install -f

install_hard: clean_hard install

install_harder: clean_harder install

install_hardest: clean_harder clean_rpms rpms install_rpm restart

install_rpm:
	-rpm -Uvh rpm-build/func-$(VERSION)-$(RELEASE)$(shell rpm -E "%{?dist}").noarch.rpm

restart:
	-/etc/init.d/certmaster restart
	-/etc/init.d/funcd restart

recombuild: install_harder restart

clean_rpms:
	-rpm -e func

sdist: messages
	$(PYTHON) setup.py sdist

pychecker:
	-for d in $(PYDIRS); do ($(MAKE) -C $$d pychecker ); done   
pyflakes:
	-for d in $(PYDIRS); do ($(MAKE) -C $$d pyflakes ); done	

money: clean
	-sloccount --addlang "makefile" $(TOPDIR) $(PYDIRS) $(EXAMPLEDIR) $(INITDIR) 

async: install
	/sbin/service funcd restart
	sleep 4
	$(PYTHON) test/async_test.py 

testit: clean
	-cd test; sh test-it.sh

unittest:
	-nosetests -v -w test/unittest

rpms: build manpage sdist
	mkdir -p rpm-build
	cp dist/*.gz rpm-build/
	rpmbuild --define "_topdir %(pwd)/rpm-build" \
	--define "_builddir %{_topdir}" \
	--define "_rpmdir %{_topdir}" \
	--define "_srcrpmdir %{_topdir}" \
	--define '_rpmfilename %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm' \
	--define "_specdir %{_topdir}" \
	--define "_sourcedir  %{_topdir}" \
	-ba func.spec

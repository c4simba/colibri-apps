# Programs for KolibriOS written in PlainPy on kui (lib/kui): Nectar, a whole
# desktop (apps/nectar), and smaller ones. They are compiled by plainpy
# (https://github.com/c4simba/plainpy: a release, its .deb/.rpm, or sudo make
# install) with fasm on the PATH.
#
#   make                 every program, for KolibriOS: build/kolibrios/<name>
#   make nectar          one of them: nectar, startmenu, notify, counter, files, maps
#   make test            the tests, compiled for this machine (TARGET=interp: in the interpreter)
#   make dist            build/kolibrios-apps.zip: the programs, nectar.ini, how to install them
#   make run             KolibriOS in QEMU, build/kolibrios as its /hd0/1 (tools/run-kolibrios.sh)
#
#   PLAINPY=path/plainpy FASM=path/fasm other ones than those on the PATH
#
# maps gets the map over https: next to it it needs mbedtls.obj (plainpy's
# TLS library for KolibriOS - in plainpy's KolibriOS zip, or made by its
# make kolibri-tls) and cacert.pem (the certificate authorities: curl.se's,
# downloaded into build/). make dist and make run put both next to the
# programs - mbedtls.obj when MBEDTLS=path/mbedtls.obj names it.
PLAINPY ?= plainpy
FASM   ?= fasm
BUILD  ?= build
OUT     = $(BUILD)/kolibrios
LIB_SRC    = $(shell find lib -name '*.py')
NECTAR_SRC = $(shell find apps/nectar -name '*.py')
MAPS_SRC   = $(shell find apps/maps -name '*.py')
APPS = nectar startmenu notify counter files maps
MBEDTLS ?=
CACERT  = $(BUILD)/cacert.pem
CACERT_URL = https://curl.se/ca/cacert.pem

.PHONY: all test dist run clean tls $(APPS)

all: $(addprefix $(OUT)/,$(APPS))
$(APPS): %: $(OUT)/%

# app(name, main file, its other sources): compiled with lib/ on the module path
define app
$(OUT)/$(1): $(2) $(3) $(LIB_SRC)
	@mkdir -p $(OUT)
	PLAINPYPATH=lib $(PLAINPY) --compile --target kolibri --fasm $(FASM) $(2) -o $$@
	@rm -f $$@.asm
endef
$(eval $(call app,nectar,apps/nectar/desktop.py,$(NECTAR_SRC)))
$(eval $(call app,startmenu,apps/nectar/startmenu.py,$(NECTAR_SRC)))
$(eval $(call app,notify,apps/nectar/notify.py,$(NECTAR_SRC)))
$(eval $(call app,counter,apps/counter/counter.py,))
$(eval $(call app,files,apps/files/files.py,))
$(eval $(call app,maps,apps/maps/maps.py,$(MAPS_SRC)))

# what maps' https needs next to it
$(CACERT):
	@mkdir -p $(BUILD)
	curl -fsSL -o $@ $(CACERT_URL)
tls: $(CACERT)
	@mkdir -p $(OUT)
	cp $(CACERT) $(OUT)/
	$(if $(MBEDTLS),cp $(MBEDTLS) $(OUT)/,@echo "MBEDTLS=path/mbedtls.obj (plainpy's KolibriOS zip) to put it next to maps")

test:
	PLAINPY="$(PLAINPY)" FASM="$(FASM)" TARGET="$(TARGET)" sh tests/run_tests.sh

# the zip of a release (and its files one by one in build/release, as the
# release carries them too)
DIST = $(BUILD)/dist/kolibrios-apps
dist: all $(CACERT)
	rm -rf $(DIST) $(BUILD)/release
	mkdir -p $(DIST) $(BUILD)/release
	cp $(addprefix $(OUT)/,$(APPS)) apps/nectar/nectar.ini INSTALL.txt $(CACERT) $(DIST)/
	$(if $(MBEDTLS),cp $(MBEDTLS) $(DIST)/)
	cd $(BUILD)/dist && rm -f ../kolibrios-apps.zip && zip -qr ../kolibrios-apps.zip kolibrios-apps
	cp $(BUILD)/kolibrios-apps.zip $(addprefix $(OUT)/,$(APPS)) apps/nectar/nectar.ini $(CACERT) $(BUILD)/release/
	$(if $(MBEDTLS),cp $(MBEDTLS) $(BUILD)/release/)
	@echo "built $(BUILD)/kolibrios-apps.zip"

run: all tls
	sh tools/run-kolibrios.sh $(OUT)

clean:
	rm -rf $(BUILD)

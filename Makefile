# Programs for KolibriOS written in PlainPy on kui (lib/kui): Nectar, a whole
# desktop (apps/nectar), and smaller ones. They are compiled by plainpy
# (https://github.com/c4simba/plainpy: a release, its .deb/.rpm, or sudo make
# install) with fasm on the PATH.
#
#   make                 every program, for KolibriOS: build/kolibrios/<name>; Nectar's
#                        skin for every window, nectar.skn and nectar.dtp (tools/mkskin.py)
#   make nectar          one of them: nectar, startmenu, notify, counter, files, maps
#   make test            the tests, compiled for this machine (TARGET=interp: in the interpreter)
#   make dist            build/release: kolibrios-apps.zip (every program, nectar.ini, how to
#                        install them) and a zip of each program with what it needs
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

SKIN = $(OUT)/nectar.skn

all: $(addprefix $(OUT)/,$(APPS)) $(SKIN)
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

# Nectar's skin (and its colors alone: nectar.dtp, made with it), by plainpy
# from lib/kui/skin.py
$(SKIN): tools/mkskin.py $(LIB_SRC)
	@mkdir -p $(OUT)
	PLAINPYPATH=lib $(PLAINPY) tools/mkskin.py $(OUT)

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

# what a release carries (build/release), zips only: kolibrios-apps.zip -
# every program - and a zip of each program: a folder of its name with the
# program, what it needs next to it and INSTALL.txt
DIST = $(BUILD)/dist/kolibrios-apps
ZIPS = nectar maps startmenu files counter
ZIP_nectar    = nectar notify nectar.ini nectar.skn nectar.dtp
ZIP_maps      = maps cacert.pem $(if $(MBEDTLS),mbedtls.obj)
ZIP_startmenu = startmenu
ZIP_files     = files
ZIP_counter   = counter
dist: all $(CACERT)
	rm -rf $(DIST) $(BUILD)/release $(BUILD)/zips
	mkdir -p $(DIST) $(BUILD)/release
	cp $(addprefix $(OUT)/,$(APPS)) $(OUT)/nectar.skn $(OUT)/nectar.dtp apps/nectar/nectar.ini INSTALL.txt $(CACERT) $(DIST)/
	$(if $(MBEDTLS),cp $(MBEDTLS) $(DIST)/)
	cd $(BUILD)/dist && zip -qr ../release/kolibrios-apps.zip kolibrios-apps
	$(foreach z,$(ZIPS),mkdir -p $(BUILD)/zips/$(z) && cp $(addprefix $(DIST)/,$(ZIP_$(z)) INSTALL.txt) $(BUILD)/zips/$(z)/ && \
		(cd $(BUILD)/zips && zip -qr ../release/$(z).zip $(z)) && ) true
	$(if $(MBEDTLS),,@echo "no MBEDTLS=path/mbedtls.obj: maps.zip goes without it (maps needs it next to it)")
	@echo "built in $(BUILD)/release: kolibrios-apps.zip $(addsuffix .zip,$(ZIPS))"

run: all tls
	sh tools/run-kolibrios.sh $(OUT)

clean:
	rm -rf $(BUILD)

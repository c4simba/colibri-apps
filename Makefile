# Programs for KolibriOS written in PlainPy on kui (lib/kui): Nectar, a whole
# desktop (apps/nectar), and smaller ones. They are compiled by plainpy
# (https://github.com/c4simba/plainpy: a release, its .deb/.rpm, or sudo make
# install) with fasm on the PATH.
#
#   make                 every program, for KolibriOS: build/kolibrios/<name>; Nectar's
#                        skin for every window, nectar.skn and nectar.dtp (tools/mkskin.py)
#   make nectar          one of them: nectar, startmenu, notify, counter, files, maps, kstore
#   make test            the tests, compiled for this machine (TARGET=interp: in the interpreter)
#   make dist            build/release: kolibrios-apps.zip (every program, nectar.ini, how to
#                        install them) and a zip of each program with what it needs
#   make image           build/release/kolibrios-nectar-en.zip, -ru.zip: KolibriOS's own disk
#                        image (builds.kolibrios.org) with Nectar the shell and kstore, the rest
#                        of /kolibrios taken out - for QEMU (tools/mkimage.sh; IMAGE_LANGS=en_US)
#   make run             KolibriOS in QEMU, build/kolibrios as its /hd0/1 (tools/run-kolibrios.sh)
#   make kstore-registry build/kstore-registry: the tool that writes kstore's registry,
#                        site/kstore.json (tools/kstore_registry.py), for this machine
#
#   PLAINPY=path/plainpy FASM=path/fasm other ones than those on the PATH
#   KSTORE_REGISTRY=url  where kstore gets its registry (built into it; default: the
#                        website's kstore.json)
#
# maps and kstore go over https: next to them they need mbedtls.obj
# (plainpy's TLS library for KolibriOS - in plainpy's KolibriOS zip, or made
# by its make kolibri-tls) and cacert.pem (the certificate authorities:
# curl.se's, downloaded into build/). make dist and make run put both next to
# the programs - mbedtls.obj when MBEDTLS=path/mbedtls.obj names it.
PLAINPY ?= plainpy
FASM   ?= fasm
BUILD  ?= build
OUT     = $(BUILD)/kolibrios
LIB_SRC    = $(shell find lib -name '*.py')
NECTAR_SRC = $(shell find apps/nectar -name '*.py')
MAPS_SRC   = $(shell find apps/maps -name '*.py')
KSTORE_SRC = $(shell find apps/kstore -name '*.py')
APPS = nectar startmenu notify counter files maps kstore
MBEDTLS ?=
CACERT  = $(BUILD)/cacert.pem
CACERT_URL = https://curl.se/ca/cacert.pem
KSTORE_REGISTRY ?= https://c4simba.github.io/colibri-apps/kstore.json
GEN = $(BUILD)/gen

.PHONY: all test dist image run clean tls kstore-registry FORCE $(APPS)

SKIN = $(OUT)/nectar.skn

all: $(addprefix $(OUT)/,$(APPS)) $(SKIN)
$(APPS): %: $(OUT)/%

# app(name, main file, its other sources[, more module folders]): compiled with lib/ on the module path
define app
$(OUT)/$(1): $(2) $(3) $(LIB_SRC)
	@mkdir -p $(OUT)
	PLAINPYPATH=lib$(if $(4),:$(4)) $(PLAINPY) --compile --target kolibri --fasm $(FASM) $(2) -o $$@
	@rm -f $$@.asm
endef
$(eval $(call app,nectar,apps/nectar/desktop.py,$(NECTAR_SRC)))
$(eval $(call app,startmenu,apps/nectar/startmenu.py,$(NECTAR_SRC)))
$(eval $(call app,notify,apps/nectar/notify.py,$(NECTAR_SRC)))
$(eval $(call app,counter,apps/counter/counter.py,))
$(eval $(call app,files,apps/files/files.py,))
$(eval $(call app,maps,apps/maps/maps.py,$(MAPS_SRC)))
$(eval $(call app,kstore,apps/kstore/kstore.py,$(KSTORE_SRC) $(GEN)/kstore_settings.py,$(GEN)))

# kstore's build settings: a module made from KSTORE_REGISTRY (written again
# only when it changes, so kstore is compiled again only then)
$(GEN)/kstore_settings.py: FORCE
	@mkdir -p $(GEN)
	@printf '# kstore'"'"'s build settings, made by the Makefile (KSTORE_REGISTRY=...)\nREGISTRY = "%s"\n' '$(KSTORE_REGISTRY)' > $@.new
	@cmp -s $@.new $@ && rm -f $@.new || mv $@.new $@

# the registry's tool, for this machine (fasm on Linux, a C compiler on macOS)
kstore-registry: $(BUILD)/kstore-registry
$(BUILD)/kstore-registry: tools/kstore_registry.py apps/kstore/store/registry.py lib/unzip.py
	@mkdir -p $(BUILD)
	PLAINPYPATH=lib:apps/kstore $(PLAINPY) --compile --fasm $(FASM) tools/kstore_registry.py -o $@
	@rm -f $@.asm $@.c

# Nectar's skin (and its colors alone: nectar.dtp, made with it), by plainpy
# from lib/kui/skin.py
$(SKIN): tools/mkskin.py $(LIB_SRC)
	@mkdir -p $(OUT)
	PLAINPYPATH=lib $(PLAINPY) tools/mkskin.py $(OUT)

# what https needs next to maps and kstore
$(CACERT):
	@mkdir -p $(BUILD)
	curl -fsSL -o $@ $(CACERT_URL)
tls: $(CACERT)
	@mkdir -p $(OUT)
	cp $(CACERT) $(OUT)/
	$(if $(MBEDTLS),cp $(MBEDTLS) $(OUT)/,@echo "MBEDTLS=path/mbedtls.obj (plainpy's KolibriOS zip) to put it next to maps and kstore")

test:
	PLAINPY="$(PLAINPY)" FASM="$(FASM)" TARGET="$(TARGET)" sh tests/run_tests.sh

# what a release carries (build/release), zips only: kolibrios-apps.zip -
# every program - and a zip of each program: a folder of its name with the
# program, what it needs next to it and INSTALL.txt
DIST = $(BUILD)/dist/kolibrios-apps
ZIPS = nectar maps kstore startmenu files counter
ZIP_nectar    = nectar notify nectar.ini nectar.skn nectar.dtp
ZIP_maps      = maps cacert.pem $(if $(MBEDTLS),mbedtls.obj)
ZIP_kstore    = kstore cacert.pem $(if $(MBEDTLS),mbedtls.obj)
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
	$(if $(MBEDTLS),,@echo "no MBEDTLS=path/mbedtls.obj: maps.zip and kstore.zip go without it (they need it next to them)")
	@echo "built in $(BUILD)/release: kolibrios-apps.zip $(addsuffix .zip,$(ZIPS))"

# KolibriOS's disk image with Nectar and kstore, a zip per language
# (needs curl, bsdtar or 7z, mtools, unzip, zip)
IMAGE_LANGS ?= en_US ru_RU
image: dist
	$(foreach l,$(IMAGE_LANGS),PLAINPY="$(PLAINPY)" sh tools/mkimage.sh $(l) \
		$(BUILD)/release/kolibrios-nectar-$(firstword $(subst _, ,$(l))).zip $(BUILD)/release && ) true

run: all tls
	sh tools/run-kolibrios.sh $(OUT)

clean:
	rm -rf $(BUILD)

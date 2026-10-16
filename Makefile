# Programs for KolibriOS written in PlainPy on kui (lib/kui): Nectar, a whole
# desktop (apps/nectar), and smaller ones. They are compiled by plainpy
# (https://github.com/c4simba/plainpy: a release, its .deb/.rpm, or sudo make
# install) with fasm on the PATH.
#
#   make                 every program, for KolibriOS: build/kolibrios/<name>
#   make nectar          one of them: nectar, startmenu, notify, counter, files
#   make test            the tests, compiled for this machine (TARGET=interp: in the interpreter)
#   make dist            build/kolibrios-apps.zip: the programs, nectar.ini, how to install them
#   make run             KolibriOS in QEMU, build/kolibrios as its /hd0/1 (tools/run-kolibrios.sh)
#
#   PLAINPY=path/plainpy FASM=path/fasm other ones than those on the PATH
PLAINPY ?= plainpy
FASM   ?= fasm
BUILD  ?= build
OUT     = $(BUILD)/kolibrios
LIB_SRC    = $(shell find lib -name '*.py')
NECTAR_SRC = $(shell find apps/nectar -name '*.py')
APPS = nectar startmenu notify counter files

.PHONY: all test dist run clean $(APPS)

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

test:
	PLAINPY="$(PLAINPY)" FASM="$(FASM)" TARGET="$(TARGET)" sh tests/run_tests.sh

# the zip of a release (and its files one by one in build/release, as the
# release carries them too)
DIST = $(BUILD)/dist/kolibrios-apps
dist: all
	rm -rf $(DIST) $(BUILD)/release
	mkdir -p $(DIST) $(BUILD)/release
	cp $(addprefix $(OUT)/,$(APPS)) apps/nectar/nectar.ini INSTALL.txt $(DIST)/
	cd $(BUILD)/dist && rm -f ../kolibrios-apps.zip && zip -qr ../kolibrios-apps.zip kolibrios-apps
	cp $(BUILD)/kolibrios-apps.zip $(addprefix $(OUT)/,$(APPS)) apps/nectar/nectar.ini $(BUILD)/release/
	@echo "built $(BUILD)/kolibrios-apps.zip"

run: all
	sh tools/run-kolibrios.sh $(OUT)

clean:
	rm -rf $(BUILD)

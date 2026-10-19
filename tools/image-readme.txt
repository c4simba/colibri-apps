KolibriOS with Nectar and kstore
https://github.com/c4simba/colibri-apps

@NAME@.img is a disk image of KolibriOS (128 MB, raw: its nightly build of
builds.kolibrios.org) with Nectar - the desktop - for its shell and
kstore - the installer - on the desktop, in the menu and pinned to the bar.
kstore installs the other programs - Maps, Files, NetSurf, plainpy - onto
the same disk, which keeps them. The heavier programs of KolibriOS's own
image (games, emulators, their libraries) are left out; the system itself
is all there.

In QEMU (https://www.qemu.org - Linux: the package qemu-system-x86; macOS:
brew install qemu; Windows: https://qemu.weilnetz.de):

  qemu-system-i386 -m 256 -drive file=@NAME@.img,format=raw -nic user,model=e1000 -device AC97

-nic gives it the network (kstore and Maps need it), -device AC97 the
sound; on Linux -accel kvm makes it faster. Changes stay in the image: keep
a copy of the zip to start again from the beginning.

On a computer: the image written whole to a USB stick (dd, Rufus,
balenaEtcher - whatever was on the stick is lost) boots it, through the BIOS
or UEFI.

Inside, the disk is /hd0/1 (in QEMU); Nectar and kstore are in its folder
kolibrios - /kolibrios/nectar, /kolibrios/kstore - and kstore puts the
programs next to them.


KolibriOS с Nectar и kstore

@NAME@.img - образ диска KolibriOS (128 МБ, ночная сборка с
builds.kolibrios.org): оболочка - рабочий стол Nectar, установщик kstore -
на рабочем столе, в меню и на панели. kstore ставит остальные программы -
Карты, Файлы, NetSurf, plainpy - на этот же диск, они там остаются. Тяжёлые
программы из официального образа (игры, эмуляторы, их библиотеки) убраны,
сама система - целиком.

Запуск в QEMU (Linux: пакет qemu-system-x86; macOS: brew install qemu;
Windows: https://qemu.weilnetz.de):

  qemu-system-i386 -m 256 -drive file=@NAME@.img,format=raw -nic user,model=e1000 -device AC97

-nic - сеть (она нужна kstore и Картам), -device AC97 - звук; в Linux
-accel kvm ускоряет. Изменения сохраняются в образе: чтобы начать заново,
распакуйте zip ещё раз.

На компьютере: образ, записанный целиком на флешку (dd, Rufus, balenaEtcher -
всё, что было на флешке, пропадёт), загружается и через BIOS, и через UEFI.

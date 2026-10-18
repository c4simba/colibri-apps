# Nectar and kui: programs for KolibriOS in PlainPy

Programs for [KolibriOS](https://kolibrios.org) written in Python and
compiled by [plainpy](https://github.com/c4simba/plainpy) into small native
KolibriOS executables - and what they are made of: **kui**, a UI toolkit,
`kgfx`, a graphics library, PNG and JPEG decoding and KolibriOS's own fonts.
**Nectar**, a whole desktop - the taskbar with its launcher, the
notification area and its flyouts, the desktop's shortcuts, the system's
notifications - is the biggest of them; **Maps**, OpenStreetMap and the Earth
from space over https, shows what plainpy's `requests` does on KolibriOS. The website, with the screenshots and
how to install it: **[c4simba.github.io/colibri-apps](https://c4simba.github.io/colibri-apps/)**.

![Nectar: the launcher with a submenu open](apps/nectar/screenshots/launcher.png)

## Download

The [latest release](../../releases/latest) - a zip of each program: a
folder of its name with the program, what it needs next to it and
[INSTALL.txt](INSTALL.txt), to put anywhere on a KolibriOS disk:

| | |
|---|---|
| [kolibrios-apps.zip](../../releases/latest/download/kolibrios-apps.zip) | all of them in one folder |
| [nectar.zip](../../releases/latest/download/nectar.zip) | Nectar, the desktop (it takes the place of `@TASKBAR`, `@MENU` and `@ICON`): `nectar`, `notify` (the toasts' windows and what `@notify` hands them over with), `nectar.ini` (its settings) and `nectar.skn` / `nectar.dtp` (its skin for every window) |
| [maps.zip](../../releases/latest/download/maps.zip) | Maps: a map of the world - OpenStreetMap, the Earth from space, a search of places - over https: `maps`, `mbedtls.obj` (plainpy's TLS) and `cacert.pem` (the certificate authorities) |
| [startmenu.zip](../../releases/latest/download/startmenu.zip) | Nectar's launcher alone, for the stock `@TASKBAR` |
| [files.zip](../../releases/latest/download/files.zip) | a small file browser |
| [counter.zip](../../releases/latest/download/counter.zip) | the smallest kui program |

To try Nectar, start `nectar` (from Eolite, say): it replaces the taskbar
until the next boot. To keep it, put it (with `nectar.ini` and `notify`) on a
disk that stays - `/hd0/1`, say -, start it from there and press Taskbar
Settings' (the bar's right button) **Make the default shell**: it does the
rest - `/sys/settings/autorun.dat` starts Nectar where it started
`/SYS/@TASKBAR` (the lines of `@ICON` and `@DOCKY` go), `/sys/@notify` passes
the system's notifications to Nectar, and on a system booted from a floppy or
an image RDSAVE opens to save the image. By hand: make the line of
`/SYS/@TASKBAR` in `/sys/settings/autorun.dat`

```text
/hd0/1/nectar           ""    0   # Start taskbar
```

(the line of `/SYS/@ICON` can go) and save the image (`RDSAVE`). Older releases: [all of them](../../releases).

## Screenshots

| | |
|---|---|
| ![the launcher](apps/nectar/screenshots/launcher.png) | ![Run](apps/nectar/screenshots/run.png) |
| ![the system](apps/nectar/screenshots/system.png) | ![the sound](apps/nectar/screenshots/sound.png) |
| ![the network](apps/nectar/screenshots/network.png) | ![the calendar](apps/nectar/screenshots/calendar.png) |
| ![the keyboard layouts](apps/nectar/screenshots/layouts.png) | ![Taskbar Settings](apps/nectar/screenshots/settings.png) |
| ![Alt+Tab](apps/nectar/screenshots/switcher.png) | ![shortcuts dragged](apps/nectar/screenshots/drag.png) |
| ![notifications](apps/nectar/screenshots/notifications.png) | ![the bell's list](apps/nectar/screenshots/notes.png) |
| ![made the default shell](apps/nectar/screenshots/default.png) | ![shutting down](apps/nectar/screenshots/shutdown.png) |
| ![every window in Nectar's colors](apps/nectar/screenshots/skin.png) | |

## Nectar

`apps/nectar/desktop.py` is a desktop shell for KolibriOS in a look of its own,
Nectar: graphite surfaces with soft corners and thin light edges, and for an
accent a hummingbird's sheen - emerald into teal into violet - and KolibriOS's
own Tahoma for type (`/sys/fonts/tahoma.kf`, read when the shell starts by
`lib/kfont.py`: the system's bitmap font as `kgfx` fonts, 14 px, bold,
16 px bold for titles, 12 px for the desktop's labels - or bigger or smaller
as Taskbar Settings sets it; DejaVu Sans, built in, where the file is
missing). The taskbar has the launcher's button (the KolibriOS
hummingbird on a tile of the sheen), a button for every program's window
(activate, minimize; the right button: Pin to the bar / Restore / Minimize /
Close / End Process; the active one has a line of the accent under it) -
pinned programs keep an icon right after the launcher's button, which starts
them and, while they run, is their window's button (dragged along the bar,
an icon changes places with the others; `nectar.ini`'s `[pinned]`, written
next to the program) - the
notification area - the system monitor (the processor's load of the last
seconds as thin bars), the sound (a speaker, its waves the volume; only with
a sound card), the network (four bars, lit while packets flow), the keyboard
layout (Ctrl+Shift or Shift+Shift goes to the next one, from `lang.ini` and
`keymap.key` as `@TASKBAR` does), the clock (with the seconds, if
wanted) and next to it the notifications' bell - and at its right end a slim
button that minimizes every window and, clicked again, brings them back.
Shortcuts on the desktop (a click selects, a double click starts, the right
button opens `icon.ini`'s menu) have their labels on dark translucent pills;
dragged, a shortcut follows the pointer as a raised tile and takes the
nearest free cell of `@ICON`'s grid where it is let go, and `icon.ini`
keeps it there. Alt+Tab shows a card in the middle of the screen with a tile
per window, the latest used first: Tab (Shift+Tab) moves on (back), letting
Alt go switches, Alt+Esc leaves things as they were. Shutting down dims the
screen behind a card with three round choices: Restart kernel, Shut down and
Restart (fn 18.9). Win, Ctrl+Esc, Alt+F4 and Ctrl+Alt+F12 work as with
`@TASKBAR`. It replaces `@TASKBAR`, `@MENU` and `@ICON`: start it from
`/sys/settings/autorun.dat` in place of `/SYS/@TASKBAR` and it ends those
three when they run.

The launcher stands over the bar: a darker rail at the left - the places
(Computer, System, RAM disk, Settings, Processes, Documentation, Search,
Run...) and one power button at its foot, which asks how to end - and the
programs at the right: the system's `menu.dat`, its main menu right there,
the submenus opening as cascades on hover after a delay. Icons are drawn at
their own size (18x18 in menus, 32x32 on the desktop), never scaled. The
keyboard works too: arrows (Left / Right between the rail and the programs),
Tab between the columns, Enter, Esc and the first letter of an item.
`apps/nectar/startmenu.py` is the same launcher as a program of its own for the
stock taskbar: install it as `/sys/@MENU` (or set `Menu=` in `taskbar.ini`);
the taskbar's button opens it and closes it again.

The icons of the notification area open flyouts - panels over the bar that
go as a menu goes (a click elsewhere, Esc, another window taking the focus):

- the system: the processor's load and the memory in use over the last
  minute (charts), the clock rate, how many processes, the busiest of them
  now, how long the system has run; "Processes" starts `cpu`;
- the sound: a round button that mutes, a slider (click, drag, the wheel,
  the arrows) and the level - the SOUND driver's master volume (its IOCTL 6
  and 7), written to `volume.dat` as `@VOLUME` keeps it, so its hotkeys go on
  from there (KolibriOS gives the wheel to the active window only: over the
  speaker it turns the volume while the shell's window is active);
- the network's details: a tab per network card (the loopback only when there
  is no other), its state, link speed, IPv4 address, mask, gateway, DNS
  server and MAC address, and two cards - received and sent: bytes, packets
  and bytes a second, looked at again every second; "Network settings" starts
  `netcfg` (also on the icon's right button);
- the calendar: the time with its seconds going, today's date, and a month
  (today on a disc of the accent; the chevrons, Left / Right or PageUp /
  PageDown turn the months, a click on the month's name or Home comes back);
- the keyboard layouts: the languages Ctrl+Shift goes through (`lang.ini`'s
  `[comkey]`), each its letters and its own name (English, Русский,
  Українська ...), the current one checked; a click, or the arrows and
  Enter, switches to one; "Keyboard settings" starts `/sys/setup`.

Notifications are the system's own: what programs say through `@notify`
(`@notify "'Title\nText' -tI"`, notify3's parameters: a title, a symbol -
error, warning, done, information, network, mail, download, sound,
application, folder, component -, `d` for one that stays until it is
clicked, `c` for one a click does not close) and what the shell says itself.
Each shows as a toast over the bar's right end - a card in the look of the
flyouts with the symbol drawn on a disc of its color -, the newest over the
others (three at a time); it stays five seconds and one more a line (longer
while the pointer is on it), then sinks behind the bar into the bell, which
lights in the accent with their number; a click on it closes it at once.
When one goes, those over it come down in its place. The bell opens the
list - the latest first, those that came since it was last looked at marked
with a line of the accent, each with its time and an x; "Clear all", the
wheel scrolls - and opening it brings the toasts showing into it. A toast is
a window of its own (a thread has one window, and the shell's is a
rectangle round its panels, so a toast in it would freeze a band as wide as
the screen for as long as it shows): the shell draws the card over the
screen beneath it and `notify`, a small program next to it, shows the
picture, sinks it and says so (IPC; the shell's pid in a shared area).
`notify` started as `@notify` is hands the notification to the shell - or,
without one, to the system's notifier; Make the default shell puts at
`/sys/@notify` a program of some 150 bytes that starts `notify` with the same
parameters (`notify` itself, 20 KB, would take the floppy image's last
room), keeping the system's notifier as `/sys/notify3`. A progress bar
(`p`) stays notify3's: its program drives it through notify3's own shared
area.

Run... (the launcher's place, the bar's menu) opens the Run panel over the
launcher's button: a line to type a program, a folder or a document into,
its parameters after it, and under it what the line may become - the lines
run before that start with it, the menu's programs whose title or file name
does, and the entries of the folder the path being typed is in (`/sys` for
a bare name, as in `menu.dat`). Tab takes the chosen suggestion (or the
first) - a folder's ends with `/`, so its entries come next -, Up and Down
choose, Enter runs, Ctrl+V pastes, Esc closes; Russian letters are typed as
the keyboard's layout gives them. Paths may hold spaces
(`/sys/File Managers/Eolite /hd0/1`: the program is the longest start of the
line that exists); a folder opens in Eolite, a document with the program
meant for it (`/sys/@open`); what is not there is said in red. The last
twenty lines are `nectar.ini`'s `[history]`.

Taskbar Settings (the bar's menu) is a card for the shell itself: the
launcher button's label, the accent (five palettes: emerald, sapphire,
amethyst, amber, coral - each a sheen of three colors), the size of the
text (13 to 16 px), the clock's seconds, which icons the notification area
shows, Windows' **In Nectar's colors** (below), a link that opens
`nectar.ini` in the editor - and Startup's **Make the default shell** (once
it is, "Starts with the system"), which does its part at once and says how
it went in a notification. Apply writes `nectar.ini` (`[launcher]`, `[bar]`)
and `kui.ini` (`[look]`: the accent and the text's size are kui's, shared by
every kui program in that folder) and starts the shell again - kui reads
`kui.ini` as it is loaded, so the whole interface takes the new look.

**In Nectar's colors** dresses every window of the system as Nectar: a
KolibriOS skin (`lib/kui/skin.py`) - graphite captions with a line of the
accent under the active window's, the minimize and close buttons soft
plates (close red), frames with a dark outline and a thin light edge - and
the color table that comes with a skin, which the system's programs draw
with: graphite work areas, light text, buttons of the accent (Calc, Eolite,
RDSAVE, the stock taskbar ... take it; a program that draws with colors of
its own keeps them). Apply makes the skin in the accent chosen, writes it
next to the shell as `nectar.skn`, puts it on at once (fn 48.8: every window
is drawn again) and names it in `/sys/settings/system.ini`'s `[style]
skin=` - ESKIN, which `autorun.dat` starts, puts on that skin at every boot
(that line and nothing else of the file changes; RDSAVE opens to keep it on
a system booted from an image). Unchecked, the line goes and the system's
own skin is back. The release has the skin as files too - `nectar.skn` and
`nectar.dtp` (the colors alone) in `nectar.zip`, for the system's own
SKINCFG or `system.ini` by hand.

What they show is the system's own: the programs come from
`/sys/settings/menu.dat` (as `@MENU`'s do), the desktop's shortcuts and their
menu from `/sys/settings/icon.ini` (as `@ICON`'s). The shell's own settings
are in `nectar.ini` (`apps/nectar/nectar.ini`; next to the program, then
`/sys/settings`, else built-in defaults): the labels of the launcher's button
and of the power button, and the rail's places, one a line -
`title=program|parameters|icon` (an `icons16.png` number), `-` for a
separator - with `[launcher_ru]` and `[places_ru]` for a Russian system, and
`[pinned]`, the programs pinned to the bar, in the same form, `[bar]` (the
clock's seconds, the notification area's icons) and `[history]` (the Run
panel's lines): the shell rewrites those sections (and only those; Taskbar
Settings only its keys) of the `nectar.ini` next to it, made from the one
the settings came from if it is not there yet. A window's
program can be pinned when the shell knows where it is: a `menu.dat` item or
a desktop shortcut of the same file name, or a program in `/sys`
(KolibriOS does not say where a process was started from). A
place whose program is not there is not shown, and what the rail has the
programs' column does not repeat (Settings, Search, Run..., `menu.dat`'s
Shut down).

How it works: a KolibriOS thread has one window, so the bar, the launcher, its
cascades, context menus, flyouts and tooltips are panels of one always-on-top
window. Everything is drawn with `kgfx` into a canvas per panel; under a
panel's shadow and anti-aliased corners goes what is beneath it (lower panels,
or the screen read with fn 36 before the menu appeared). The desktop's
shortcuts are not windows: like `@ICON`'s they are put on the screen's
background layer (fn 25) and drawn again when the kernel redraws the
background (event 5); clicks reach them when the pixel's owner (fn 34) is the
desktop. A part of the desktop is drawn again as one picture made by the
shell - the wallpaper (the background image mapped into the program, fn 15.6)
with the shortcuts over it - never by asking the kernel, which would wipe
every shortcut there first: a selection moving from one shortcut to another,
and a shortcut being dragged - each move puts one picture, the desktop with
the tile at its new place, over its old and new places - leave nothing
behind and make nothing blink. While the desktop itself is the active window (a click on it makes it
so), KolibriOS redraws neither the background nor the windows that a
shrinking window uncovers - the closed menus would stay on the screen - so the
shell's window takes the focus before it shrinks. No threads, no other
processes: the launcher is drawn when the shell starts and opens at once.

## Maps

![Maps: a search for Red Square, the places found](apps/maps/screenshots/search.jpg)

`apps/maps/maps.py` is a map of the world: OpenStreetMap's standard map, or
the Earth from space - [EOxCloudless](https://cloudless.eox.at) 2024,
Sentinel-2's photos without the clouds (10 m a pixel) -, and a search of
places by name with OpenStreetMap's Nominatim, all of it over https:
plainpy's `requests` and `ssl` (TLS 1.2, mbedTLS) on KolibriOS itself. The
mouse drags the map, the wheel zooms round the pointer, a double click zooms
in there; `+` and `-` (PageUp, PageDown, the buttons at the top right) zoom,
the arrows move it; the card at the bottom right (or Tab) shows the map or
the photos. Typing goes to the search (Russian letters as the keyboard's
layout gives them): Enter finds the places of that name in the system's
language - the first one is shown at once with a pin, Up and Down or a click
go to the others -, Esc closes the list, then leaves the field. The window
can be resized and maximized; the scale bar, the coordinates of the middle
and the credits the licences ask for are at the bottom.

| | |
|---|---|
| ![where it opens](apps/maps/screenshots/europe.jpg) | ![the middle of Moscow](apps/maps/screenshots/city.jpg) |
| ![Baikal from space](apps/maps/screenshots/baikal.jpg) | ![the Earth, the window maximized](apps/maps/screenshots/earth.jpg) |

`maps [lat lon [zoom]]` opens it elsewhere than over Europe and Russia. It
needs, next to it, `mbedtls.obj` (plainpy's TLS library for KolibriOS; also
`/sys/lib` or `/kolibrios/lib`) and `cacert.pem` (the authorities the
servers' certificates are checked by: curl.se's; also `/sys/settings` or
`/kolibrios/etc`) - `maps.zip` has both - and the network up.

How it works: the window never waits for the network. Compiled programs have
no threads, so `maps` starts itself again as the fetcher (`maps --fetch <pid>
<language>`, a process without a window; `osmmap/link.py`). After each frame
the window tells it which tiles it wants, the nearest to the middle first -
the list replaced as the map moves -, and the fetcher gets them over https,
decodes them (in QEMU without KVM a fifth of a second for a map's PNG, about
twice that for a photo's JPEG) and sends the pixels back, a tile a message:
KolibriOS's IPC (fn 60) copies them into the window's area and wakes it
(`kui.window`'s `on_ipc`). A drag, a click, the wheel are answered at once,
the tiles are drawn as they come; the searches go the same way, and the
fetcher pauses three seconds when the network fails and ends with the
window. A `requests.Session` per server keeps its connection open, so the
TLS handshake is made once. The map is drawn into one canvas the size of the
window (`kgfx`, the tiles pasted row by row) and put on it in one call: a
drag does not flicker. A tile not there yet shows a piece of a tile of a
smaller zoom, enlarged, or four of the next zoom, made smaller, while its own
comes; the tiles are kept in memory, the longest out of sight forgotten
first. Over the tiles, kui's cards: `SearchField`, `ListEntry`, `Tab`,
`card`, the pin a `Stamp` of `glyphs.marker`. The package
`apps/maps/osmmap/`: `geo` (Web Mercator), `tiles`, `places` (Nominatim's
JSON read into a dataclass, as compiled code reads JSON), `net` (the https),
`link` (the fetcher and what it and the window say), `view` (the drawing,
the layers, what is where).

The tiles come from OpenStreetMap's tile servers (their
[policy](https://operations.osmfoundation.org/policies/tiles/): a User-Agent
that names the program, no bulk downloading - a person dragging a map
asks for a few) and from EOX (EOxCloudless 2024: CC BY-NC-SA 4.0, for
non-commercial use, with its credit); the search from
[Nominatim](https://operations.osmfoundation.org/policies/nominatim/) (one
search a second at most).

## kui

kui is a toolkit for KolibriOS programs written in PlainPy, compiled or in the
interpreter (plainpy runs on KolibriOS too). It has two levels. `kui.window`
(what `import kui` gives) describes a window with decorators - a paint
function, buttons, keys (`on_key`, `on_key_code`, `on_any_key`), clicks,
double clicks, drags and their end, the wheel, IPC messages (`on_ipc`), UTF-8
text, and `on_idle`: work done between events (a function that says when it
wants to run again - at once, in n/100 s, or after the next event);
`@window(..., sizable=True)` makes a window the user can resize and maximize,
drawn in its client area's coordinates (`win.width` x `win.height`):

```python
from kui import Window, window

count = 0

@window("Counter", 100, 100, 260, 160)
def counter(win: Window) -> None:          # paints the window; `counter` is the Window
    win.bar(20, 30, 220, 20, 0x334455)
    win.text(24, 36, "Count: " + str(count))

@counter.button("+1", x=20, y=80)
def increment() -> None:
    global count
    count += 1
    counter.redraw()

@counter.on_key("q")
def leave() -> None:
    counter.close()

counter.run()
```

(`apps/counter/counter.py` in full; `apps/files/files.py`: a list with
keyboard, mouse and wheel navigation and a panel with the entry's size,
dates, attributes and the first lines - or bytes - of a file; and
`apps/maps/maps.py`: a sizable window, drags, the wheel, a process of its own
for the network, talked to by IPC.) Everything
else in kui is a drawn level, the one Nectar is made of. The interface is made of `lib/kui`, a toolkit for such programs. Every
panel draws itself - its background, then each row through the widget the row
carries (a menu item, a tab, a slider, the clock ...), so a new kind of row
is a small `Widget` subclass; a `Surface` is one window made of panels, and
`MenuSurface` adds menus to it:

| `kui` module | |
|---|---|
| `window` | the decorator level: `@window(...)`, buttons, keys, clicks, drags, the wheel, idle work, sizable windows (`import kui`) |
| `theme`, `look`, `fonts`, `item` | the look (colors, gradients, sizes, the accent's palettes); `kui.ini`'s `[look]` (accent, text size); the fonts (the system's Tahoma or DejaVu); `Item`: a row of a menu |
| `panel`, `surface` | `Panel`, `Row`, `Widget`; one window made of panels: shadows, corners over what is beneath, hot rows |
| `menus`, `popup` | menus on a surface: hover delays, cascades, context menus, the keyboard; their panels and placing |
| `flyout`, `tooltip`, `dialog` | a bar icon's panel; tooltips; a modal card over the dimmed screen with round choices |
| `widgets`, `slider`, `chart` | separators, push and text buttons, tabs, check boxes, color swatches, `ListEntry` (a thing found: its name, and dim under it where it is); a slider; percents over time |
| `textinput` | `LineEdit` (a line being typed: cp866 letters, the caret's keys, a paste), `TextField` (its field, scrolled to the caret), `SearchField` (one with a magnifier) |
| `draw`, `band`, `glyphs`, `icons` | drawing helpers - `card` (a card floating over a picture, its shadow under the rounded corners too), `Stamp` (a shape worked out once, laid down in any color) -; a gradient per row; drawn symbols (power, restart, search, a cross, a map's pin ...); the system's icon strips |
| `skin` | a KolibriOS skin (`.skn`) and color table (`.dtp`) in kui's look and accent: what every window of the system wears |

and the package `apps/nectar/nectar/` is the desktop's own, by what it is about:

| `nectar` module | |
|---|---|
| `config`, `system`, `theme` | `nectar.ini`, `menu.dat`, `icon.ini`, defaults; starting programs; the shell's sizes |
| `autorun` | Make the default shell: `autorun.dat` rewritten byte for byte, the `@notify` stub (machine code made there) |
| `notes/` | notifications: `note` (`@notify`'s parameters, the bell's list), `toast` (drawn over the screen, stacked, moved down), `center` (the bell, its list), `card` (symbols, wrapped lines), `area` (the shared areas and messages), `window` and `forward` (`notify.py`'s two parts) |
| `menu/` | `startpanel` (the launcher and its rows' widgets), `controller` (kui's menus with the launcher), `standalone` |
| `taskbar/` | `bar` (the panel), its widgets `startbutton`, `pins` (pinned programs, dragged), `tasks`, `sysmon`, `volume`, `network`, `language`, `clock`, `showdesktop`; `contextmenu`, `switcher` (Alt+Tab) |
| `flyouts/` | `system`, `sound`, `netinfo` (the network's details), `calendar`, `layouts` (the keyboard's), `settings` (Taskbar Settings) |
| `style` | Nectar's skin on every window: made, put on, named in `system.ini` for the next boot, taken off |
| `run/` | the Run panel: `files` (the disks, a folder read once), `suggest` (history, programs, paths), `command` (what a line runs), `panel` |
| `desktop/` | `desktopicons`, `drag` |
| `dialogs/` | `shutdown` |
| `shell` | all of it together, the event loop, hotkeys |

## Graphics: `lib/kgfx.py`, `lib/png.py`, `lib/jpeg.py`

`kgfx` draws 32-bit pictures off-screen and puts them into a KolibriOS window
in one call (fn 65), flicker-free; it works compiled and in the interpreter,
and everything but the two KolibriOS calls runs on any system
(`Canvas.save_bmp` writes a picture to look at):

- `Canvas(w, h)`: pixels `0x00RRGGBB`; `fill`, `fill_alpha`, `hline`,
  `vline`, `frame`, `gradient`, `gradient_stops` (any number of stops),
  anti-aliased `round_rect`, `round_frame`, `ellipse` and `cover` (any
  `inside(x, y)` test, supersampled), `triangle`, `shadow` (a soft drop
  shadow), `image` (with its alpha channel), `paste` (an opaque picture, row
  by row), `canvas` (copy a part), `text`
  (also oblique), `blit` (to the window, fn 65 with a row offset) and `grab`
  (from the screen, fn 36);
- `Image(w, h)`: B G R A pixels - `Image.from_png`, `from_memory` (an icon
  strip the system shares), `sub`, `keyed` (a color made transparent, a flat
  shadow color made translucent), `scaled` (area-averaging down, bilinear up,
  weighted by alpha), `tinted`;
- `Font`: bitmap fonts with 16 levels of coverage per pixel (stored at
  1 bit a pixel when they are not anti-aliased, 4 when they are), `width` and
  `fit` (shortened with an ellipsis). `tools/mkfont.py` (Pillow and fontTools,
  only there) renders TrueType fonts into such a module:
  `lib/kgfx_tahoma.py` holds Wine's Tahoma (LGPL) at 11 px - from its
  embedded bitmap strike, crisp as Windows XP drew it - in regular and bold,
  and a 15 px anti-aliased bold; Latin, Cyrillic and a few symbols.
  `lib/kfont.py` makes such fonts of KolibriOS's own bitmap fonts
  (`.kf`, as `/sys/fonts/tahoma.kf`: sizes 9 to 22 px, cp1251's glyphs) when
  a program starts - with FB2Reader's faint pixels in a diagonal's steps and
  a bold face drawn twice; `tests/kfont_glyphs.py` reads a `.kf` made
  up in memory.

`png` decodes PNG files in PlainPy over the standard library's `zlib`: every
color type and bit depth, palettes with `tRNS`, Adam7 interlacing.
`tests/kgfx_draw.py` checks both (pixel values and checksums, the same
on every target and in the interpreter). `jpeg` decodes baseline JPEGs -
what tile servers and most cameras write: gray and YCbCr, any sampling of
the colors, restart intervals, several scans - with libjpeg's accurate
integer inverse DCT and its smoothing of colors kept at half the resolution
(`jpeg.decode(data)`: `png.decode`'s B G R A pixels); progressive ones raise
`ValueError`. `tests/jpeg_decode.py` holds pictures made by libjpeg-turbo's
`cjpeg` and the pixels its `djpeg` gives them: 4:4:4 and gray come out the
same to the bit, 4:2:0 at most 2 off (the smoothing rounds a little
differently).

## The other programs

- `apps/files`: a file browser - Up / Down / PgUp / PgDn / Home / End or
  the wheel move, Enter or a double click opens, Backspace goes up.
- `apps/counter`: a count, +1 and Reset (q closes it) - the smallest kui program.
- `apps/maps`: the map of the world (above).

A new program is a folder of `apps/` with its main file, a line of the
`Makefile` (`$(eval $(call app,NAME,apps/NAME/NAME.py,))`) and, if it
should be in a release, a name in `APPS`.

## Building

What it takes: [plainpy](https://github.com/c4simba/plainpy) - a release
(`plainpy_amd64.deb`, `plainpy.x86_64.rpm`, a tarball) or its sources and
`sudo make install` - and fasm on the PATH (`sudo apt install fasm`).

```sh
make                    # build/kolibrios: nectar, startmenu, notify, counter, files, maps; nectar.skn, nectar.dtp
make nectar             # one of them
make test               # the tests, compiled for this machine
make test TARGET=interp # ... in the interpreter
make dist               # build/release: kolibrios-apps.zip and a zip of each program
make run                # KolibriOS in QEMU, build/kolibrios as /hd0/1 (tools/run-kolibrios.sh)
```

(`PLAINPY=path/plainpy`, `FASM=path/fasm` take others than those on the PATH.)
`make dist` and `make run` put next to `maps` what its https needs:
`cacert.pem` (curl.se's, downloaded into `build/`) and - with
`MBEDTLS=path/mbedtls.obj` - plainpy's TLS library for KolibriOS (in plainpy's
KolibriOS zip, or made by its `make kolibri-tls`); the release workflow takes
it from plainpy's latest release - or, while that has none, makes it from
plainpy's sources (LLVM 15).
The programs are compiled with `lib/` on the module path
(`PLAINPYPATH=lib plainpy --compile --target kolibri apps/nectar/desktop.py`).

`tests/` run without KolibriOS, offscreen, both in the interpreter and
compiled (`tests/run_tests.sh`; expected outputs in `tests/expected`):
`nectar_menu` the launcher (configuration, layout, keyboard navigation,
drawing), `nectar_tray` the monitor's arithmetic, the volume's mapping, the
Alt+Tab card, a dragged shortcut's cell and `icon.ini`, pins moved and the
layouts' flyout, `nectar_run` the Run panel (the line, suggestions over a
made-up disk, what lines run, the history), `nectar_settings` the settings
card and the ini keys it writes, `nectar_style` the windows' skin
(`system.ini`'s line set, replaced, taken away; the `.skn` read back as the
kernel reads it), `nectar_notes` the notifications (`@notify`'s
parameters, toasts, the bell and its list, `autorun.dat` made to start
Nectar), `maps_view` the map (Web Mercator, the scale, the tiles from a
made-up server - one that cannot be reached, one without the tile, one that
answers nonsense -, previews, the window drawn, the places found, the
layers), `kgfx_draw`, `jpeg_decode` and `kfont_glyphs` the graphics. `startmenu_kolibri` runs the stand-alone launcher on the scripted
KolibriOS of plainpy's `tests/x86run.py`:
`TARGET=kolibri RUN="python3 <plainpy>/tests/x86run.py" make test`.

GitHub Actions (`.github/workflows/build.yml`) builds and tests it on every
push with plainpy's latest release; a tag `v1.2.3` publishes the release
1.2.3 with the zips above. `.github/workflows/pages.yml` publishes the
website - `site/index.html` with `apps/nectar/screenshots/` - on GitHub Pages
(once, in the repository's Settings -> Pages: Source "GitHub Actions"),
again for every release, which it names.

## Layout

```text
apps/nectar/          Nectar: desktop.py, startmenu.py, notify.py, the package nectar/, nectar.ini, screenshots/
apps/maps/            Maps: maps.py, the package osmmap/, screenshots/
apps/files/           the file browser
apps/counter/         the smallest kui program
lib/kui/              the toolkit
lib/kgfx.py           pictures, fonts, drawing (kgfx_sans.py, kgfx_tahoma.py: fonts made by tools/mkfont.py)
lib/png.py            PNG decoding
lib/jpeg.py           JPEG decoding (baseline)
lib/kfont.py          KolibriOS's .kf fonts as kgfx fonts
tests/                the tests and their expected outputs
site/                 the website (GitHub Pages: .github/workflows/pages.yml)
tools/                mkfont.py (TrueType fonts into kgfx modules), mkskin.py (Nectar's skin), run-kolibrios.sh (QEMU)
```

`import kolibri` - the KolibriOS system functions - is plainpy's own
(`lib/kolibri.py` of plainpy, installed with it).

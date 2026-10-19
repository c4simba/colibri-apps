# store - kstore, an installer of programs for KolibriOS, made of:
#
#   registry   the registry - the programs, where each comes from, how it is
#              unpacked -: its JSON read (and written, by the tool), dates,
#              what a program's date says (not installed, older, current)
#   net        the registry's text and the programs' archives over https
#              (plainpy's requests), a piece at a time
#   jobs       what the worker does - the registry got, a program installed
#              (lib/unzip) - and the lines of text that ask and tell how it goes
#   view       the window drawn: the programs' cards, their buttons, how an
#              install goes; what is at a point of it
#
# apps/kstore/kstore.py is the program: the window (kui), its keys and mouse,
# the worker (lib/worker: kstore started again without a window, so the
# window never waits for the network). tools/kstore_registry.py writes the
# registry (site/kstore.json).

# osmmap - a map of the world for KolibriOS, written in PlainPy: OpenStreetMap's
# tiles, the Earth from space (EOxCloudless) and OpenStreetMap's search over
# https (plainpy's requests and ssl), drawn with kgfx in kui's look. The
# program is apps/maps/maps.py; what it is made of:
#
#   geo       Web Mercator: degrees and world pixels, tiles, wrapping round the
#             world, the scale bar's round distance, the zoom a box fits at
#   tiles     the tiles of a layer in memory (the longest out of sight
#             forgotten first), the ones in sight asked for, nearest to the
#             middle first; PNGs and JPEGs decoded (lib/png.py, lib/jpeg.py);
#             previews from the tiles of the zooms next to it
#   places    a place Nominatim found: the fields read from its JSON, its
#             name, where it is, the zoom it fits at
#   net       https: the map's tiles, the photos, the search - a kept-open
#             connection to each server, what went wrong in a few words, the
#             credits the licences ask for
#   link      the fetcher: the program run again as a process of its own that
#             does the waiting (https, decoding) and sends the window decoded
#             tiles and places by IPC; the messages; the window's side of it
#   view      the window drawn: the tiles, the pin, the cards (the search and
#             the places found, the zoom, the layers, the scale, the credit,
#             the trouble); what is at a point; Layer: a kind of map

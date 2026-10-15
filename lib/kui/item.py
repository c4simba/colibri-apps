# kui.item - Item: what a row of a menu (or any list of things to run) is.

class Item:
    """An entry of a menu, a list, a desktop: something to run (run, args -
    what they mean is the program's), a submenu (items) or a separator. icon:
    an 18x18 icon of ICONS18 (kui.icons); icon32: a 32x32 one of ICONS32;
    glyph: a symbol kui draws (kui.glyphs.symbol: "power", "restart", ...);
    bold: a bold title; pos: a place for it (a desktop shortcut's: x, y,
    negative from the right / bottom edge); key: its name in the file it came
    from (a section of an ini file)."""

    def __init__(self, title: str = "", icon: int = -1, icon32: int = -1, glyph: str = "",
                 run: str = "", args: str = "", bold: bool = False, separator: bool = False,
                 items: list["Item"] = None, pos: list[int] = None, key: str = ""):
        self.title = title
        self.icon = icon
        self.icon32 = icon32
        self.glyph = glyph
        self.run = run
        self.args = args
        self.bold = bold
        self.separator = separator
        self.items: list[Item] = items if items is not None else []
        self.pos: list[int] = pos if pos is not None else []
        self.key = key

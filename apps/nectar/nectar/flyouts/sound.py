# nectar.flyouts.sound - the volume, opened by the notification area's
# speaker: a round button that mutes and unmutes, a slider (click or drag
# it; the wheel, the arrows, PageUp / PageDown turn it, M or space mutes) and
# the level.
#
#   Sound                                  72 %
#   ( <)) )   ==================O--------
import kolibri as k
from kgfx import Canvas
from kui.fonts import SANS_BIG
from kui import glyphs
from kui.panel import Row, Widget
from kui.flyout import Flyout, anchored
from kui.slider import Slider
from ..config import Item
from ..taskbar.volume import Sound
from ..theme import RAISED, SUNKEN, LINE, TEXT, TEXT_DIM, TEXT_FAINT, ACCENT, SHEEN, DANGER, TASK_DOWN

W = 300
H = 104
R_MUTE = 60
R_SLIDER = 61
TRACK_X = 66               # the slider's track, panel coordinates
TRACK_Y = 72

class MuteButton(Widget):
    """The speaker on a round plate: struck out and reddish when muted."""

    def __init__(self, sound: Sound):
        self.sound = sound

    def paint(self, cv: Canvas, row: Row, hot: bool, opened: bool) -> None:
        muted = self.sound.muted
        cv.ellipse(row.x, row.y, row.w, row.h, TASK_DOWN if hot else RAISED)
        if muted:
            cv.ellipse(row.x, row.y, row.w, row.h, DANGER, 60)
        glyphs.speaker(cv, row.x + (row.w - 20) // 2, row.y + (row.h - 20) // 2, 20, TEXT,
                       self.sound.waves() if not muted else 0, muted)

class SoundPanel(Flyout):
    def __init__(self, level: int, x: int, bottom: int, screen_w: int, russian: bool, sound: Sound):
        pos = anchored(W, H, x, bottom, screen_w)
        super().__init__(level, "Звук" if russian else "Sound", pos[0], pos[1], W, H)
        self.sound = sound
        self.slider = Slider(TRACK_X, TRACK_Y, W - TRACK_X - 24)
        self.dragging = False
        self.rows.append(Row(Item(title="mute"), R_MUTE, 16, TRACK_Y - 18, 36, 36, MuteButton(sound)))
        self.rows.append(Row(Item(title="volume"), R_SLIDER, TRACK_X - 12, TRACK_Y - 18, self.slider.w + 24, 36, self.slider))

    def paint_content(self, cv: Canvas) -> None:
        s = self.sound
        self.slider.value = s.level                  # (the rows are drawn after this)
        self.slider.off = s.muted
        text = str(s.level) + " %"
        cv.text(SANS_BIG, W - 18 - SANS_BIG.width(text), 14, text, TEXT_FAINT if s.muted else TEXT_DIM)

    def click(self, i: int) -> str:
        if self.rows[i].kind == R_MUTE:
            self.sound.toggle_mute()
            self.sound.save()
        return ""

    def pointer(self, x: int, y: int, pressed: bool, held: bool, released: bool) -> bool:
        """The slider follows the pointer from a press on it until the button is let go."""
        if pressed:
            r = self.rows[1]
            self.dragging = r.x <= x < r.x + r.w and r.y <= y < r.y + r.h
        if not self.dragging:
            return False
        changed = False
        if pressed or held:
            changed = self.sound.set_level(self.slider.value_at(x))
        if released or not held:
            self.dragging = False
            self.sound.save()
        return changed or pressed

    def capturing(self) -> bool:
        return self.dragging

    def wheel(self, steps: int) -> bool:
        if self.sound.set_level(self.sound.level - steps * 5):
            self.sound.save()
            return True
        return False

    def key(self, code: int) -> bool:
        s = self.sound
        if code == k.KEY_LEFT or code == k.KEY_DOWN:
            changed = s.set_level(s.level - 5)
        elif code == k.KEY_RIGHT or code == k.KEY_UP:
            changed = s.set_level(s.level + 5)
        elif code == k.KEY_PAGE_DOWN:
            changed = s.set_level(s.level - 20)
        elif code == k.KEY_PAGE_UP:
            changed = s.set_level(s.level + 20)
        elif code == 32 or code == ord("m") or code == ord("M"):
            s.toggle_mute()
            changed = True
        else:
            return False
        if changed:
            s.save()
        return changed

    def update(self) -> bool:
        return self.sound.read()

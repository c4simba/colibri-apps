# nectar.taskbar.contextmenu - what the right button offers on the bar.
# Items whose run starts with "@" are the shell's own actions:
#   @restore @minimize @close @kill    the task the menu is for
#   @pin @unpin @start                  pin its program to the bar, unpin, start a pinned one
#   @desktop                            minimize every window (or restore them)
#   @shutdown                           turn the computer off
#   @netinfo                            the network's details (the flyout)
from ..config import Item, separator
from .tasks import Task
from . import network

PIN_NONE = 0               # (what for_task offers: nothing, Pin, Unpin)
PIN_CAN = 1
PIN_DONE = 2

def pin_item(state: int, russian: bool) -> list[Item]:
    if state == PIN_CAN:
        return [Item(title="Закрепить на панели" if russian else "Pin to the bar", run="@pin")]
    if state == PIN_DONE:
        return [Item(title="Открепить от панели" if russian else "Unpin from the bar", run="@unpin")]
    return []

def for_task(t: Task, russian: bool, pin: int = PIN_NONE) -> list[Item]:
    items: list[Item] = []
    pinning = pin_item(pin, russian)
    if len(pinning) > 0:
        items.extend(pinning)
        items.append(separator())
    if t.minimized:
        items.append(Item(title="Восстановить" if russian else "Restore", icon=52, run="@restore"))
    else:
        items.append(Item(title="Свернуть" if russian else "Minimize", icon=37, run="@minimize"))
    items.append(separator())
    items.append(Item(title="Закрыть" if russian else "Close", run="@close", bold=True))
    items.append(Item(title="Завершить процесс" if russian else "End Process", icon=63, run="@kill"))
    return items

def for_pin(it: Item, russian: bool) -> list[Item]:
    """A pinned program that does not run."""
    return [Item(title=it.title, icon=it.icon, run="@start", bold=True), separator()] + pin_item(PIN_DONE, russian)

def for_bar(russian: bool) -> list[Item]:
    return [Item(title="Показать рабочий стол" if russian else "Show the Desktop", icon=61, run="@desktop"),
            Item(title="Процессы" if russian else "Processes", icon=47, run="cpu"),
            Item(title="Выполнить..." if russian else "Run...", icon=53, run="run"),
            Item(title="Параметры панели..." if russian else "Taskbar Settings...", icon=60, run="@settings"),
            separator(),
            Item(title="Выключение..." if russian else "Turn Off...", icon=4, run="@shutdown")]

def for_network(russian: bool) -> list[Item]:
    return [Item(title="Состояние" if russian else "Status", icon=47, run="@netinfo", bold=True),
            Item(title="Настройка сети" if russian else "Network Settings", icon=25, run=network.SETTINGS)]

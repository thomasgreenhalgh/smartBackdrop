"""Smart Backdrop for Nuke.

Wraps the selected nodes in a padded, pastel backdrop with a centred bold
title and description. Backdrops are purely visual: no callbacks and nothing
in their knobChanged. The "Edit title and colour" button carries its own copy
of the edit code, so it works for anyone who opens the script, plugin or not.

Optional, local only: enable_grab_handles() shows a large MOVE handle beside
the selected backdrop. Handles are temporary and never saved into scripts.

menu.py:
    import smartBackdrop
    nuke.menu('Nuke').addCommand('Edit/Smart Backdrop', smartBackdrop.create, 'ctrl+alt+b')
    smartBackdrop.enable_grab_handles()
"""

import traceback

import nuke

try:
    from PySide6.QtCore import QTimer
except ImportError:
    from PySide2.QtCore import QTimer


# Everything the Edit button needs. It's executed here for the plugin and
# embedded verbatim in each backdrop's button, so keep it self-contained.
_EDIT_SOURCE = r'''
import html

import nuke

try:
    from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QGridLayout, QHBoxLayout,
                                   QLabel, QLineEdit, QPlainTextEdit, QPushButton, QButtonGroup)
    from PySide6.QtCore import Qt
except ImportError:
    from PySide2.QtWidgets import (QApplication, QDialog, QVBoxLayout, QGridLayout, QHBoxLayout,
                                   QLabel, QLineEdit, QPlainTextEdit, QPushButton, QButtonGroup)
    from PySide2.QtCore import Qt

PASTELS = [
    ("Pink", "#8A5A65"),
    ("Peach", "#8C6A55"),
    ("Butter", "#8A7F4E"),
    ("Mint", "#557A68"),
    ("Sage", "#66745A"),
    ("Sky", "#4F6F82"),
    ("Periwinkle", "#5C6488"),
    ("Lavender", "#6E5F86"),
    ("Lilac", "#805C7C"),
    ("Coral", "#8A5F57"),
    ("Aqua", "#4F7A78"),
    ("Grey", "#5E5E5E"),
]

TITLE_FONT_TAG = 7
TEXT_COLOR = 0xE8E8E8FF


def _hex_to_tile(hex_color):
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return (r << 24) | (g << 16) | (b << 8) | 0xFF


def _nearest_pastel(tile):
    def distance(hex_color):
        a = _hex_to_tile(hex_color)
        return sum(abs(((a >> s) & 0xFF) - ((tile >> s) & 0xFF)) for s in (24, 16, 8))

    return min((hex_color for _, hex_color in PASTELS), key=distance)


class BackdropDialog(QDialog):
    def __init__(self, title="", description="", color=None, parent=None):
        super(BackdropDialog, self).__init__(parent or QApplication.activeWindow())
        self.setWindowTitle("Smart Backdrop")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Title"))
        self.title_edit = QLineEdit(title)
        self.title_edit.returnPressed.connect(self.accept)
        layout.addWidget(self.title_edit)

        layout.addWidget(QLabel("Description"))
        self.description_edit = QPlainTextEdit(description)
        self.description_edit.setFixedHeight(80)
        layout.addWidget(self.description_edit)

        layout.addWidget(QLabel("Colour"))
        grid = QGridLayout()
        grid.setSpacing(6)
        self.swatches = QButtonGroup(self)
        self.swatches.setExclusive(True)
        selected = color or PASTELS[0][1]
        for i, (name, hex_color) in enumerate(PASTELS):
            button = QPushButton()
            button.setCheckable(True)
            button.setFixedSize(48, 32)
            button.setToolTip(name)
            button.setProperty("hex_color", hex_color)
            button.setStyleSheet(
                "QPushButton { background-color: %s; border: 2px solid #3a3a3a; border-radius: 4px; }"
                "QPushButton:checked { border: 3px solid #ffffff; }" % hex_color
            )
            button.setChecked(hex_color == selected)
            self.swatches.addButton(button)
            grid.addWidget(button, i // 6, i % 6)
        layout.addLayout(grid)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("OK")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        layout.addLayout(buttons)

        self.title_edit.setFocus(Qt.OtherFocusReason)

    def values(self):
        checked = self.swatches.checkedButton()
        color = checked.property("hex_color") if checked else PASTELS[0][1]
        return self.title_edit.text().strip(), self.description_edit.toPlainText().strip(), color


def _ask(title="", description="", color=None):
    dialog = BackdropDialog(title, description, color)
    run = getattr(dialog, "exec", None) or dialog.exec_
    if not run():
        return None
    return dialog.values()


def _escape(text):
    # Labels are TCL-evaluated, so square brackets must not reach the label raw.
    return html.escape(text).replace("[", "&#91;").replace("]", "&#93;")


def _label_html(title, description):
    parts = []
    if title:
        parts.append('<b><font size="%d">%s</font></b>' % (TITLE_FONT_TAG, _escape(title)))
    if description:
        parts.append('<font size="3">%s</font>' % _escape(description).replace("\n", "<br>"))
    return "<center>%s</center>" % "<br>".join(parts)


def _apply_text(backdrop, title, description, color):
    backdrop["label"].setValue(_label_html(title, description))
    backdrop["tile_color"].setValue(_hex_to_tile(color))
    backdrop["note_font_color"].setValue(TEXT_COLOR)
    backdrop["sb_title"].setValue(title)
    backdrop["sb_description"].setValue(description)


def _edit(backdrop):
    result = _ask(backdrop["sb_title"].value(),
                  backdrop["sb_description"].value(),
                  _nearest_pastel(int(backdrop["tile_color"].value())))
    if result is not None:
        _apply_text(backdrop, *result)
'''

exec(_EDIT_SOURCE, globals())

EDIT_COMMAND = "exec(%r, {})" % (_EDIT_SOURCE + "\n_edit(nuke.thisNode())\n")

PAD_X = 120
PAD_TOP = 60
PAD_BOTTOM = 80

BASE_FONT_SIZE = 20
# Qt renders <font size="7"> at roughly 2.4x the base size.
TITLE_SCALE = 2.4

# Knobs from earlier versions of the plugin that respaced nodes on resize.
OBSOLETE_KNOBS = ("sb_layout", "sb_recapture", "sb_rect", "sb_respace", "sb_header")


# ---------------------------------------------------------------- geometry

def _node_rect(node):
    if node.Class() == "BackdropNode":
        w, h = node["bdwidth"].value(), node["bdheight"].value()
    else:
        w, h = node.screenWidth(), node.screenHeight()
    return node.xpos(), node.ypos(), int(w), int(h)


def _bounds(nodes):
    rects = [_node_rect(n) for n in nodes]
    return (min(r[0] for r in rects), min(r[1] for r in rects),
            max(r[0] + r[2] for r in rects), max(r[1] + r[3] for r in rects))


def _header_height(title, description):
    height = PAD_TOP
    if title:
        height += int(BASE_FONT_SIZE * TITLE_SCALE * 1.3)
    if description:
        height += int(BASE_FONT_SIZE * 1.4) * (description.count("\n") + 1)
    return height


def _text_width(title, description):
    title_w = len(title) * BASE_FONT_SIZE * TITLE_SCALE * 0.6
    desc_w = max([len(line) for line in description.splitlines()] or [0]) * BASE_FONT_SIZE * 0.55
    return int(max(title_w, desc_w)) + 2 * PAD_X


# ---------------------------------------------------------------- knobs

def _ensure_knobs(backdrop):
    knobs = backdrop.knobs()
    for name in OBSOLETE_KNOBS:
        if name in knobs:
            backdrop.removeKnob(knobs[name])

    if "smartBackdrop" not in knobs:
        backdrop.addKnob(nuke.Tab_Knob("smartBackdrop", "Smart Backdrop"))
    if "sb_edit" in knobs:
        knobs["sb_edit"].setValue(EDIT_COMMAND)
    else:
        backdrop.addKnob(nuke.PyScript_Knob("sb_edit", "Edit title and colour", EDIT_COMMAND))

    for name in ("sb_title", "sb_description"):
        if name not in knobs:
            knob = nuke.String_Knob(name, name)
            knob.setFlag(nuke.INVISIBLE)
            backdrop.addKnob(knob)


# ---------------------------------------------------------------- public

def create():
    nodes = nuke.selectedNodes()
    if not nodes:
        nuke.message("Smart Backdrop: select some nodes first.")
        return

    result = _ask()
    if result is None:
        return
    title, description, color = result

    left, top, right, bottom = _bounds(nodes)
    header = _header_height(title, description)
    width = max(right - left + 2 * PAD_X, _text_width(title, description))
    extra = width - (right - left + 2 * PAD_X)
    height = header + (bottom - top) + PAD_BOTTOM

    backdrops = [n for n in nodes if n.Class() == "BackdropNode"]
    z_order = min(n["z_order"].value() for n in backdrops) - 1 if backdrops else 0

    for node in nuke.selectedNodes():
        node.setSelected(False)

    backdrop = nuke.nodes.BackdropNode(
        xpos=int(left - PAD_X - extra / 2),
        ypos=int(top - header),
        bdwidth=int(width),
        bdheight=int(height),
        note_font_size=BASE_FONT_SIZE,
        z_order=z_order,
    )
    _ensure_knobs(backdrop)
    _apply_text(backdrop, title, description, color)
    backdrop.setSelected(True)
    return backdrop


def edit(backdrop):
    """Entry point for Edit buttons made by earlier versions; upgrades them first."""
    _ensure_knobs(backdrop)
    _edit(backdrop)


# ---------------------------------------------------------------- grab handles

HANDLE_KNOB = "sb_handle_for"
HANDLE_FONT_SIZE = 48
HANDLE_WIDTH = 170
HANDLE_GAP = 30
HANDLE_DEFAULT_COLOR = 0x5E5E5EFF

_handle_timer = None
_suppressed_for = None


def _is_handle(node):
    return HANDLE_KNOB in node.knobs()


def _make_handle(backdrop):
    color = int(backdrop["tile_color"].value()) or HANDLE_DEFAULT_COLOR
    handle = nuke.nodes.StickyNote(
        # Plain text: StickyNote sizes itself from the unstyled label, so
        # HTML like <b> renders wider than the note and wraps.
        label="MOVE",
        note_font_size=HANDLE_FONT_SIZE,
        note_font_color=TEXT_COLOR,
        tile_color=color,
    )
    owner = nuke.String_Knob(HANDLE_KNOB, HANDLE_KNOB, backdrop.name())
    owner.setFlag(nuke.INVISIBLE)
    handle.addKnob(owner)
    handle.setXYpos(backdrop.xpos() - HANDLE_WIDTH - HANDLE_GAP, backdrop.ypos())
    return handle


def _delete_handles(handles):
    if not handles:
        return
    nuke.Undo.disable()
    try:
        for handle in handles:
            nuke.delete(handle)
    finally:
        nuke.Undo.enable()


def _select_with_contents(backdrop):
    # Dragging the handle only carries the nodes on the backdrop if they're
    # selected too, as they are after clicking the backdrop's name bar.
    backdrop.setSelected(True)
    for node in backdrop.getNodes():
        node.setSelected(True)


def _target_backdrop(selected):
    handles = [n for n in selected if _is_handle(n)]
    others = [n for n in selected if not _is_handle(n)]
    if not others:
        if len(handles) != 1:
            return None
        # Clicking the handle on its own deselects the backdrop; reselect it.
        backdrop = nuke.toNode(handles[0][HANDLE_KNOB].value())
        if backdrop is not None:
            _select_with_contents(backdrop)
        return backdrop

    # Clicking a backdrop's name bar selects it plus everything on it, so
    # accept a backdrop whose contents cover the rest of the selection.
    names = {n.name() for n in others}
    for backdrop in (n for n in others if n.Class() == "BackdropNode"):
        inside = {n.name() for n in backdrop.getNodes()}
        inside.add(backdrop.name())
        if names <= inside:
            return backdrop
    return None


def _update_handles():
    global _suppressed_for
    with nuke.root():
        target = _target_backdrop(nuke.selectedNodes())
        handles = [n for n in nuke.allNodes("StickyNote") if _is_handle(n)]

        if target is None or target.name() != _suppressed_for:
            _suppressed_for = None

        keep = None
        stale = []
        for handle in handles:
            if keep is None and target is not None and handle[HANDLE_KNOB].value() == target.name():
                keep = handle
            else:
                stale.append(handle)
        _delete_handles(stale)

        if target is None or _suppressed_for:
            return
        if keep is None:
            nuke.Undo.disable()
            try:
                keep = _make_handle(target)
            finally:
                nuke.Undo.enable()
            _select_with_contents(target)
        if not keep.isSelected():
            # Handle and backdrop selected together means dragging the handle
            # moves the backdrop, which carries the nodes sitting on it.
            keep.setSelected(True)


def _tick():
    try:
        _update_handles()
    except Exception:
        traceback.print_exc()
        print("Smart Backdrop: grab handles stopped after an error.")
        disable_grab_handles()


def _remove_handles_before_save():
    global _suppressed_for
    with nuke.root():
        target = _target_backdrop(nuke.selectedNodes())
        _delete_handles([n for n in nuke.allNodes("StickyNote") if _is_handle(n)])
    # Don't recreate the handle straight away, or the script is dirty again
    # right after saving. It comes back once the selection changes.
    _suppressed_for = target.name() if target is not None else None


def enable_grab_handles(interval_ms=150):
    global _handle_timer
    if _handle_timer is not None:
        return
    _handle_timer = QTimer()
    _handle_timer.timeout.connect(_tick)
    _handle_timer.start(interval_ms)
    nuke.addOnScriptSave(_remove_handles_before_save)


def disable_grab_handles():
    global _handle_timer
    if _handle_timer is None:
        return
    _handle_timer.stop()
    _handle_timer = None
    nuke.removeOnScriptSave(_remove_handles_before_save)
    with nuke.root():
        _delete_handles([n for n in nuke.allNodes("StickyNote") if _is_handle(n)])

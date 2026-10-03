"""Regenerate SmartBackdrop.nk from smartBackdrop.py without needing Nuke.

    python3 tools/make_template.py
"""

import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# smartBackdrop imports nuke and PySide at load time; stub them out.
sys.modules["nuke"] = types.ModuleType("nuke")
widgets = types.ModuleType("PySide6.QtWidgets")
for name in ("QApplication QDialog QVBoxLayout QGridLayout QHBoxLayout QLabel "
             "QLineEdit QPlainTextEdit QPushButton QButtonGroup").split():
    setattr(widgets, name, type(name, (), {}))
core = types.ModuleType("PySide6.QtCore")
core.Qt = core.QTimer = type("Stub", (), {})
sys.modules.update({"PySide6": types.ModuleType("PySide6"), "PySide6.QtWidgets": widgets, "PySide6.QtCore": core})

sys.path.insert(0, ROOT)
import smartBackdrop as sb  # noqa: E402

TITLE = "Smart Backdrop"
DESCRIPTION = "Smart Backdrop tab > Edit title and colour"
COLOR = "#4F6F82"


def tcl(text):
    """Quote a string the way .nk files expect."""
    out = []
    for ch in text:
        if ch == "\n":
            out.append("\\n")
        elif ch in '\\"[]{}$':
            out.append("\\" + ch)
        else:
            out.append(ch)
    return '"%s"' % "".join(out)


def build():
    lines = [
        "set cut_paste_input [stack 0]",
        "version 16.0 v8",
        "BackdropNode {",
        " inputs 0",
        " name SmartBackdrop1",
        " tile_color 0x%08x" % sb._hex_to_tile(COLOR),
        " label %s" % tcl(sb._label_html(TITLE, DESCRIPTION)),
        " note_font_size %d" % sb.BASE_FONT_SIZE,
        " note_font_color 0x%08x" % sb.TEXT_COLOR,
        " selected true",
        " xpos 0",
        " ypos 0",
        " bdwidth 700",
        " bdheight 450",
        ' addUserKnob {20 smartBackdrop l "Smart Backdrop"}',
        ' addUserKnob {22 sb_edit l "Edit title and colour" T %s +STARTLINE}' % tcl(sb.EDIT_COMMAND),
        " addUserKnob {1 sb_title +INVISIBLE}",
        " sb_title %s" % tcl(TITLE),
        " addUserKnob {1 sb_description +INVISIBLE}",
        " sb_description %s" % tcl(DESCRIPTION),
        "}",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    path = os.path.join(ROOT, "SmartBackdrop.nk")
    with open(path, "w") as handle:
        handle.write(build())
    print("wrote", path)

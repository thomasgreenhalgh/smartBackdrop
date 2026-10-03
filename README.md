# smartBackdrop

A backdrop tool for Nuke. Select some nodes, press **Ctrl+Alt+B**, enter a title and description, pick a colour, and the nodes get wrapped in a generously padded backdrop with a large bold title and a smaller description, both centred.

Backdrops are purely visual: no callbacks and nothing in `knobChanged`, so scripts are safe to hand to anyone. Each backdrop has an **Edit title and colour** button on its Smart Backdrop tab that carries its own code, so it works on machines without the plugin installed.

Tested with Nuke 16 (PySide6). Falls back to PySide2 for older versions.

## No install: use the template

Open `SmartBackdrop.nk` in a text editor, copy everything, and paste it into the Node Graph. You can also use **File > Insert Comp Nodes**. Move or resize the backdrop as needed, then use **Smart Backdrop > Edit title and colour** to set the text and colour.

## Install the plugin

1. Copy `smartBackdrop.py` into your `~/.nuke` folder.
2. Add this to `~/.nuke/menu.py` (create the file if it doesn't exist):

```python
import nuke
import smartBackdrop

nuke.menu('Nuke').addCommand('Edit/Smart Backdrop', smartBackdrop.create, 'ctrl+alt+b')
smartBackdrop.enable_grab_handles()  # optional, see below
```

3. Restart Nuke.

## Grab handles (optional)

`enable_grab_handles()` shows a large **MOVE** sticky note beside any backdrop you select. Drag it to move the backdrop and everything on it. The handle disappears when you deselect, isn't recorded in undo, and is removed before every save, so it never ends up in your scripts. Leave the line out of `menu.py` if you don't want it.

## Customising

Constants at the top of `smartBackdrop.py`:

- `PASTELS`: the colour swatches
- `PAD_X`, `PAD_TOP`, `PAD_BOTTOM`: space around the nodes
- `BASE_FONT_SIZE`, `TITLE_SCALE`: text sizes
- `HANDLE_FONT_SIZE`, `HANDLE_WIDTH`, `HANDLE_GAP`: grab handle size and position

After changing the colours or label code, regenerate the template with `python3 tools/make_template.py`.

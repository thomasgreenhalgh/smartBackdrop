import nuke
import smartBackdrop

nuke.menu('Nuke').addCommand('Edit/Smart Backdrop', smartBackdrop.create, 'ctrl+alt+b')
smartBackdrop.enable_grab_handles()

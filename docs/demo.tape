# VHS tape for the Khnum terminal demo (https://github.com/charmbracelet/vhs)
# Produce the GIF with:  vhs docs/demo.tape
# Outputs docs/demo.gif — embedded at the top of README (house standard, see
# CLAUDE.md rule: every Lord1Egypt CLI/npm/PyPI project ships one).

Output docs/demo.gif

Set FontSize 18
Set Width 1100
Set Height 640
Set Theme "Dracula"
Set Padding 18

Type "python3 -m khnum list"
Enter
Sleep 2s

Type "python3 -m khnum gen --kind sram_1rw --depth 1024 --width 32 --byte-en -o build"
Enter
Sleep 2s

Type "cat build/khnum_sram_1rw_1024x32_be.manifest.json"
Enter
Sleep 3s

```sh
pip install -r requirements.txt

python font_gen.py \
--xml-dir "assets" \ # Path to all the XML files, or the parent dir
--fonts "DFPKaiW5-GB.ttf" \ # The earlier the higher the priority
"DFPKaiW5-B5.ttf" \
"黎ミンY10 B.ttf" \
--output bb_font.ttf \
--log-file merge_details.log \
--glyph-sheet glyph_sheet.png \
--common-chars-file "common_chars.txt"
```

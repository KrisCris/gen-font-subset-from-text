#!/usr/bin/env python3
import os
import sys
import math
import argparse
import xml.etree.ElementTree as ET

# FontTools
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

# For glyph sheet visualization
# Requires "pip install freetype-py pillow"
import freetype
from PIL import Image, ImageDraw

def parse_xml_file(xml_path):
    """Parse a single XML file, collect all characters from .text in every node."""
    chars = set()
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        for node in root.iter():
            if node.text:
                chars.update(node.text)
    except Exception as e:
        print(f"Error parsing {xml_path}: {e}")
    return chars

def parse_xml_inputs(xml_dirs, xml_files):
    """
    Given directories and files, gather a set of all characters
    found in the .text of any XML node.
    """
    required_chars = set()

    # For each directory, read all .xml files
    for d in xml_dirs:
        if not os.path.isdir(d):
            print(f"Warning: {d} is not a directory, skipping.")
            continue
        for root, dirs, files in os.walk(d):
            for fname in files:
                if fname.lower().endswith(".xml"):
                    fpath = os.path.join(root, fname)
                    required_chars.update(parse_xml_file(fpath))

    # For each explicit XML file
    for f in xml_files:
        if not os.path.isfile(f):
            print(f"Warning: {f} is not a file, skipping.")
            continue
        required_chars.update(parse_xml_file(f))

    return required_chars

def parse_common_chars_file(txt_path):
    """
    Read all lines from `txt_path`. For each line, add every character
    to a set (excluding line-breaks).
    """
    chars = set()
    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            for line in f:
                # line.strip() removes trailing newline; but we still want spaces or punctuation if present
                # So if you do want spaces, remove only the trailing newline:
                # e.g. line = line.rstrip("\r\n")
                # But here we'll do a basic strip for demonstration:
                line = line.strip()
                if line:
                    chars.update(line)
    except Exception as e:
        print(f"Error reading {txt_path}: {e}")
    return chars

def font_supports_char(ttfont, char_code):
    """Return the glyph name if the font supports this char_code, else None."""
    try:
        cmap = ttfont["cmap"].getBestCmap()
        return cmap.get(char_code, None)
    except KeyError:
        return None

def copy_glyph_and_dependencies(glyph_name, source_font, target_font, copied_glyphs):
    """
    Copy `glyph_name` from `source_font` into `target_font`, recursively
    copying composite components as well. `copied_glyphs` is a set used
    to avoid copying the same glyph repeatedly.
    """
    if glyph_name in copied_glyphs:
        return  # already copied

    glyf_src = source_font["glyf"]
    glyf_dst = target_font["glyf"]
    if glyph_name not in glyf_src:
        # If glyph doesn't exist in source (rare corner case)
        return

    # Copy glyf outline
    glyf_dst[glyph_name] = glyf_src[glyph_name]

    # Copy horizontal metrics
    hmtx_src = source_font["hmtx"].metrics
    hmtx_dst = target_font["hmtx"].metrics
    if glyph_name in hmtx_src:
        hmtx_dst[glyph_name] = hmtx_src[glyph_name]
    else:
        # fallback
        hmtx_dst[glyph_name] = (500, 0)

    copied_glyphs.add(glyph_name)

    # If glyph is composite, copy its components
    glyph_obj = glyf_dst[glyph_name]
    if glyph_obj.isComposite():
        for component in glyph_obj.components:
            component_name = component.glyphName
            copy_glyph_and_dependencies(component_name, source_font, target_font, copied_glyphs)

def get_or_create_cmap12(ttfont):
    """
    Return an existing format 12 subtable (platform=3, platEncID=10)
    or create one if not found.
    """
    cmap_obj = ttfont["cmap"]
    for subtable in cmap_obj.tables:
        if (subtable.platformID == 3 and
            subtable.platEncID == 10 and
            subtable.format == 12):
            return subtable
    # Not found, create a new one
    cmap12 = CmapSubtable.newSubtable(12)
    cmap12.platformID = 3
    cmap12.platEncID = 10
    cmap12.language = 0
    cmap12.cmap = {}
    cmap_obj.tables.append(cmap12)
    return cmap12

def add_char_to_cmap(ttfont, char_code, glyph_name):
    """
    Add (char_code -> glyph_name) to a format 12 cmap subtable,
    ensuring codepoints up to U+10FFFF are supported.
    """
    cmap12 = get_or_create_cmap12(ttfont)
    cmap12.cmap[char_code] = glyph_name

def build_minimal_font(required_chars, fonts_priority, output_ttf_path, log_file=None):
    """
    Build a minimal TTF that contains glyphs for all characters in `required_chars`,
    using the provided `fonts_priority` list in order. The first font that supports
    a character supplies the glyph outline. Result is saved to `output_ttf_path`.
    """
    if not fonts_priority:
        raise ValueError("No fonts specified in fonts_priority.")

    # 1) Start with the first font as base
    base_font_path = fonts_priority[0]
    if not os.path.isfile(base_font_path):
        raise FileNotFoundError(f"Base font not found: {base_font_path}")
    msg = f"Using '{base_font_path}' as the base font."
    print(msg)
    if log_file:
        log_file.write(msg + "\n")

    merged_font = TTFont(base_font_path)

    # We'll cache the TTFont objects in memory for speed
    font_cache = {}
    for fpath in fonts_priority:
        if not os.path.isfile(fpath):
            raise FileNotFoundError(f"Font not found: {fpath}")
        font_cache[fpath] = TTFont(fpath)

    copied_glyphs = set()  # track glyphs we've brought into merged_font

    missing_chars = []
    # 2) For each character
    for ch in sorted(required_chars):
        char_code = ord(ch)
        found = False
        for fpath in fonts_priority:
            f = font_cache[fpath]
            glyph_name = font_supports_char(f, char_code)
            if glyph_name:
                # Copy the glyph + dependencies
                copy_glyph_and_dependencies(glyph_name, f, merged_font, copied_glyphs)
                # Add to cmap (format 12)
                add_char_to_cmap(merged_font, char_code, glyph_name)

                msg = (f"Character '{ch}' (U+{char_code:04X}) "
                       f"using font '{os.path.basename(fpath)}' "
                       f"-> glyph '{glyph_name}'")
                print(msg)
                if log_file:
                    log_file.write(msg + "\n")

                found = True
                break
        if not found:
            missing_chars.append(ch)

    if missing_chars:
        msg = "WARNING: These characters were not found in any font:"
        print(msg)
        if log_file:
            log_file.write(msg + "\n")
        for ch in missing_chars:
            warn_str = f"  U+{ord(ch):04X} '{ch}'"
            print(warn_str)
            if log_file:
                log_file.write(warn_str + "\n")

    # 3) Remove any original glyphs in the base font not used
    #    (except .notdef, .null, etc.). If you want to keep them, skip this step.
    glyf_table = merged_font["glyf"]
    all_glyphs = list(glyf_table.keys())
    for gname in all_glyphs:
        if gname not in copied_glyphs and gname not in (".notdef", ".null", "nonmarkingreturn"):
            del merged_font["glyf"][gname]
            if gname in merged_font["hmtx"].metrics:
                del merged_font["hmtx"].metrics[gname]

    # 4) Update maxp.numGlyphs
    merged_font["maxp"].numGlyphs = len(merged_font["glyf"].keys())

    # Save
    merged_font.save(output_ttf_path)
    msg = f"Saved minimal font to '{output_ttf_path}'."
    print(msg)
    if log_file:
        log_file.write(msg + "\n")

def generate_glyph_sheet(font_path, characters, png_path="glyph_sheet.png", pt_size=64, columns=16):
    """
    Renders each character from `characters` in the given TTF/OTF font
    using freetype-py, arranges them into a grid, and saves as a .png.
    
    Args:
        font_path (str): Path to the TTF/OTF font.
        characters (Iterable of str): The set/list of characters to display.
        png_path (str): Where to save the resulting PNG image.
        pt_size (int): Point size to render each glyph.
        columns (int): How many glyphs per row in the sheet.
    """
    # Load the font with freetype
    face = freetype.Face(font_path)
    # Set character size in 1/64th of a point
    face.set_char_size(pt_size * 64)

    # Convert the set to a sorted list so we have a consistent ordering
    chars_list = sorted(characters)
    if not chars_list:
        print("No characters to visualize. Skipping sheet generation.")
        return

    # First pass: measure each glyph to find max width/height
    max_w = 0
    max_h = 0
    for ch in chars_list:
        face.load_char(ch, freetype.FT_LOAD_RENDER)
        bmp = face.glyph.bitmap
        w, h = bmp.width, bmp.rows
        if w > max_w:
            max_w = w
        if h > max_h:
            max_h = h

    Y_OFFSET = int(max_h / 2)

    # We'll add some vertical padding so we can place a codepoint label
    padding_x = 10
    padding_y = 20
    cell_w = max_w + padding_x
    cell_h = max_h + padding_y

    # Compute how many rows we need
    rows = math.ceil(len(chars_list) / columns)

    # Create a blank RGBA image
    img_w = columns * cell_w
    img_h = rows * cell_h
    img = Image.new("RGBA", (img_w, img_h), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Render each char
    for idx, ch in enumerate(chars_list):
        row = idx // columns
        col = idx % columns

        # position for the top-left corner of this cell
        x_off = col * cell_w
        y_off = row * cell_h

        # Render the glyph
        face.load_char(ch, freetype.FT_LOAD_RENDER)
        glyph = face.glyph
        bmp = glyph.bitmap

        # Convert freetype's bitmap to a Pillow image (grayscale "L")
        glyph_img = Image.new("L", (bmp.width, bmp.rows), 0)
        glyph_img.frombytes(bytes(bmp.buffer), "raw", "L", 0, -1)
        glyph_img = glyph_img.transpose(Image.FLIP_TOP_BOTTOM)

        # Convert to RGBA
        glyph_img_rgba = glyph_img.convert("RGBA")

        # Compute where to place in the cell
        # We'll use the glyph's left/top offsets to better align the glyph
        left = x_off + glyph.bitmap_left
        # The baseline is typically near cell_h - glyph.bitmap_top
        top = y_off + (max_h - h) - (glyph.bitmap_top - (max_h - h)) + Y_OFFSET

        # Draw the glyph
        img.alpha_composite(glyph_img_rgba, (left, top))

        # Draw codepoint label at bottom of cell
        code_str = f"U+{ord(ch):04X}"
        draw.text((x_off+2, y_off + max_h), code_str, fill=(0, 0, 0, 255))

    # Save the final sprite sheet
    img.save(png_path)
    print(f"Saved glyph sheet to '{png_path}'.")

def main():
    parser = argparse.ArgumentParser(
        description="Build a minimal TTF containing glyphs for all characters "
                    "extracted from a set of XML files, using multiple fonts in fallback order. "
                    "Optionally, generate a glyph sheet (.png) visualizing the result."
    )
    parser.add_argument(
        "--xml-dir", nargs="*", default=[],
        help="One or more directories; all .xml files in these dirs are scanned."
    )
    parser.add_argument(
        "--xml-file", nargs="*", default=[],
        help="One or more XML files to scan."
    )
    parser.add_argument(
        "--common-chars-file",
        help="Optional path to a text file containing additional common characters to include."
    )
    parser.add_argument(
        "--fonts", nargs="+", required=True,
        help="List of TTF fonts in fallback priority order (first = highest priority)."
    )
    parser.add_argument(
        "--output", required=True,
        help="Path to save the minimal TTF."
    )
    parser.add_argument(
        "--log-file",
        help="Optional path to save a detailed log of which character used which font."
    )
    parser.add_argument(
        "--glyph-sheet",
        help="If provided, also generate a .png sheet of glyphs from the minimal TTF."
    )
    parser.add_argument(
        "--glyph-size", type=int, default=64,
        help="Point size used for glyph rendering in the sheet (default 64)."
    )
    parser.add_argument(
        "--glyph-cols", type=int, default=16,
        help="Number of columns per row in the glyph sheet (default 16)."
    )

    args = parser.parse_args()

    # 1) Collect required characters
    required_chars = parse_xml_inputs(args.xml_dir, args.xml_file)
    print(f"Collected {len(required_chars)} unique characters from XML inputs.")

    # 2) If there's a common-chars file, read it and union the sets
    if args.common_chars_file:
        common_chars = parse_common_chars_file(args.common_chars_file)
        old_count = len(required_chars)
        required_chars.update(common_chars)
        print(f"Added {len(common_chars)} chars from {args.common_chars_file}; "
              f"total now {len(required_chars)} (was {old_count}).")

    # 3) Create/append to log file if specified
    log_fh = None
    if args.log_file:
        log_fh = open(args.log_file, "w", encoding="utf-8")

    # 4) Build minimal font
    try:
        build_minimal_font(required_chars, args.fonts, args.output, log_file=log_fh)
    finally:
        if log_fh:
            log_fh.close()

    # 5) Generate glyph sheet (optional)
    if args.glyph_sheet:
        generate_glyph_sheet(
            font_path=args.output,
            characters=required_chars,
            png_path=args.glyph_sheet,
            pt_size=args.glyph_size,
            columns=args.glyph_cols
        )

if __name__ == "__main__":
    main()

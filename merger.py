from fontTools.ttLib import TTFont

def merge_fonts_preserve_a(font_a_path, font_b_path, output_path):
    """
    Merge font B into font A while preserving glyphs and mappings from font A
    if both fonts contain the same character. Works with large size differences.

    Args:
        font_a_path (str): Path to the primary font (A).
        font_b_path (str): Path to the secondary font (B).
        output_path (str): Path to save the merged font file.
    """
    # Load both fonts
    font_a = TTFont(font_a_path)
    font_b = TTFont(font_b_path)

    # Get cmap (character-to-glyph mapping) tables from both fonts
    cmap_a = font_a["cmap"].getBestCmap()
    cmap_b = font_b["cmap"].getBestCmap()

    # Check for required tables
    if "glyf" not in font_a or "glyf" not in font_b:
        raise ValueError("Both fonts must contain a 'glyf' table.")

    # Add glyphs from font B to font A if not present
    for char_code, glyph_name_b in cmap_b.items():
        if char_code not in cmap_a:
            # If the character doesn't exist in font A
            if glyph_name_b in font_b["glyf"]:  # Check if glyph exists in B's glyf table
                # Add the character mapping to cmap in font A
                font_a["cmap"].tables[0].cmap[char_code] = glyph_name_b

                # Add the glyph from font B to font A
                if glyph_name_b not in font_a["glyf"]:
                    font_a["glyf"][glyph_name_b] = font_b["glyf"][glyph_name_b]

                    # Add default metrics to hmtx table
                    font_a["hmtx"].metrics[glyph_name_b] = (500, 0)  # Default width and side bearing
            else:
                print(f"Warning: Glyph '{glyph_name_b}' for character {chr(char_code)} is missing in font B.")
        else:
            # If the character already exists in font A, preserve font A's glyph
            print(f"Preserving glyph for character {chr(char_code)} from font A.")

    # Update maxp.numGlyphs to match the number of glyphs in glyf table
    font_a["maxp"].numGlyphs = len(font_a["glyf"].keys())

    # Save the merged font
    font_a.save(output_path)
    print(f"Merged font saved to: {output_path}")




if __name__ == "__main__":
    font_a = "./DFPKaiW5-GB.ttf"
    font_b = "./DFPKaiW5-B5.ttf"
    font_c = "./黎ミンY10 B-BB.ttf"

    output_font = "./DFPKaiW5-CHS.ttf"

    merge_fonts_preserve_a(font_a, font_b, output_font)
    merge_fonts_preserve_a(output_font, font_c, output_font)

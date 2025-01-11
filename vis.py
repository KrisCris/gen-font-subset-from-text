import math
from fontTools.ttLib import TTFont
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.font_manager import FontProperties
from matplotlib import rcParams


def get_supported_characters(font_path):
    """
    Extract all characters supported by the font.
    """
    try:
        font = TTFont(font_path)
        cmap = font["cmap"]
        supported_chars = set()
        for table in cmap.tables:
            supported_chars.update(table.cmap.keys())
        # Convert Unicode code points to characters
        return [chr(code) for code in sorted(supported_chars)]
    except Exception as e:
        print(f"Error reading font: {e}")
        return []
    

def visualize_font_single_large(
    font_path,
    characters,
    columns=20,
    font_size=12,
    cell_size=0.8,  # inches per cell
    output_file="output.png",
):
    cjk_font = FontProperties(fname=font_path)

    total_chars = len(characters)
    rows = math.ceil(total_chars / columns)

    fig_width = columns * cell_size
    fig_height = rows * cell_size

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.set_xlim(0, columns)
    ax.set_ylim(0, rows)
    ax.invert_yaxis()
    ax.axis("off")

    for i, char in enumerate(characters):
        col_index = i % columns
        row_index = i // columns
        x = col_index + 0.5
        y = row_index + 0.5
        ax.text(
            x,
            y,
            char,
            fontsize=font_size,
            ha="center",
            va="center",
        )

    ax.set_title(f"Visualizing {total_chars} Characters", fontsize=font_size * 1.5)

    # Save directly to a file instead of trying to fit on screen
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved large figure to {output_file}. Please open it in an external viewer.")


# Example usage
if __name__ == "__main__":
    # rcParams["font.family"] = "DFPKaiW5-GB"
    rcParams["font.family"] = ['SimSun', 'Times New Roman', 'Arial', 'sans-serif']

    font_file = "./黎ミンY10 B-BB.ttf"

    visualize_font_single_large(
        font_path=font_file,
        characters=get_supported_characters(font_file),
        columns=40,  # You can increase columns to reduce the number of rows
        font_size=32,  # Keep font size the same for all glyphs
        cell_size=0.8,  # Increase cell_size if glyphs still appear too close
        output_file=f"{font_file}.png",
    )

import os
import xml.etree.ElementTree as ET
from fontTools.ttLib import TTFont
from fontTools.subset import Subsetter

# # Step 1: Extract characters from XML files
# def extract_characters_from_xml(xml_path):
#     """
#     Extract all unique characters from <text> elements in an XML file or directory.
#     """
#     characters = set()
#     if os.path.isfile(xml_path):  # Check if it's a single file
#         files = [xml_path]
#     elif os.path.isdir(xml_path):  # Check if it's a directory
#         files = [os.path.join(xml_path, f) for f in os.listdir(xml_path) if f.endswith(".xml")]
#     else:
#         raise NotADirectoryError(f"The path {xml_path} is neither a file nor a directory.")
    
#     for file_path in files:
#         try:
#             tree = ET.parse(file_path)
#             root = tree.getroot()
#             for text_element in root.findall(".//text"):
#                 if text_element.text:
#                     characters.update(text_element.text)  # Add characters to the set
#         except Exception as e:
#             print(f"Error parsing {file_path}: {e}")
#     return characters

def extract_characters_from_xml(paths):
    """
    Extract all unique characters from <text> elements in a list of XML files or directories.

    Args:
        paths (list): A list of file or directory paths.

    Returns:
        set: A set of unique characters extracted from the XML files.
    """
    characters = set()
    files = []

    # Process each path in the list
    for path in paths:
        if os.path.isfile(path):  # If it's a single file
            if path.endswith(".xml"):
                files.append(path)
        elif os.path.isdir(path):  # If it's a directory
            for f in os.listdir(path):
                if f.endswith(".xml"):
                    files.append(os.path.join(path, f))
        else:
            print(f"Warning: The path {path} is neither a file nor a directory. Skipping.")

    # Parse each XML file and extract characters
    for file_path in files:
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            for text_element in root.findall(".//text"):
                if text_element.text:
                    characters.update(text_element.text)  # Add characters to the set
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

    return characters


# Step 2: Check font support
def check_character_support(font_path, characters):
    """
    Check which characters are supported by the font.
    """
    try:
        font = TTFont(font_path)
        cmap = font["cmap"]
        supported_chars = set()
        for table in cmap.tables:
            supported_chars.update(table.cmap.keys())
        supported = {char for char in characters if ord(char) in supported_chars}
        missing = characters - supported
        redundant = {chr(code) for code in supported_chars if chr(code) not in characters}
        return supported, missing, redundant
    except Exception as e:
        print(f"Error reading font: {e}")
        return set(), set(), set()

# Step 3: Subset font
def subset_font(font_path, output_path, characters):
    """
    Subset the font to include only the specified characters.
    """
    try:
        font = TTFont(font_path)
        subsetter = Subsetter()
        unicodes = [ord(char) for char in characters]
        subsetter.populate(unicodes=unicodes)
        subsetter.subset(font)
        font.save(output_path)
        print(f"Subset font saved to {output_path}")
    except Exception as e:
        print(f"Error during subsetting: {e}")

# Main Workflow
def main():
    font_file = "./黎ミンY10 B.ttf"  # Path to your font file
    xml_folder = [r"D:\Coding\Bloodborne-CN-reTranslation\item-msgbnd-dcx", r"D:\Coding\Bloodborne-CN-reTranslation\menu-msgbnd-dcx"]  # Folder containing XML files
    output_font_file = "./黎ミンY10 B-BB.ttf"  # Output font file
    common_characters = set("")  # Define your commonly used characters

    # Step 1: Extract all characters from XML files
    print("Extracting characters from XML files...")
    xml_characters = extract_characters_from_xml(xml_folder)
    all_characters = xml_characters | common_characters  # Combine with common characters
    print(f"Total unique characters extracted: {len(xml_characters)}")
    print(f"Total unique characters including common set: {len(all_characters)}")

    # Step 2: Check font support
    print("Checking font support...")
    supported_chars, missing_chars, redundant_chars = check_character_support(font_file, all_characters)
    print(f"Characters supported by the font: {len(supported_chars)}")
    print(f"Characters missing from the font: {len(missing_chars)}")
    print(f"Redundant characters in the font: {len(redundant_chars)}")

    # Display missing and redundant characters (optional)
    print("\nMissing Characters:")
    print("".join(missing_chars))
    # print("\nRedundant Characters:")
    # print("".join(redundant_chars))

    # Step 3: Ask for subsetting
    if input("\nDo you want to subset the font? (y/n): ").strip().lower() == "y":
        print("Creating subset font...")
        subset_font(font_file, output_font_file, supported_chars | common_characters)
    else:
        print("Font subsetting skipped.")

if __name__ == "__main__":
    main()

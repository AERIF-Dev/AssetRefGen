"""Compose a labeled review gallery from existing public example images; no generation."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "examples"


def compose():
    canvas = Image.new("RGB", (1800, 1510), "#111b26")
    draw = ImageDraw.Draw(canvas)
    title = ImageFont.load_default(size=56)
    heading = ImageFont.load_default(size=27)
    small = ImageFont.load_default(size=23)
    draw.text((52, 38), "AssetRefGen", font=title, fill="#f6e8ce")
    draw.text((54, 110), "One short request. A recoverable reference workflow.", font=heading, fill="#c3d2db")
    draw.text((54, 174), "ORIGINAL TEST SOURCES / INVENTORY EXAMPLES", font=small, fill="#e7b97e")

    def image(path, box):
        with Image.open(path) as src:
            thumb = src.convert("RGB")
            thumb.thumbnail((box[2] - box[0], box[3] - box[1]), Image.Resampling.LANCZOS)
            canvas.paste(thumb, (box[0] + (box[2] - box[0] - thumb.width) // 2,
                                 box[1] + (box[3] - box[1] - thumb.height) // 2))
            thumb.close()

    image(E / "sources/characters.png", (50, 220, 1030, 870))
    image(E / "sources/objects.png", (1060, 300, 1750, 750))
    draw.text((54, 895), "3 distinct designs", font=heading, fill="#f4f4ee")
    draw.text((1060, 795), "2 distinct objects", font=heading, fill="#f4f4ee")
    draw.text((54, 947), "LIVE TURNAROUND / ONE IDENTITY, FOUR DIRECTIONS", font=small, fill="#e7b97e")
    image(E / "kiln-traveler/contact_preview.png", (40, 998, 1760, 1432))
    draw.text((54, 1463), "Quick-mode example. Minor cross-view drift remains; geometry is unverified.",
              font=small, fill="#b8c5d1")
    canvas.save(E / "gallery.png")
    canvas.close()


if __name__ == "__main__":
    compose()
    print(E / "gallery.png")

"""The gallery screenshots are captured at 2x for sharp text, then written at the
1280x769 the gig gallery asks for."""

from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parent.parent.parent
for name in ("shot1.png", "shot2.png", "shot3.png"):
    path = OUT / name
    image = Image.open(path)
    if image.size != (1280, 769):
        image.resize((1280, 769), Image.LANCZOS).save(path)
    print(name, Image.open(path).size)

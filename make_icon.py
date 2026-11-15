"""Generate the app icon from the bank-shield artwork used on the login page."""
from pathlib import Path

from PIL import Image
from PySide6.QtWidgets import QApplication

from login_art import shield_pixmap


def main():
    app = QApplication.instance() or QApplication([])
    png_path = Path(__file__).with_name("icon.png")
    ico_path = Path(__file__).with_name("icon.ico")

    shield_pixmap(512).save(str(png_path), "PNG")
    with Image.open(png_path) as image:
        image.convert("RGBA").save(
            ico_path,
            format="ICO",
            sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
        )
    print("Updated icon.png and icon.ico from the login-page bank shield.")
    app.quit()


if __name__ == "__main__":
    main()

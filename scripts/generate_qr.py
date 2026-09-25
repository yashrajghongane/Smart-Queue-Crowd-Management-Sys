"""
SmartQueue — QR Code Generator & Verifier
Generates PNG, SVG, and URL text assets for the production patient registration endpoint.
Programmatically decodes and verifies the generated PNG using OpenCV.
"""

import os
import qrcode
import qrcode.image.svg
import cv2

def generate_and_verify_qr():
    output_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "qr")
    os.makedirs(output_dir, exist_ok=True)
    
    url = "https://smartqueue-api.onrender.com/patient/"
    
    # 1. URL text file
    url_file = os.path.join(output_dir, "patient-registration-url.txt")
    with open(url_file, "w", encoding="utf-8") as f:
        f.write(url + "\n")
    print(f"Saved: {url_file}")
    
    # 2. PNG QR code
    qr_png = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr_png.add_data(url)
    qr_png.make(fit=True)
    img_png = qr_png.make_image(fill_color="black", back_color="white")
    png_path = os.path.join(output_dir, "patient-registration-qr.png")
    img_png.save(png_path)
    print(f"Saved: {png_path} ({os.path.getsize(png_path)} bytes)")
    
    # 3. SVG QR code
    factory = qrcode.image.svg.SvgPathImage
    qr_svg = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
        image_factory=factory
    )
    qr_svg.add_data(url)
    qr_svg.make(fit=True)
    img_svg = qr_svg.make_image()
    svg_path = os.path.join(output_dir, "patient-registration-qr.svg")
    img_svg.save(svg_path)
    print(f"Saved: {svg_path} ({os.path.getsize(svg_path)} bytes)")
    
    # 4. Programmatic Verification with OpenCV
    detector = cv2.QRCodeDetector()
    decoded_val, points, _ = detector.detectAndDecode(cv2.imread(png_path))
    print(f"Decoded from PNG: {decoded_val}")
    assert decoded_val == url, f"Decoded mismatch! Expected '{url}', got '{decoded_val}'"
    print("VERIFICATION: PASS (Decoded content strictly matches expected production URL)")

if __name__ == "__main__":
    generate_and_verify_qr()

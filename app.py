import streamlit as st
import pandas as pd
from fpdf import FPDF
from PIL import Image
import os
import zipfile
import tempfile

# Set Streamlit page config
st.set_page_config(page_title="Giordano Catalogue Generator", layout="centered")

# Title
st.title("🕒 Giordano Catalogue Generator")

# Uploads
excel_file = st.file_uploader("Upload Product Excel File", type=["xlsx"])
image_zip = st.file_uploader("Upload Product Images (ZIP file)", type=["zip"])
logo_file = st.file_uploader("Upload Logo Image", type=["png", "jpg", "jpeg"])

# Select layout
cards_per_row = st.selectbox("Select number of product cards per row", [2, 3])

# Font path for DejaVu (ensure this TTF file is available)
FONT_PATH = "DejaVuSans.ttf"

if excel_file and image_zip and logo_file:
    # Read Excel
    df = pd.read_excel(excel_file)

    # Remove unwanted columns if present
    if "Name" in df.columns:
        df = df.drop(columns=["Name"])

    # Extract images
    temp_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(image_zip, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    # Save logo
    logo_path = os.path.join(temp_dir, "logo.png")
    with open(logo_path, "wb") as f:
        f.write(logo_file.read())

    # PDF setup
    class PDF(FPDF):
        def __init__(self):
            super().__init__()
            self.set_auto_page_break(auto=True, margin=15)
            self.add_page()
            self.add_font('DejaVu', '', FONT_PATH, uni=True)
            self.set_font("DejaVu", size=10)
            self.set_fill_color(255, 255, 255)

        def header(self):
            if os.path.exists(logo_path):
                self.image(logo_path, x=70, y=10, w=70)  # center logo
                self.ln(30)

        def product_card(self, x, y, product):
            self.set_xy(x, y)

            # Container
            card_w = 190 / cards_per_row - 10
            card_h = 80
            self.set_fill_color(255, 255, 255)
            self.rounded_rect(x, y, card_w, card_h, 3, 'DF')

            # Image
            img_path = os.path.join(temp_dir, product['Model'] + '.jpg')
            if os.path.exists(img_path):
                try:
                    im = Image.open(img_path)
                    aspect = im.width / im.height
                    img_w = card_w - 20
                    img_h = img_w / aspect
                    if img_h > 40:
                        img_h = 40
                        img_w = img_h * aspect
                    img_x = x + (card_w - img_w) / 2
                    img_y = y + 5
                    self.image(img_path, x=img_x, y=img_y, w=img_w, h=img_h)
                except:
                    pass

            # Text
            text_x = x + 5
            text_y = y + 50
            self.set_xy(text_x, text_y)
            self.set_font("DejaVu", style='B', size=8)
            self.cell(card_w - 10, 5, f"Model: {product['Model']}", ln=True)

            self.set_font("DejaVu", size=8)
            self.cell(card_w - 10, 5, f"MRP: ₹{product['MRP']} Offer: ₹{product['Offer']}", ln=True)

            # Discount with pastel highlight
            if 'Discount' in product and not pd.isna(product['Discount']):
                self.set_text_color(0, 102, 204)
                self.set_font("DejaVu", style='B', size=8)
                self.cell(card_w - 10, 5, f"Discount: {product['Discount']}%", ln=True)
                self.set_text_color(0, 0, 0)
            else:
                self.ln(5)

            if 'Stock' in product and not pd.isna(product['Stock']):
                self.set_font("DejaVu", size=8)
                self.cell(card_w - 10, 5, f"Stock: {product['Stock']}", ln=True)

        def rounded_rect(self, x, y, w, h, r, style=''):
            op = {'F': 'f', 'DF': 'B', 'FD': 'B'}.get(style, 'S')
            self.set_line_width(0.1)
            self._out(f"{x + r:.2f} {y:.2f} m")
            self._Arc(x + r, y, x, y, x, y + r)
            self._out(f"{x:.2f} {y + h - r:.2f} l")
            self._Arc(x, y + h - r, x, y + h, x + r, y + h)
            self._out(f"{x + w - r:.2f} {y + h:.2f} l")
            self._Arc(x + w - r, y + h, x + w, y + h, x + w, y + h - r)
            self._out(f"{x + w:.2f} {y + r:.2f} l")
            self._Arc(x + w, y + r, x + w, y, x + w - r, y)
            self._out(f"{x + r:.2f} {y:.2f} l {op}")

        def _Arc(self, x1, y1, x2, y2, x3, y3):
            h = 4 / 3 * (2 ** 0.5 - 1)
            self._out(f"{x1 + h * (x2 - x1):.2f} {y1 + h * (y2 - y1):.2f} {x3 + h * (x2 - x3):.2f} {y3 + h * (y2 - y3):.2f} {x3:.2f} {y3:.2f} c")

    pdf = PDF()

    # Track missing images
    missing = []

    # Layout cards
    x_start = 10
    y = 50
    spacing_x = (190 - (cards_per_row * 60)) // (cards_per_row + 1)
    card_width = (190 / cards_per_row) - 10

    for idx, row in df.iterrows():
        model = str(row['Model']).strip()
        if not os.path.exists(os.path.join(temp_dir, model + '.jpg')):
            missing.append((idx + 2, model))  # Excel row numbers

    # Generate cards
    col = 0
    x = 10
    for i, row in df.iterrows():
        model = str(row['Model']).strip()
        if os.path.exists(os.path.join(temp_dir, model + '.jpg')):
            if col == 0:
                y += 90
                if y > 250:
                    pdf.add_page()
                    y = 50
            x = 10 + col * (card_width + 10)
            pdf.product_card(x, y, row)
            col += 1
            if col >= cards_per_row:
                col = 0

    output_path = os.path.join(temp_dir, "Giordano_Catalogue.pdf")
    pdf.output(output_path)

    with open(output_path, "rb") as f:
        st.download_button("📄 Download PDF Catalogue", f, file_name="Giordano_Catalogue.pdf", mime="application/pdf")

    # Show missing images if any
    if missing:
        st.warning("⚠️ Missing images for the following rows:")
        for row_num, model in missing:
            st.text(f"Row {row_num}: Missing image for model '{model}.jpg'")

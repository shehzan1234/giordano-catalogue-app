import streamlit as st
from fpdf import FPDF
from PIL import Image
import pandas as pd
import os

# Set Streamlit layout
st.set_page_config(layout="wide")
st.title("Giordano PDF Catalogue Generator")

# File upload
excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])
image_folder = st.file_uploader("Upload Product Images (as ZIP)", type=["zip"])
logo_file = st.file_uploader("Upload Logo Image (PNG)", type=["png"])
font_file = st.file_uploader("Upload Unicode Font (TTF)", type=["ttf"])
cards_per_row = st.selectbox("Select number of product cards per row", [2, 3])

if all([excel_file, image_folder, logo_file, font_file]):
    from io import BytesIO
    import zipfile
    import tempfile
    import shutil

    temp_dir = tempfile.mkdtemp()

    # Save and extract image zip
    image_zip_path = os.path.join(temp_dir, "images.zip")
    with open(image_zip_path, "wb") as f:
        f.write(image_folder.read())

    with zipfile.ZipFile(image_zip_path, "r") as zip_ref:
        zip_ref.extractall(os.path.join(temp_dir, "product_images"))

    image_dir = os.path.join(temp_dir, "product_images")

    # Save logo
    logo_path = os.path.join(temp_dir, "logo.png")
    with open(logo_path, "wb") as f:
        f.write(logo_file.read())

    # Save font
    font_path = os.path.join(temp_dir, "font.ttf")
    with open(font_path, "wb") as f:
        f.write(font_file.read())

    # Read Excel
    df = pd.read_excel(excel_file)
    df['Model'] = df['Model'].astype(str).str.replace(".jpg", "", case=False)

    # PDF setup
    class PDF(FPDF):
        def __init__(self, cards_per_row):
            super().__init__()
            self.cards_per_row = cards_per_row
            self.card_width = 190 / cards_per_row - 10
            self.card_height = 90
            self.margin_x = 10
            self.margin_y = 10
            self.set_auto_page_break(auto=True, margin=15)
            self.add_page()
            self.add_logo()
            self.set_font("DejaVu", size=8)

        def header(self):
            pass  # No default header

        def add_logo(self):
            logo_w = 60
            logo_h = 20
            page_w = self.w
            x = (page_w - logo_w) / 2
            self.image(logo_path, x=x, y=10, w=logo_w, h=logo_h)
            self.ln(logo_h + 10)

        def add_card(self, x, y, product, image_path):
            self.set_xy(x, y)
            self.set_fill_color(255, 255, 255)
            self.rounded_rect(x, y, self.card_width, self.card_height, 2, 'DF')
            
            # Image
            if image_path:
                try:
                    img = Image.open(image_path)
                    iw, ih = img.size
                    aspect = iw / ih
                    max_w = self.card_width - 10
                    max_h = 35
                    if aspect > 1:
                        w = max_w
                        h = max_w / aspect
                    else:
                        h = max_h
                        w = max_h * aspect
                    img_x = x + (self.card_width - w) / 2
                    img_y = y + 5
                    img_temp = os.path.join(temp_dir, "temp_img.jpg")
                    img.save(img_temp)
                    self.image(img_temp, x=img_x, y=img_y, w=w, h=h)
                except:
                    pass

            text_y = y + 45
            self.set_xy(x + 5, text_y)
            self.set_font("DejaVu", 'B', 8)
            self.multi_cell(self.card_width - 10, 4, f"{product['Model']}", align='C')

            self.set_font("DejaVu", size=8)
            self.set_xy(x + 5, text_y + 10)
            self.cell(self.card_width - 10, 4, f"MRP: ₹{product['MRP']}", ln=1, align='C')

            self.set_font("DejaVu", 'B', 9)
            self.set_text_color(255, 0, 0)
            self.set_xy(x + 5, text_y + 18)
            self.cell(self.card_width - 10, 4, f"Offer: ₹{product['Offer Price']}  ({product['Discount']}%)", ln=1, align='C')
            self.set_text_color(0, 0, 0)

    pdf = PDF(cards_per_row)
    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.add_font("DejaVu", "B", font_path, uni=True)

    x_start = pdf.l_margin
    y_start = pdf.get_y() + 5
    x = x_start
    y = y_start
    col_count = 0
    unmatched_rows = []

    for idx, row in df.iterrows():
        image_filename = row['Model'] + ".jpg"
        image_path = os.path.join(image_dir, image_filename)
        if not os.path.exists(image_path):
            unmatched_rows.append((idx+2, row['Model']))  # +2 for header and 0-index
            continue

        pdf.add_card(x, y, row, image_path)
        col_count += 1
        if col_count == cards_per_row:
            col_count = 0
            x = x_start
            y += pdf.card_height + 10
            if y + pdf.card_height + 10 > pdf.h - pdf.b_margin:
                pdf.add_page()
                y = pdf.get_y()
        else:
            x += pdf.card_width + 10

    # Save PDF
    output_path = os.path.join(temp_dir, "giordano_catalogue.pdf")
    pdf.output(output_path)

    with open(output_path, "rb") as f:
        st.download_button("Download PDF", f, file_name="giordano_catalogue.pdf")

    # Show unmatched
    if unmatched_rows:
        st.subheader("⚠️ Missing Images:")
        for row in unmatched_rows:
            st.write(f"Row {row[0]}: Image '{row[1]}.jpg' not found")

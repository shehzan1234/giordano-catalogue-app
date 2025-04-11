import streamlit as st
from fpdf import FPDF
import pandas as pd
import os
import zipfile
import tempfile
from PIL import Image

st.set_page_config(page_title="Giordano Catalogue Generator", layout="centered")
st.title("🕒 Giordano Catalogue Generator")

excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])
image_zip = st.file_uploader("Upload Product Images (ZIP)", type=["zip"])
logo_file = st.file_uploader("Upload Logo (PNG or JPG)", type=["png", "jpg", "jpeg"])
cards_per_row = st.selectbox("Select number of product cards per row", [2, 3])

FONT_PATH = "DejaVuSans.ttf"

# PDF class
class CataloguePDF(FPDF):
    def __init__(self, logo_path, cards_per_row):
        super().__init__()
        self.cards_per_row = cards_per_row
        self.logo_path = logo_path
        self.set_auto_page_break(auto=True, margin=15)
        self.add_font("DejaVu", "", FONT_PATH, uni=True)
        self.add_font("DejaVu", "B", FONT_PATH, uni=True)
        self.set_font("DejaVu", "", 10)

    def header(self):
        if self.logo_path:
            logo_w = 60
            logo_x = (self.w - logo_w) / 2
            self.image(self.logo_path, x=logo_x, y=10, w=logo_w)
            self.ln(30)

    def product_card(self, x, y, w, h, data, image_path):
        self.set_xy(x, y)
        self.set_fill_color(255, 255, 255)
        self.rect(x, y, w, h, 'F')

        if image_path:
            try:
                img = Image.open(image_path)
                img.thumbnail((w - 10, h // 2))
                temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                img.save(temp_img.name, "JPEG")
                img_w, img_h = img.size
                img_x = x + (w - img_w * 0.264) / 2  # convert px to mm
                img_y = y + 5
                self.image(temp_img.name, x=img_x, y=img_y, w=img_w * 0.264)
                os.unlink(temp_img.name)
            except:
                pass

        # Text
        self.set_xy(x + 4, y + h // 2 + 5)
        self.set_font("DejaVu", "B", 9)
        self.multi_cell(w - 8, 5, f"Model: {data['Model']}", 0)
        self.set_font("DejaVu", "", 8)
        self.multi_cell(w - 8, 5, f"MRP: ₹{data['MRP']}  Offer: ₹{data['CSP']}", 0)
        self.multi_cell(w - 8, 5, f"Discount: {data['Discount']}%", 0)
        self.multi_cell(w - 8, 5, f"Gender: {data['Gender']}", 0)
        self.multi_cell(w - 8, 5, f"Stock: {data['Inventory']}", 0)
        if pd.notna(data.get("Remarks")) and data['Remarks']:
            self.multi_cell(w - 8, 5, f"Note: {data['Remarks']}", 0)

if st.button("Generate Catalogue") and excel_file and image_zip:
    with tempfile.TemporaryDirectory() as tmpdir:
        # Save logo
        logo_path = None
        if logo_file:
            logo_path = os.path.join(tmpdir, "logo.png")
            with open(logo_path, "wb") as f:
                f.write(logo_file.read())

        # Extract images
        with zipfile.ZipFile(image_zip, 'r') as zip_ref:
            zip_ref.extractall(tmpdir)

        # Load Excel
        df = pd.read_excel(excel_file)
        df["Model"] = df["Model"].astype(str).str.replace(".jpg", "", regex=False)

        pdf = CataloguePDF(logo_path=logo_path, cards_per_row=cards_per_row)
        pdf.add_page()

        card_w = (pdf.w - 20 - (cards_per_row - 1) * 5) / cards_per_row
        card_h = 70
        x_start = 10
        y = pdf.get_y() + 10
        x = x_start

        created = []
        errors = []

        for idx, row in df.iterrows():
            model = row["Model"]
            image_path = os.path.join(tmpdir, f"{model}.jpg")
            if not os.path.exists(image_path):
                errors.append((idx + 2, model))
                continue

            pdf.product_card(x, y, card_w, card_h, row, image_path)

            if (idx + 1) % cards_per_row == 0:
                x = x_start
                y += card_h + 10
                if y + card_h > pdf.h - 20:
                    pdf.add_page()
                    y = pdf.get_y() + 10
            else:
                x += card_w + 5

        # Export PDF
        output_path = os.path.join(tmpdir, "giordano_catalogue.pdf")
        pdf.output(output_path)

        with open(output_path, "rb") as f:
            st.download_button("📄 Download Catalogue PDF", f, file_name="giordano_catalogue.pdf")

        if errors:
            st.warning("⚠️ Missing images for:")
            for row_num, model in errors:
                st.text(f"Row {row_num}: {model}.jpg not found")

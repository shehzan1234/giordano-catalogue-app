import streamlit as st
from PIL import Image
import pandas as pd
import os
from fpdf import FPDF
import tempfile
import zipfile

# Load images from zip
def load_images_from_zip(zip_file):
    image_dict = {}
    with zipfile.ZipFile(zip_file, 'r') as z:
        for filename in z.namelist():
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                with z.open(filename) as file:
                    img = Image.open(file).convert("RGB")
                    model_name = os.path.splitext(os.path.basename(filename))[0].strip()
                    image_dict[model_name] = img
    return image_dict

# Custom PDF with visual enhancements
class StyledPDF(FPDF):
    def __init__(self, logo_path, cards_per_row=2):
        super().__init__()
        self.logo_path = logo_path
        self.cards_per_row = cards_per_row
        self.set_auto_page_break(auto=True, margin=15)
        self.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        self.set_font("DejaVu", "", 10)

    def header(self):
        if self.logo_path:
            self.image(self.logo_path, x=(210 - 50) / 2, y=10, w=50)
            self.ln(25)

    def add_product_grid(self, products):
        card_width = (190 - (self.cards_per_row - 1) * 10) / self.cards_per_row
        card_height = 90
        x_start = 10
        y = self.get_y()
        for i, (data, image) in enumerate(products):
            x = x_start + (i % self.cards_per_row) * (card_width + 10)
            if i % self.cards_per_row == 0 and i != 0:
                y += card_height + 10
                self.set_y(y)
            self.set_xy(x, y)
            self.product_card(data, image, card_width, card_height)

        self.ln(card_height + 15)

    def product_card(self, data, image, w, h):
        x, y = self.get_x(), self.get_y()
        self.set_fill_color(255, 255, 255)
        self.rect(x, y, w, h, style="F")
        self.set_draw_color(200, 200, 200)
        self.rect(x, y, w, h)

        # Optional: Accent stripe
        self.set_fill_color(230, 230, 250)
        self.rect(x, y, w, 4, style='F')

        padding = 3
        image_height = h * 0.45
        image_y = y + 5

        if image:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmpfile:
                image.thumbnail((w - 2 * padding, image_height))
                image.save(tmpfile.name)
                self.image(tmpfile.name, x + padding, image_y, w - 2 * padding)
                os.unlink(tmpfile.name)

        # Text info
        text_y = image_y + image_height + 2
        self.set_xy(x + padding, text_y)
        self.set_font("DejaVu", "B", 10)
        self.multi_cell(w - 2 * padding, 5, f"{data['Model']}", align="L")

        self.set_font("DejaVu", "", 9)
        self.set_xy(x + padding, self.get_y())
        self.multi_cell(w - 2 * padding, 5, f"MRP: ₹{data['MRP']}", align="L")

        # Offer + discount
        self.set_text_color(255, 0, 0)
        self.set_font("DejaVu", "B", 9)
        self.set_xy(x + padding, self.get_y())
        self.multi_cell(w - 2 * padding, 5,
                        f"Offer: ₹{data['CSP']} ({data['Discount']}%)", align="L")
        self.set_text_color(0, 0, 0)

        # Gender & Inventory
        self.set_font("DejaVu", "", 9)
        self.set_xy(x + padding, self.get_y())
        self.multi_cell(w - 2 * padding, 5,
                        f"{data['Gender']} | In Stock: {data['Inventory']}", align="L")

        if data['Remarks']:
            self.set_xy(x + padding, self.get_y())
            self.set_font("DejaVu", "I", 8)
            self.multi_cell(w - 2 * padding, 4, f"Note: {data['Remarks']}", align="L")

# Streamlit UI
st.set_page_config(page_title="Giordano Catalogue Generator", layout="wide")
st.title("🛍️ Giordano Product Catalogue Generator")

excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])
image_zip = st.file_uploader("Upload Product Images (ZIP)", type=["zip"])
logo_file = st.file_uploader("Upload Brand Logo (PNG)", type=["png"])
cards_per_row = st.selectbox("Select number of product cards per row", [2, 3])

if st.button("Generate Catalogue") and excel_file and image_zip:
    df = pd.read_excel(excel_file)
    required = {"Model", "MRP", "CSP", "Discount", "Gender", "Inventory"}
    if not required.issubset(df.columns):
        st.error("Excel must have Model, MRP, CSP, Discount, Gender, Inventory")
        st.stop()

    images = load_images_from_zip(image_zip)

    # Save logo
    logo_path = None
    if logo_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_logo:
            tmp_logo.write(logo_file.read())
            logo_path = tmp_logo.name

    pdf = StyledPDF(logo_path=logo_path, cards_per_row=cards_per_row)
    pdf.add_page()

    created_cards = 0
    mismatches = []

    grouped_products = []
    for idx, row in df.iterrows():
        model = str(row["Model"]).strip()
        model_key = os.path.splitext(model)[0]
        data = {
            "Model": model_key,
            "MRP": str(row["MRP"]),
            "CSP": str(row["CSP"]),
            "Discount": str(row["Discount"]).replace('%', ''),
            "Gender": str(row["Gender"]),
            "Inventory": str(row["Inventory"]),
            "Remarks": str(row.get("Remarks", "") or "")
        }
        image = images.get(model_key)
        if image:
            grouped_products.append((data, image))
            created_cards += 1
            if len(grouped_products) == cards_per_row:
                pdf.add_product_grid(grouped_products)
                grouped_products = []
        else:
            mismatches.append((idx + 2, model))  # Excel row number (1-based + header)

    if grouped_products:
        pdf.add_product_grid(grouped_products)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        pdf.output(tmp_pdf.name)
        with open(tmp_pdf.name, "rb") as f:
            st.download_button("📄 Download PDF Catalogue", f, file_name="giordano_catalogue.pdf")

    if mismatches:
        st.warning("⚠️ Some models in Excel did not match any image in ZIP:")
        for row_num, model in mismatches:
            st.text(f"Row {row_num}: No image found for model '{model}'")

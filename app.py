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
                    model_name = os.path.splitext(os.path.basename(filename))[0]
                    image_dict[model_name.strip()] = img
    return image_dict

class WhatsAppPDF(FPDF):
    def __init__(self, logo_path, products_per_row=2):
        super().__init__('P', 'mm', 'A4')
        self.logo_path = logo_path
        self.products_per_row = products_per_row
        self.set_auto_page_break(auto=True, margin=10)
        self.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        self.set_font("DejaVu", size=9)

    def header(self):
        if self.logo_path:
            logo_width = 50
            page_width = self.w
            x = (page_width - logo_width) / 2
            self.image(self.logo_path, x=x, y=8, w=logo_width)
            self.ln(25)

    def add_product_grid(self, products):
        padding = 5
        usable_width = self.w - 2 * 10  # side margins
        card_width = (usable_width - (self.products_per_row - 1) * padding) / self.products_per_row
        card_height = 80  # fixed height for uniform layout

        row = []
        for i, (data, image) in enumerate(products):
            row.append((data, image))
            if len(row) == self.products_per_row or i == len(products) - 1:
                y_start = self.get_y()
                for col, (data, image) in enumerate(row):
                    x = 10 + col * (card_width + padding)
                    self.set_xy(x, y_start)
                    self.product_card(data, image, card_width, card_height)
                self.ln(card_height + padding)
                row = []

    def product_card(self, data, image, card_width, card_height):
        padding = 2
        text_height = 4

        self.set_fill_color(255, 255, 255)
        self.rect(self.get_x(), self.get_y(), card_width, card_height, 'F')

        max_img_width = card_width - 2 * padding
        max_img_height = 35
        img_y_offset = self.get_y() + padding
        img_x_offset = self.get_x() + padding

        if image:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmpfile:
                image.save(tmpfile.name, format="JPEG", quality=95)
                img_w, img_h = image.size
                aspect = img_w / img_h

                display_w = max_img_width
                display_h = display_w / aspect
                if display_h > max_img_height:
                    display_h = max_img_height
                    display_w = display_h * aspect

                x_img = self.get_x() + (card_width - display_w) / 2
                self.image(tmpfile.name, x=x_img, y=img_y_offset, w=display_w, h=display_h)
                os.unlink(tmpfile.name)

        # Move to text area
        self.set_xy(self.get_x() + padding, img_y_offset + max_img_height + 2)
        self.set_font("DejaVu", "", 9)
        self.cell(card_width - 2 * padding, text_height, data['Model'], ln=1)

        self.set_font("DejaVu", "", 8)
        self.cell(card_width - 2 * padding, text_height, f"MRP: ₹{data['MRP']}", ln=1)
        self.set_text_color(0, 102, 0)
        self.cell(card_width - 2 * padding, text_height, f"Offer: ₹{data['CSP']} ({data['Discount']}%)", ln=1)
        self.set_text_color(0, 0, 0)
        self.cell(card_width - 2 * padding, text_height, f"Gender: {data['Gender']}", ln=1)
        self.cell(card_width - 2 * padding, text_height, f"Inventory: {data['Inventory']}", ln=1)
        if data.get("Remarks"):
            self.cell(card_width - 2 * padding, text_height, f"Note: {data['Remarks']}", ln=1)

# Streamlit UI
st.set_page_config(page_title="Giordano Catalogue Generator")
st.title("🛍️ Giordano WhatsApp-style Catalogue Generator")

excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])
image_zip = st.file_uploader("Upload Product Images (ZIP)", type=["zip"])
logo_file = st.file_uploader("Upload Brand Logo (PNG)", type=["png"])

products_per_row = st.selectbox("Products per row in PDF:", [2, 3], index=0)

if st.button("Generate Catalogue") and excel_file and image_zip:
    try:
        df = pd.read_excel(excel_file)
    except Exception as e:
        st.error(f"❌ Error reading Excel file: {e}")
        st.stop()

    required_columns = {"Model", "MRP", "CSP", "Discount", "Gender", "Inventory"}
    if not required_columns.issubset(df.columns):
        st.error("❌ Excel must contain: Model, MRP, CSP, Discount, Gender, Inventory (Remarks optional)")
        st.stop()

    images = load_images_from_zip(image_zip)

    logo_path = None
    if logo_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_logo:
            tmp_logo.write(logo_file.read())
            logo_path = tmp_logo.name

    pdf = WhatsAppPDF(logo_path=logo_path, products_per_row=products_per_row)
    pdf.add_page()

    created = []
    errors = []

    for idx, row in df.iterrows():
        model = str(row["Model"]).strip()
        model_key = os.path.splitext(model)[0]
        image = images.get(model_key)

        data = {
            "Model": model_key,
            "MRP": str(row["MRP"]),
            "CSP": str(row["CSP"]),
            "Discount": str(row["Discount"]),
            "Gender": str(row["Gender"]),
            "Inventory": str(row["Inventory"]),
            "Remarks": str(row.get("Remarks", ""))
        }

        if image:
            created.append((data, image))
        else:
            errors.append((idx + 2, model_key))

    pdf.add_product_grid(created)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        pdf.output(tmp_pdf.name)
        with open(tmp_pdf.name, "rb") as f:
            st.download_button("📄 Download Catalogue PDF", f, file_name="giordano_catalogue.pdf")

    if errors:
        st.subheader("⚠️ Missing Images Detected")
        for row_num, model in errors:
            st.warning(f"Row {row_num}: No image found for model '{model}'")

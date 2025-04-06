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
        super().__init__(orientation='P', unit='mm', format='A4')
        self.logo_path = logo_path
        self.products_per_row = products_per_row
        self.set_auto_page_break(auto=True, margin=10)

        self.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        self.set_font("DejaVu", size=9)

    def header(self):
        if self.logo_path:
            page_width = self.w
            logo_width = 50
            x = (page_width - logo_width) / 2
            self.image(self.logo_path, x=x, y=8, w=logo_width)
            self.ln(28)  # reserve space below logo

    def add_product_grid(self, products):
        card_width = (self.w - 20 - (self.products_per_row - 1) * 5) / self.products_per_row
        x_start = 10

        row = []
        for i, (data, image) in enumerate(products):
            row.append((data, image))
            if len(row) == self.products_per_row or i == len(products) - 1:
                y_top = self.get_y()
                max_height = 0

                # First, calculate all card heights in this row
                card_heights = []
                for data, image in row:
                    card_height = self.calculate_card_height(data, image, card_width)
                    card_heights.append(card_height)
                    max_height = max(max_height, card_height)

                # Then draw each card at its x position but same y position
                for idx, (data, image) in enumerate(row):
                    x = x_start + idx * (card_width + 5)
                    self.set_xy(x, y_top)
                    self.product_card(data, image, card_width, max_height)

                self.set_y(y_top + max_height + 10)
                row = []

    def calculate_card_height(self, data, image, card_width):
        return 85  # Standardized height to keep all rows aligned

    def product_card(self, data, image, card_width, card_height):
        card_padding = 2
        text_height = 4
        max_img_height = 40

        x = self.get_x()
        y = self.get_y()

        self.set_fill_color(255, 255, 255)
        self.rect(x, y, card_width, card_height, 'F')

        if image:
            max_img_width = card_width - 2 * card_padding
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmpfile:
                image.save(tmpfile.name, format="JPEG", quality=95)
                img_w, img_h = image.size
                aspect = img_w / img_h

                display_w = max_img_width
                display_h = display_w / aspect
                if display_h > max_img_height:
                    display_h = max_img_height
                    display_w = display_h * aspect

                x_img = x + (card_width - display_w) / 2
                y_img = y + card_padding
                self.image(tmpfile.name, x=x_img, y=y_img, w=display_w, h=display_h)
                os.unlink(tmpfile.name)

        # Move to text area
        self.set_xy(x + card_padding, y + max_img_height + 5)
        self.set_font("DejaVu", size=9)
        self.cell(card_width - 2 * card_padding, text_height, data['Model'], ln=1)

        self.set_font("DejaVu", size=8)
        self.cell(card_width - 2 * card_padding, text_height, f"MRP: ₹{data['MRP']}", ln=1)
        self.set_text_color(0, 100, 0)
        self.cell(card_width - 2 * card_padding, text_height, f"Offer: ₹{data['CSP']} ({data['Discount']})", ln=1)
        self.set_text_color(0, 0, 0)
        self.cell(card_width - 2 * card_padding, text_height, f"Gender: {data['Gender']}", ln=1)
        self.cell(card_width - 2 * card_padding, text_height, f"Inventory: {data['Inventory']}", ln=1)
        if data.get("Remarks"):
            self.cell(card_width - 2 * card_padding, text_height, f"Note: {data['Remarks']}", ln=1)

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

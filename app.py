import streamlit as st
from PIL import Image
import pandas as pd
import os
from fpdf import FPDF
import tempfile
import zipfile

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
        self.set_auto_page_break(auto=True, margin=15)
        self.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        self.set_font("DejaVu", size=9)

    def header(self):
        if self.logo_path:
            logo_width = 50
            x = (self.w - logo_width) / 2
            self.image(self.logo_path, x=x, y=8, w=logo_width)
            self.ln(25)  # reserve space below logo

    def add_product_grid(self, products):
        spacing = 5
        margin = 10
        card_width = (self.w - 2 * margin - (self.products_per_row - 1) * spacing) / self.products_per_row
        y = self.get_y()

        row_data = []
        for idx, (data, image) in enumerate(products):
            row_data.append((data, image))

            # Render the row once it's filled or last row
            if len(row_data) == self.products_per_row or idx == len(products) - 1:
                # Measure max card height in row
                heights = []
                for d, img in row_data:
                    heights.append(self.calculate_card_height(img))
                row_height = max(heights) + 35  # extra space for text

                # If next row doesn't fit, start new page
                if y + row_height > self.h - 15:
                    self.add_page()
                    y = self.get_y()

                for i, (d, img) in enumerate(row_data):
                    x = margin + i * (card_width + spacing)
                    self.set_xy(x, y)
                    self.draw_card(d, img, card_width)

                y += row_height + 5
                self.set_y(y)
                row_data = []

    def calculate_card_height(self, image):
        return 45  # consistent max image height

    def draw_card(self, data, image, card_width):
        card_padding = 2
        text_height = 4
        card_height = self.calculate_card_height(image) + 35

        x_start = self.get_x()
        y_start = self.get_y()

        self.set_fill_color(255, 255, 255)
        self.rect(x_start, y_start, card_width, card_height, 'F')

        if image:
            max_img_w = card_width - 2 * card_padding
            max_img_h = 45

            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmpfile:
                image.save(tmpfile.name, format="JPEG", quality=95)
                iw, ih = image.size
                aspect = iw / ih

                display_w = max_img_w
                display_h = display_w / aspect
                if display_h > max_img_h:
                    display_h = max_img_h
                    display_w = display_h * aspect

                x_img = x_start + (card_width - display_w) / 2
                y_img = y_start + card_padding
                self.image(tmpfile.name, x=x_img, y=y_img, w=display_w, h=display_h)
                os.unlink(tmpfile.name)

        # Draw text below image
        self.set_xy(x_start + card_padding, y_start + max_img_h + 2)
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

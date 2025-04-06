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
    def __init__(self, logo_path=None, products_per_row=2):
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
            self.ln(25)  # Extra space after logo

    def add_product_grid(self, products):
        margin_x = 10
        spacing_x = 5
        spacing_y = 10
        card_width = (self.w - 2 * margin_x - (self.products_per_row - 1) * spacing_x) / self.products_per_row

        row = []
        for idx, (data, image) in enumerate(products):
            row.append((data, image))
            if len(row) == self.products_per_row or idx == len(products) - 1:
                x_positions = []
                y_top = self.get_y()
                max_height = 0
                images_tempfiles = []

                for i, (data, image) in enumerate(row):
                    x = margin_x + i * (card_width + spacing_x)
                    y = y_top

                    # Save image temporarily
                    temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                    image.save(temp_img.name, format="JPEG", quality=95)
                    images_tempfiles.append(temp_img.name)

                    # Estimate image size
                    max_img_width = card_width - 4
                    max_img_height = 40
                    img_w, img_h = image.size
                    aspect_ratio = img_w / img_h

                    display_w = max_img_width
                    display_h = display_w / aspect_ratio
                    if display_h > max_img_height:
                        display_h = max_img_height
                        display_w = display_h * aspect_ratio

                    x_img = x + (card_width - display_w) / 2
                    self.image(temp_img.name, x=x_img, y=y, w=display_w, h=display_h)

                    y_text = y + display_h + 2
                    self.set_xy(x + 2, y_text)
                    self.set_font("DejaVu", size=9)
                    self.multi_cell(card_width - 4, 4, data['Model'], align='L')

                    self.set_font("DejaVu", size=8)
                    self.cell(card_width - 4, 4, f"MRP: ₹{data['MRP']}", ln=1)
                    self.set_text_color(0, 100, 0)
                    self.cell(card_width - 4, 4, f"Offer: ₹{data['CSP']} ({data['Discount']})", ln=1)
                    self.set_text_color(0, 0, 0)
                    self.cell(card_width - 4, 4, f"Gender: {data['Gender']}", ln=1)
                    self.cell(card_width - 4, 4, f"Inventory: {data['Inventory']}", ln=1)
                    if data.get("Remarks"):
                        self.cell(card_width - 4, 4, f"Note: {data['Remarks']}", ln=1)

                    max_y = self.get_y()
                    max_height = max(max_height, max_y - y)

                self.ln(max_height + spacing_y)

                for file in images_tempfiles:
                    os.unlink(file)

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

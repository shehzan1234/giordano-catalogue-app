import streamlit as st
from fpdf import FPDF
import pandas as pd
from PIL import Image
import tempfile
import os
import zipfile

# Load images from ZIP
def load_images_from_zip(zip_file):
    image_dict = {}
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        for file in zip_ref.namelist():
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                name = os.path.splitext(os.path.basename(file))[0].strip()
                with zip_ref.open(file) as image_file:
                    img = Image.open(image_file).convert("RGB")
                    image_dict[name] = img
    return image_dict

# Custom PDF class
class PDF(FPDF):
    def __init__(self, logo_path, products_per_row):
        super().__init__()
        self.logo_path = logo_path
        self.products_per_row = products_per_row
        self.set_auto_page_break(auto=True, margin=10)
        self.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        self.set_font("DejaVu", "", 9)

    def header(self):
        if self.logo_path:
            logo_width = 45
            page_width = self.w
            x = (page_width - logo_width) / 2
            self.image(self.logo_path, x=x, y=8, w=logo_width)
            self.ln(25)

    def add_products(self, products):
        margin = 10
        spacing = 5
        available_width = self.w - 2 * margin - (self.products_per_row - 1) * spacing
        card_width = available_width / self.products_per_row
        card_height = 80
        max_img_height = 35
        padding = 2

        x_start = margin
        y_start = self.get_y()

        row = []
        for i, (data, image) in enumerate(products):
            row.append((data, image))
            if len(row) == self.products_per_row or i == len(products) - 1:
                max_y = self.get_y()
                for col, (data, image) in enumerate(row):
                    x = x_start + col * (card_width + spacing)
                    y = max_y
                    self.set_xy(x, y)

                    # Card background
                    self.set_fill_color(255, 255, 255)
                    self.rect(x, y, card_width, card_height, 'F')

                    # Product image
                    if image:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_img:
                            image.save(tmp_img.name, format="JPEG", quality=95)
                            iw, ih = image.size
                            aspect = iw / ih
                            img_w = card_width - 2 * padding
                            img_h = img_w / aspect
                            if img_h > max_img_height:
                                img_h = max_img_height
                                img_w = img_h * aspect
                            img_x = x + (card_width - img_w) / 2
                            img_y = y + padding
                            self.image(tmp_img.name, x=img_x, y=img_y, w=img_w, h=img_h)
                            os.unlink(tmp_img.name)

                    # Product text
                    self.set_xy(x + padding, y + max_img_height + padding + 1)
                    self.set_font("DejaVu", "", 9)
                    self.cell(card_width - 2 * padding, 4, f"{data['Model']}", ln=1)

                    self.set_font("DejaVu", "", 8)
                    self.cell(card_width - 2 * padding, 4, f"MRP: ₹{data['MRP']}", ln=1)
                    self.set_text_color(0, 100, 0)
                    self.cell(card_width - 2 * padding, 4, f"Offer: ₹{data['CSP']} ({data['Discount']}%)", ln=1)
                    self.set_text_color(0, 0, 0)
                    self.cell(card_width - 2 * padding, 4, f"Gender: {data['Gender']}", ln=1)
                    self.cell(card_width - 2 * padding, 4, f"Inventory: {data['Inventory']}", ln=1)
                    if data.get("Remarks"):
                        self.multi_cell(card_width - 2 * padding, 4, f"Note: {data['Remarks']}")

                self.ln(card_height + spacing)
                row = []

# Streamlit app
st.set_page_config(page_title="Giordano Catalogue Generator")
st.title("🛍️ Giordano WhatsApp-style Catalogue Generator")

excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])
zip_file = st.file_uploader("Upload Product Images ZIP", type=["zip"])
logo_file = st.file_uploader("Upload Logo (PNG)", type=["png"])
products_per_row = st.selectbox("Products per row in PDF", [2, 3], index=0)

if st.button("Generate PDF") and excel_file and zip_file:
    try:
        df = pd.read_excel(excel_file)
    except Exception as e:
        st.error(f"Error reading Excel: {e}")
        st.stop()

    required_cols = {"Model", "MRP", "CSP", "Discount", "Gender", "Inventory"}
    if not required_cols.issubset(df.columns):
        st.error("Excel must contain: Model, MRP, CSP, Discount, Gender, Inventory")
        st.stop()

    images = load_images_from_zip(zip_file)

    logo_path = None
    if logo_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_logo:
            tmp_logo.write(logo_file.read())
            logo_path = tmp_logo.name

    pdf = PDF(logo_path=logo_path, products_per_row=products_per_row)
    pdf.add_page()

    data_list = []
    errors = []
    for idx, row in df.iterrows():
        model = str(row["Model"]).strip()
        model_key = os.path.splitext(model)[0]
        img = images.get(model_key)
        product_data = {
            "Model": model_key,
            "MRP": row["MRP"],
            "CSP": row["CSP"],
            "Discount": row["Discount"],
            "Gender": row["Gender"],
            "Inventory": row["Inventory"],
            "Remarks": row.get("Remarks", "")
        }
        if img:
            data_list.append((product_data, img))
        else:
            errors.append((idx + 2, model_key))  # Excel row number

    pdf.add_products(data_list)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        pdf.output(tmp_pdf.name)
        with open(tmp_pdf.name, "rb") as f:
            st.download_button("📄 Download Final Catalogue PDF", f, file_name="giordano_catalogue.pdf")

    if errors:
        st.subheader("⚠️ Missing Images")
        for row_num, model in errors:
            st.warning(f"Row {row_num}: No image found for model '{model}'")

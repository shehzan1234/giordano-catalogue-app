import streamlit as st
import pandas as pd
import os
from PIL import Image
import tempfile
import zipfile
from fpdf import FPDF

# Load images from ZIP
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

# Enhanced WhatsApp-style PDF
class CataloguePDF(FPDF):
    def __init__(self, logo_path, columns=2):
        super().__init__()
        self.logo_path = logo_path
        self.columns = columns
        self.set_auto_page_break(auto=True, margin=15)
        self.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        self.set_font("DejaVu", "", 12)
        self.margin = 10
        self.card_width = (210 - 2 * self.margin - (columns - 1) * 5) / columns
        self.card_height = 100
        self.x_start = self.margin
        self.y_start = self.get_y()
        self.card_count = 0

    def header(self):
        if self.logo_path:
            self.set_y(10)
            logo_width = 40
            self.image(self.logo_path, x=(210 - logo_width) / 2, y=10, w=logo_width)
            self.ln(25)

    def product_card(self, data, image):
        x = self.x_start + (self.card_count % self.columns) * (self.card_width + 5)
        y = self.get_y()

        self.set_xy(x, y)

        # Card background (white with soft border)
        self.set_fill_color(255, 255, 255)
        self.set_draw_color(230, 230, 230)
        self.rect(x, y, self.card_width, self.card_height, 'DF')

        # Image
        if image:
            img_w = self.card_width - 10
            img_h = 45
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmpfile:
                image.save(tmpfile.name)
                self.image(tmpfile.name, x + 5, y + 5, w=img_w, h=img_h, type='JPG')
                os.unlink(tmpfile.name)

        # Text Content
        text_y = y + 52
        self.set_xy(x + 5, text_y)
        self.set_font("DejaVu", "B", 10)
        self.multi_cell(self.card_width - 10, 5, f"{data['Model']}", align='L')

        self.set_font("DejaVu", "", 9)
        self.set_xy(x + 5, self.get_y())
        self.cell(self.card_width - 10, 5, f"MRP: ₹{data['MRP']}", ln=1)

        self.set_font("DejaVu", "B", 9)
        self.set_text_color(0, 100, 0)
        self.cell(self.card_width - 10, 5, f"Offer: ₹{data['CSP']} ({data['Discount']} OFF)", ln=1)
        self.set_text_color(0, 0, 0)

        self.set_font("DejaVu", "", 9)
        self.cell(self.card_width - 10, 5, f"Gender: {data['Gender']}", ln=1)
        self.cell(self.card_width - 10, 5, f"Inventory: {data['Inventory']}", ln=1)

        if data['Remarks'] and data['Remarks'].lower() != 'nan':
            self.set_font("DejaVu", "I", 8)
            self.set_text_color(80, 80, 80)
            self.multi_cell(self.card_width - 10, 4, f"Note: {data['Remarks']}")
            self.set_text_color(0, 0, 0)

        self.card_count += 1
        if self.card_count % self.columns == 0:
            self.ln(self.card_height + 5)

# Streamlit app
st.set_page_config(page_title="Giordano Catalogue Generator", layout="centered")
st.title("🛍️ Giordano WhatsApp-style Catalogue Generator")

excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])
image_zip = st.file_uploader("Upload Product Images (ZIP)", type=["zip"])
logo_file = st.file_uploader("Upload Brand Logo (PNG)", type=["png"])
columns_per_row = st.radio("Select number of products per row in PDF", [2, 3], index=0)

if st.button("Generate Catalogue") and excel_file and image_zip:
    try:
        df = pd.read_excel(excel_file)
    except Exception as e:
        st.error(f"❌ Error reading Excel file: {e}")
        st.stop()

    required_cols = {"Model", "MRP", "CSP", "Discount", "Gender", "Inventory"}
    if not required_cols.issubset(df.columns):
        st.error("❌ Excel must contain: Model, MRP, CSP, Discount, Gender, Inventory (Remarks optional)")
        st.stop()

    images = load_images_from_zip(image_zip)

    # Save logo to temp file
    logo_path = None
    if logo_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_logo:
            tmp_logo.write(logo_file.read())
            logo_path = tmp_logo.name

    pdf = CataloguePDF(logo_path=logo_path, columns=columns_per_row)
    pdf.add_page()

    missing_rows = []
    for idx, row in df.iterrows():
        model = str(row["Model"]).strip().split(".")[0]
        data = {
            "Model": model,
            "MRP": str(row["MRP"]),
            "CSP": str(row["CSP"]),
            "Discount": str(row["Discount"]),
            "Gender": str(row["Gender"]),
            "Inventory": str(row["Inventory"]),
            "Remarks": str(row.get("Remarks", ""))
        }
        image = images.get(model)
        if image:
            pdf.product_card(data, image)
        else:
            missing_rows.append((idx + 2, model))  # +2 for Excel row number incl. header

    if missing_rows:
        st.warning("⚠️ Some models were missing images:")
        for row_num, missing_model in missing_rows:
            st.text(f"Row {row_num}: {missing_model}")

    if pdf.card_count == 0:
        st.error("❌ No product cards were created. Check image names and Excel formatting.")
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            pdf.output(tmp_pdf.name)
            with open(tmp_pdf.name, "rb") as f:
                st.download_button("📄 Download Catalogue PDF", f, file_name="giordano_catalogue.pdf")

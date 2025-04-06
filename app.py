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

# PDF generator class with Unicode support
class WhatsAppPDF(FPDF):
    def __init__(self, logo_path, products_per_row=2):
        super().__init__()
        self.logo_path = logo_path
        self.products_per_row = products_per_row
        self.set_auto_page_break(auto=True, margin=10)

        self.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        self.set_font("DejaVu", "", 10)

        self.margin = 10
        self.cell_width = (210 - 2 * self.margin) / self.products_per_row
        self.cell_height = 90
        self.col = 0

    def header(self):
        if self.logo_path:
            self.set_y(10)
            self.set_x((210 - 50) / 2)
            self.image(self.logo_path, x=self.get_x(), y=self.get_y(), w=50)
            self.ln(30)

    def add_product_card(self, data, image):
        x = self.margin + self.col * self.cell_width
        y = self.get_y()

        self.set_xy(x, y)
        self.set_fill_color(255, 255, 255)
        self.rect(x, y, self.cell_width, self.cell_height + 60, 'F')

        if image:
            img_w, img_h = image.size
            max_w = self.cell_width - 10
            max_h = self.cell_height
            ratio = min(max_w / img_w, max_h / img_h)
            display_w = img_w * ratio
            display_h = img_h * ratio
            img_x = x + (self.cell_width - display_w) / 2
            img_y = y + 5

            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmpfile:
                image.save(tmpfile.name)
                self.image(tmpfile.name, x=img_x, y=img_y, w=display_w, h=display_h)
                os.unlink(tmpfile.name)

        self.set_xy(x + 2, y + self.cell_height + 5)
        lines = [
            f"{data['Model']}",
            f"MRP: ₹{data['MRP']}",
            f"Offer Price: ₹{data['CSP']} ({data['Discount']} OFF)",
            f"Gender: {data['Gender']}",
            f"Inventory: {data['Inventory']}"
        ]
        if data.get("Remarks"):
            lines.append(f"Note: {data['Remarks']}")

        for line in lines:
            self.cell(self.cell_width - 4, 6, line, ln=1)

        self.col += 1
        if self.col >= self.products_per_row:
            self.col = 0
            self.ln(self.cell_height + 65)

# Streamlit UI
st.set_page_config(page_title="Giordano Catalogue Generator")
st.title("🛍️ Giordano WhatsApp-style Catalogue Generator")

excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])
image_zip = st.file_uploader("Upload Product Images (ZIP)", type=["zip"])
logo_file = st.file_uploader("Upload Brand Logo (PNG)", type=["png"])
products_per_row = st.selectbox("How many products per row?", [2, 3])

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

    # Save logo to temp file if uploaded
    logo_path = None
    if logo_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_logo:
            tmp_logo.write(logo_file.read())
            logo_path = tmp_logo.name

    pdf = WhatsAppPDF(logo_path=logo_path, products_per_row=products_per_row)
    pdf.add_page()

    created_cards = 0
    for _, row in df.iterrows():
        model = str(row["Model"]).strip()
        model_key = os.path.splitext(model)[0]
        data = {
            "Model": model_key,
            "MRP": str(row["MRP"]),
            "CSP": str(row["CSP"]),
            "Discount": str(row["Discount"]),
            "Gender": str(row["Gender"]),
            "Inventory": str(row["Inventory"]),
            "Remarks": str(row.get("Remarks", ""))
        }
        image = images.get(model_key)
        if image:
            pdf.add_product_card(data, image)
            created_cards += 1
        else:
            st.warning(f"⚠️ No image found for model: {model_key}")

    if created_cards == 0:
        st.error("❌ No product cards were created. Check image names in Excel and ZIP.")
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            pdf.output(tmp_pdf.name)
            with open(tmp_pdf.name, "rb") as f:
                st.download_button("📄 Download Catalogue PDF", f, file_name="giordano_catalogue.pdf")

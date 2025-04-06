import streamlit as st
from PIL import Image
import pandas as pd
import os
from fpdf import FPDF
import tempfile
import zipfile

# Load images from ZIP file
def load_images_from_zip(zip_file):
    image_dict = {}
    with zipfile.ZipFile(zip_file, 'r') as z:
        for filename in z.namelist():
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                with z.open(filename) as file:
                    img = Image.open(file).convert("RGB")
                    image_dict[filename.strip()] = img
    return image_dict

# PDF Generator with Unicode support
class WhatsAppPDF(FPDF):
    def __init__(self, logo_path):
        super().__init__()
        self.logo_path = logo_path
        self.set_auto_page_break(auto=True, margin=15)

        # Load DejaVu font (must be in same folder as app)
        self.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        self.set_font("DejaVu", "", 12)

    def header(self):
        if self.logo_path:
            self.image(self.logo_path, 10, 8, 33)
        self.set_font("DejaVu", "", 15)
        self.cell(80)
        self.cell(30, 10, 'Product Catalogue', 0, 0, 'C')
        self.ln(20)

    def product_card(self, data, image):
        self.set_font("DejaVu", "", 12)
        self.set_fill_color(220, 248, 198)

        lines = [
            f"{data['Model']}",
            f"MRP: ₹{data['MRP']}",
            f"Offer Price: ₹{data['CSP']} ({data['Discount']} OFF)",
            f"Gender: {data['Gender']}",
            f"Inventory: {data['Inventory']}"
        ]
        if data.get("Remarks") and data["Remarks"].strip().lower() != "nan":
            lines.append(f"Note: {data['Remarks']}")

        full_text = "\n".join(lines)
        self.multi_cell(0, 10, full_text, border=1, fill=True)

        if image:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmpfile:
                image.save(tmpfile.name)
                self.image(tmpfile.name, w=60)
                os.unlink(tmpfile.name)
        self.ln(5)

# Streamlit App UI
st.set_page_config(page_title="Giordano Catalogue Generator")
st.title("🛍️ Giordano WhatsApp-style Catalogue Generator")

excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])
image_zip = st.file_uploader("Upload Product Images (ZIP)", type=["zip"])
logo_file = st.file_uploader("Upload Brand Logo (PNG)", type=["png"])

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

    if logo_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_logo:
            tmp_logo.write(logo_file.read())
            logo_path = tmp_logo.name
    else:
        logo_path = None

    pdf = WhatsAppPDF(logo_path=logo_path)
    pdf.add_page()

    created_cards = 0
    for _, row in df.iterrows():
        model_raw = str(row["Model"]).strip()
        model_with_ext = model_raw + ".jpg"
        data = {
            "Model": model_raw,
            "MRP": str(row["MRP"]),
            "CSP": str(row["CSP"]),
            "Discount": str(row["Discount"]),
            "Gender": str(row["Gender"]),
            "Inventory": str(row["Inventory"]),
            "Remarks": str(row.get("Remarks", ""))
        }
        image = images.get(model_with_ext)
        if image:
            pdf.product_card(data, image)
            created_cards += 1
        else:
            st.warning(f"⚠️ No image found for model: {model_raw} (looking for {model_with_ext})")

    if created_cards == 0:
        st.error("❌ No product cards were created. Check image names in Excel and ZIP.")
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            pdf.output(tmp_pdf.name)
            with open(tmp_pdf.name, "rb") as f:
                st.download_button("📄 Download Catalogue PDF", f, file_name="giordano_catalogue.pdf")

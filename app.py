import streamlit as st
from PIL import Image
import pandas as pd
import os
from fpdf import FPDF
import tempfile
import zipfile

# --- Helper function to load images from zip ---
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

# --- WhatsApp-style PDF Generator ---
class WhatsAppPDF(FPDF):
    def __init__(self, logo_path):
        super().__init__()
        self.logo_path = logo_path
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        if self.logo_path:
            self.image(self.logo_path, 10, 8, 33)
        self.set_font('Arial', 'B', 15)
        self.cell(80)
        self.cell(30, 10, 'Product Catalogue', 0, 0, 'C')
        self.ln(20)

    def product_card(self, model, name, price, image):
        self.set_font("Arial", '', 12)
        self.set_fill_color(220, 248, 198)  # WhatsApp green bubble
        self.multi_cell(0, 10, f"{model} - {name}\nPrice: ₹{price}", border=1, fill=True)
        if image:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmpfile:
                image.save(tmpfile.name)
                self.image(tmpfile.name, w=60)
                os.unlink(tmpfile.name)
        self.ln(5)

# --- Streamlit App ---
st.set_page_config(page_title="Giordano Catalogue Generator")
st.title("🛍️ Giordano WhatsApp-style Catalogue Generator")

excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])
image_zip = st.file_uploader("Upload Product Images (ZIP)", type=["zip"])
logo_file = st.file_uploader("Upload Brand Logo (PNG)", type=["png"])

if st.button("Generate Catalogue") and excel_file and image_zip:
    df = pd.read_excel(excel_file)
    images = load_images_from_zip(image_zip)
    model_col = "Model" if "Model" in df.columns else df.columns[0]

    st.subheader("🧾 Debug Info")
    st.text("✅ Models from Excel:")
    excel_models = df[model_col].astype(str).str.strip().tolist()
    st.write(excel_models)

    st.text("🖼️ Images Found:")
    image_models = list(images.keys())
    st.write(image_models)

    missing_images = [m for m in excel_models if m not in image_models]
    if missing_images:
        st.warning(f"⚠️ No image found for: {', '.join(missing_images)}")

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
        model = str(row[model_col]).strip()
        name = str(row.get("Name", ""))
        price = str(row.get("Price", ""))
        image = images.get(model)
        if image:
            pdf.product_card(model, name, price, image)
            created_cards += 1
        else:
            st.error(f"❌ No image found for model: {model}")

    if created_cards == 0:
        st.error("❌ No product cards were created. Check image names in Excel and ZIP.")
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            pdf.output(tmp_pdf.name)
            with open(tmp_pdf.name, "rb") as f:
                st.download_button("📄 Download Catalogue PDF", f, file_name="giordano_catalogue.pdf")

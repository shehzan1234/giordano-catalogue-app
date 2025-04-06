import streamlit as st
from PIL import Image
import pandas as pd
import os
from fpdf import FPDF
import tempfile
import zipfile

# Load images from ZIP
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

# WhatsApp Style PDF
class WhatsAppPDF(FPDF):
    def __init__(self, logo_path, cards_per_row=2):
        super().__init__()
        self.logo_path = logo_path
        self.cards_per_row = cards_per_row
        self.set_auto_page_break(auto=True, margin=15)
        self.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        self.set_font("DejaVu", "", 10)

    def header(self):
        if self.logo_path:
            page_width = self.w - 20
            self.image(self.logo_path, x=(210 - 50) / 2, y=10, w=50)  # Centered logo
            self.ln(25)

    def add_product_grid(self, products, images):
        card_width = (self.w - 20 - ((self.cards_per_row - 1) * 5)) / self.cards_per_row
        card_height = 90
        x_start = 10
        y = self.get_y()

        for idx, product in enumerate(products):
            x = x_start + (idx % self.cards_per_row) * (card_width + 5)
            if idx % self.cards_per_row == 0 and idx != 0:
                y += card_height + 10
            self.set_xy(x, y)

            # Draw card background
            self.set_fill_color(240, 255, 240)
            self.rect(x, y, card_width, card_height, 'F')

            # Draw image
            image = images.get(product["Model"])
            if image:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmpfile:
                    image.save(tmpfile.name)
                    iw, ih = image.size
                    max_w, max_h = card_width - 10, 45
                    ratio = min(max_w / iw, max_h / ih)
                    w, h = iw * ratio, ih * ratio
                    img_x = x + (card_width - w) / 2
                    self.image(tmpfile.name, x=img_x, y=y + 3, w=w, h=h)
                    os.unlink(tmpfile.name)

            # Draw text
            self.set_xy(x + 3, y + 50)
            lines = [
                f"{product['Model']}",
                f"MRP: ₹{product['MRP']}",
                f"Offer: ₹{product['CSP']} ({product['Discount']} OFF)",
                f"Gender: {product['Gender']}",
                f"Inventory: {product['Inventory']}"
            ]
            if product.get("Remarks") and product["Remarks"] != "nan":
                lines.append(f"Note: {product['Remarks']}")
            for line in lines:
                self.cell(card_width - 6, 5, line, ln=1)

        self.ln(card_height + 10)

# Streamlit App
st.set_page_config(page_title="Giordano Catalogue Generator")
st.title("🛍️ Giordano WhatsApp-style Catalogue Generator")

excel_file = st.file_uploader("📄 Upload Excel File", type=["xlsx"])
image_zip = st.file_uploader("🖼️ Upload Product Images (.zip)", type=["zip"])
logo_file = st.file_uploader("🏷️ Upload Brand Logo (.png)", type=["png"])
cards_per_row = st.selectbox("🧩 Products Per Row in PDF", [2, 3], index=0)

if st.button("🚀 Generate Catalogue") and excel_file and image_zip:
    df = pd.read_excel(excel_file)
    required_columns = {"Model", "MRP", "CSP", "Discount", "Gender", "Inventory"}
    if not required_columns.issubset(df.columns):
        st.error("❌ Excel must include columns: Model, MRP, CSP, Discount, Gender, Inventory (Remarks optional)")
        st.stop()

    images = load_images_from_zip(image_zip)

    # Save logo to temp
    logo_path = None
    if logo_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_logo:
            tmp_logo.write(logo_file.read())
            logo_path = tmp_logo.name

    pdf = WhatsAppPDF(logo_path=logo_path, cards_per_row=cards_per_row)
    pdf.add_page()

    created_cards = 0
    products = []
    for _, row in df.iterrows():
        model = str(row["Model"]).strip()
        data = {
            "Model": model,
            "MRP": str(row["MRP"]),
            "CSP": str(row["CSP"]),
            "Discount": str(row["Discount"]),
            "Gender": str(row["Gender"]),
            "Inventory": str(row["Inventory"]),
            "Remarks": str(row.get("Remarks", ""))
        }
        if model in images:
            products.append(data)
            created_cards += 1
        else:
            st.warning(f"⚠️ No image found for model: {model}")

    if created_cards == 0:
        st.error("❌ No matching product images found. Check ZIP and Excel model names.")
        st.stop()

    pdf.add_product_grid(products, images)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        pdf.output(tmp_pdf.name)
        with open(tmp_pdf.name, "rb") as f:
            st.download_button("📄 Download PDF", f, file_name="giordano_catalogue.pdf")

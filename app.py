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

# PDF Generator
class WhatsAppPDF(FPDF):
    def __init__(self, logo_path):
        super().__init__()
        self.logo_path = logo_path
        self.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        self.set_auto_page_break(auto=True, margin=15)
        self.set_font("DejaVu", "", 10)

    def header(self):
        if self.logo_path:
            with Image.open(self.logo_path) as img:
                w, h = img.size
                max_w = 50
                aspect_ratio = h / w
                display_w = max_w
                display_h = max_w * aspect_ratio
                page_width = self.w - 2 * self.l_margin
                x_center = self.l_margin + (page_width - display_w) / 2
                self.image(self.logo_path, x=x_center, y=8, w=display_w, h=display_h)
                self.ln(display_h + 10)
        else:
            self.ln(20)

    def add_product_grid(self, products, images, cards_per_row=2):
        card_width = (self.w - 2 * self.l_margin - ((cards_per_row - 1) * 5)) / cards_per_row
        max_img_height = 60
        y_start = self.get_y()

        for i, data in enumerate(products):
            x = self.l_margin + (i % cards_per_row) * (card_width + 5)
            if i % cards_per_row == 0 and i != 0:
                y_start = self.get_y() + max_img_height + 35
                self.set_y(y_start)

            self.set_xy(x, y_start)

            # Image
            image = images.get(data['Model'])
            if image:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmpfile:
                    image.thumbnail((card_width, max_img_height), Image.LANCZOS)
                    image.save(tmpfile.name)
                    self.image(tmpfile.name, x=x + (card_width - image.width * 0.75) / 2, y=y_start, w=image.width * 0.75)
                    os.unlink(tmpfile.name)

            # Text box below image
            self.set_xy(x, y_start + max_img_height + 2)
            lines = [
                f"{data['Model']}",
                f"MRP: ₹{data['MRP']}",
                f"Offer Price: ₹{data['CSP']} ({data['Discount']}% OFF)",
                f"Gender: {data['Gender']}",
                f"Inventory: {data['Inventory']}"
            ]
            if data.get("Remarks") and str(data["Remarks"]).strip().lower() != 'nan':
                lines.append(f"Note: {data['Remarks']}")

            self.set_fill_color(220, 248, 198)
            text = "\n".join(lines)
            self.multi_cell(card_width, 5, text, border=1, fill=True)

# Streamlit UI
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

    # Save logo to temp
    if logo_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_logo:
            tmp_logo.write(logo_file.read())
            logo_path = tmp_logo.name
    else:
        logo_path = None

    pdf = WhatsAppPDF(logo_path=logo_path)
    pdf.add_page()

    # Prepare product data
    product_data = []
    for _, row in df.iterrows():
        model = os.path.splitext(str(row["Model"]).strip())[0]
        product_data.append({
            "Model": model,
            "MRP": str(row["MRP"]),
            "CSP": str(row["CSP"]),
            "Discount": str(row["Discount"]),
            "Gender": str(row["Gender"]),
            "Inventory": str(row["Inventory"]),
            "Remarks": str(row.get("Remarks", ""))
        })

    if not any(model['Model'] in images for model in product_data):
        st.error("❌ No matching product images found for any models.")
        st.stop()

    pdf.add_product_grid(product_data, images)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        pdf.output(tmp_pdf.name)
        with open(tmp_pdf.name, "rb") as f:
            st.download_button("📄 Download Catalogue PDF", f, file_name="giordano_catalogue.pdf")

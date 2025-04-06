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
                    model_name = os.path.splitext(os.path.basename(filename))[0]
                    image_dict[model_name.strip()] = img
    return image_dict

# PDF class with Unicode and layout support
class WhatsAppPDF(FPDF):
    def __init__(self, logo_path):
        super().__init__()
        self.logo_path = logo_path
        self.set_auto_page_break(auto=True, margin=15)

        self.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        self.set_font("DejaVu", "", 10)

    def header(self):
        if self.logo_path:
            self.image(self.logo_path, x=80, y=10, w=50)
            self.ln(30)
        else:
            self.ln(10)

    def add_product_grid(self, products):
        card_width = 95
        card_height = 120
        margin_x = 10
        margin_y = 10
        spacing_x = 5
        spacing_y = 5
        cards_per_row = 2

        x_start = margin_x
        y = self.get_y()

        for index, (data, image) in enumerate(products):
            x = x_start + (index % cards_per_row) * (card_width + spacing_x)
            if index % cards_per_row == 0 and index != 0:
                y += card_height + spacing_y
                self.set_y(y)
                self.set_x(x_start)
            else:
                self.set_xy(x, y)

            # Draw the card background
            self.set_fill_color(220, 248, 198)
            self.rect(x, y, card_width, card_height, style='F')

            # Add image proportionally
            if image:
                img_w, img_h = image.size
                aspect_ratio = img_w / img_h
                max_img_w = card_width - 10
                max_img_h = 50

                if img_w > img_h:
                    new_w = max_img_w
                    new_h = new_w / aspect_ratio
                else:
                    new_h = max_img_h
                    new_w = new_h * aspect_ratio

                new_w = min(new_w, max_img_w)
                new_h = min(new_h, max_img_h)

                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmpfile:
                    image.save(tmpfile.name)
                    self.image(tmpfile.name, x + (card_width - new_w) / 2, y + 5, w=new_w, h=new_h)
                    os.unlink(tmpfile.name)

            # Add text info
            self.set_xy(x + 3, y + 60)
            lines = [
                f"{data['Model']}",
                f"MRP: ₹{data['MRP']}",
                f"Offer: ₹{data['CSP']} ({data['Discount']} OFF)",
                f"Gender: {data['Gender']}",
                f"Stock: {data['Inventory']}",
            ]
            if data.get("Remarks"):
                lines.append(f"Note: {data['Remarks']}")

            for line in lines:
                self.multi_cell(card_width - 6, 5, line, border=0)

# Streamlit UI
st.set_page_config(page_title="Giordano Catalogue Generator")
st.title("🛍️ Giordano WhatsApp-style Catalogue Generator")

excel_file = st.file_uploader("📄 Upload Excel File", type=["xlsx"])
image_zip = st.file_uploader("🖼️ Upload Product Images (ZIP)", type=["zip"])
logo_file = st.file_uploader("🏷️ Upload Brand Logo (PNG)", type=["png"])

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

    # Save logo to temp path
    logo_path = None
    if logo_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_logo:
            tmp_logo.write(logo_file.read())
            logo_path = tmp_logo.name

    pdf = WhatsAppPDF(logo_path=logo_path)
    pdf.add_page()

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
        image = images.get(model)
        if image:
            products.append((data, image))
        else:
            st.warning(f"⚠️ No image found for model: {model}")

    if not products:
        st.error("❌ No product cards were created. Check image names in Excel and ZIP.")
    else:
        pdf.add_product_grid(products)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            pdf.output(tmp_pdf.name)
            with open(tmp_pdf.name, "rb") as f:
                st.download_button("📄 Download Catalogue PDF", f, file_name="giordano_catalogue.pdf")

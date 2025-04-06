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
                    key = os.path.splitext(os.path.basename(filename))[0].strip().lower()
                    image_dict[key] = img
    return image_dict

# Unicode PDF with proper grid layout
class GridPDF(FPDF):
    def __init__(self, logo_path, items_per_row=2):
        super().__init__()
        self.logo_path = logo_path
        self.items_per_row = items_per_row
        self.margin = 10
        self.spacing = 10
        self.card_width = (self.w - 2 * self.margin - (items_per_row - 1) * self.spacing) / items_per_row
        self.card_height = 80

        self.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        self.set_font("DejaVu", "", 10)
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        if self.logo_path:
            self.image(self.logo_path, 10, 8, 33)
        self.set_font("DejaVu", "", 14)
        self.cell(0, 10, "Product Catalogue", 0, 1, "C")
        self.ln(10)

    def product_grid(self, products):
        x_start = self.margin
        y = self.get_y()
        initial_y = y
        row_height = self.card_height + 60  # room for image + text

        for index, (data, image) in enumerate(products):
            col = index % self.items_per_row
            x = x_start + col * (self.card_width + self.spacing)

            # Start new row if at first column and not first product
            if col == 0 and index != 0:
                y += row_height
                self.set_y(y)

            # Draw card image
            if image:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_img:
                    image.save(tmp_img.name, format="JPEG")
                    self.image(tmp_img.name, x, y, self.card_width, 40)
                    os.unlink(tmp_img.name)

            # Text
            self.set_xy(x, y + 42)
            discount = data["Discount"]
            if not str(discount).endswith("%"):
                discount = f"{discount}%"

            lines = [
                f"{data['Model']}",
                f"MRP: ₹{data['MRP']}",
                f"Offer: ₹{data['CSP']} ({discount} OFF)",
                f"Gender: {data['Gender']}",
                f"Inventory: {data['Inventory']}",
            ]
            if data.get("Remarks") and str(data["Remarks"]).strip().lower() != "nan":
                lines.append(f"Note: {data['Remarks']}")

            for line in lines:
                self.set_x(x)
                self.cell(self.card_width, 5, line, ln=1)

        self.ln(row_height)

# Streamlit UI
st.set_page_config(page_title="Giordano Grid Catalogue Generator")
st.title("🛍️ Giordano Grid-style Catalogue Generator")

excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])
image_zip = st.file_uploader("Upload Product Images (ZIP)", type=["zip"])
logo_file = st.file_uploader("Upload Brand Logo (PNG)", type=["png"])

if st.button("Generate Catalogue") and excel_file and image_zip:
    try:
        df = pd.read_excel(excel_file)
    except Exception as e:
        st.error(f"❌ Error reading Excel file: {e}")
        st.stop()

    required_cols = {"Model", "MRP", "CSP", "Discount", "Gender", "Inventory"}
    if not required_cols.issubset(df.columns):
        st.error("❌ Excel must contain: Model, MRP, CSP, Discount, Gender, Inventory")
        st.stop()

    images = load_images_from_zip(image_zip)

    if logo_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_logo:
            tmp_logo.write(logo_file.read())
            logo_path = tmp_logo.name
    else:
        logo_path = None

    pdf = GridPDF(logo_path=logo_path, items_per_row=2)
    pdf.add_page()

    product_cards = []
    for _, row in df.iterrows():
        model = str(row["Model"]).strip().lower()
        data = {
            "Model": model.upper(),
            "MRP": str(row["MRP"]),
            "CSP": str(row["CSP"]),
            "Discount": str(row["Discount"]),
            "Gender": str(row["Gender"]),
            "Inventory": str(row["Inventory"]),
            "Remarks": str(row.get("Remarks", ""))
        }
        image = images.get(model)
        if image:
            product_cards.append((data, image))
        else:
            st.warning(f"⚠️ No image found for model: {model}")

    if not product_cards:
        st.error("❌ No product cards were created.")
    else:
        for i in range(0, len(product_cards), pdf.items_per_row * 3):
            chunk = product_cards[i:i + pdf.items_per_row * 3]
            pdf.product_grid(chunk)
            if i + pdf.items_per_row * 3 < len(product_cards):
                pdf.add_page()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            pdf.output(tmp_pdf.name)
            with open(tmp_pdf.name, "rb") as f:
                st.download_button("📄 Download Catalogue PDF", f, file_name="giordano_grid_catalogue.pdf")

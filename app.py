import streamlit as st
from PIL import Image
import pandas as pd
import os
from fpdf import FPDF
import tempfile
import zipfile
from io import BytesIO

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

# Custom PDF class
class CataloguePDF(FPDF):
    def __init__(self, logo_path, cards_per_row=2):
        super().__init__()
        self.logo_path = logo_path
        self.cards_per_row = cards_per_row
        self.set_auto_page_break(auto=True, margin=10)
        self.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        self.set_font("DejaVu", "", 10)

    def header(self):
        if self.logo_path:
            self.image(self.logo_path, x=(210 - 50) / 2, y=8, w=50)
            self.ln(25)
        else:
            self.ln(10)

    def product_grid(self, products):
        page_width = self.w - 20
        card_width = page_width / self.cards_per_row - 5
        card_height = 100
        image_height = 50

        for i, item in enumerate(products):
            if i % self.cards_per_row == 0:
                self.ln(5)
                x_start = self.get_x()
                y_start = self.get_y()

            x = 10 + (i % self.cards_per_row) * (card_width + 5)
            self.set_xy(x, y_start)
            self.set_fill_color(255, 255, 255)
            self.rect(x, y_start, card_width, card_height, 'DF')

            if item["image"]:
                img = item["image"]
                img_ratio = img.width / img.height
                new_width = card_width - 10
                new_height = new_width / img_ratio

                if new_height > image_height:
                    new_height = image_height
                    new_width = new_height * img_ratio

                img_x = x + (card_width - new_width) / 2
                img_y = y_start + 5

                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmpfile:
                    img.save(tmpfile.name)
                    self.image(tmpfile.name, x=img_x, y=img_y, w=new_width, h=new_height)
                    os.unlink(tmpfile.name)

            self.set_xy(x + 2, y_start + image_height + 8)
            self.set_font("DejaVu", "", 8)
            text = (
                f"{item['data']['Model']}\n"
                f"MRP: ₹{item['data']['MRP']}\n"
                f"Offer: ₹{item['data']['CSP']} ({item['data']['Discount']} OFF)\n"
                f"Gender: {item['data']['Gender']}\n"
                f"Inventory: {item['data']['Inventory']}"
            )
            if item['data'].get("Remarks"):
                text += f"\nNote: {item['data']['Remarks']}"
            self.multi_cell(card_width - 4, 4, text, align='L')

# Streamlit UI
st.set_page_config(page_title="Giordano Catalogue Generator", layout="centered")
st.title("🛍️ Giordano WhatsApp-style Catalogue Generator")

excel_file = st.file_uploader("Upload Excel File (.xlsx)", type=["xlsx"])
image_zip = st.file_uploader("Upload Product Images (.zip)", type=["zip"])
logo_file = st.file_uploader("Upload Brand Logo (.png)", type=["png"])
cards_per_row = st.radio("Select number of products per row in PDF", [2, 3])

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

    # Save logo temporarily
    logo_path = None
    if logo_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_logo:
            tmp_logo.write(logo_file.read())
            logo_path = tmp_logo.name

    pdf = CataloguePDF(logo_path=logo_path, cards_per_row=cards_per_row)
    pdf.add_page()

    cards = []
    missing = []

    for idx, row in df.iterrows():
        model_key = str(row["Model"]).strip()
        model_key = os.path.splitext(model_key)[0]  # Remove extension
        image = images.get(model_key)

        data = {
            "Model": model_key,
            "MRP": row["MRP"],
            "CSP": row["CSP"],
            "Discount": row["Discount"],
            "Gender": row["Gender"],
            "Inventory": row["Inventory"],
            "Remarks": row.get("Remarks", "")
        }

        if image:
            cards.append({"data": data, "image": image})
        else:
            missing.append((idx + 2, model_key))  # Excel row = index + header + 1

    # Add product cards to PDF
    for i in range(0, len(cards), pdf.cards_per_row):
        pdf.product_grid(cards[i:i + pdf.cards_per_row])

    if not cards:
        st.error("❌ No product cards created. Check if images match model names in Excel.")
        st.stop()

    # Save and serve PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        pdf.output(tmp_pdf.name)
        with open(tmp_pdf.name, "rb") as f:
            st.download_button("📄 Download Catalogue PDF", f, file_name="giordano_catalogue.pdf")

    # Show any missing images
    if missing:
        st.warning("⚠️ Some models were missing images:")
        preview_df = df.iloc[[row[0] - 2 for row in missing]].copy()
        preview_df.insert(0, "Excel Row", [row[0] for row in missing])
        st.dataframe(preview_df)

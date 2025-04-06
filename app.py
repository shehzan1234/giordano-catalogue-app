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

# PDF generator class
class WhatsAppPDF(FPDF):
    def __init__(self, logo_path, columns):
        super().__init__()
        self.logo_path = logo_path
        self.columns = columns
        self.set_auto_page_break(auto=True, margin=15)
        self.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        self.set_font("DejaVu", "", 10)

    def header(self):
        if self.logo_path:
            page_width = self.w - 2 * self.l_margin
            self.image(self.logo_path, x=(self.w - 40) / 2, y=8, w=40)
            self.ln(25)

    def product_card(self, data, image, card_width, card_height):
        x_start = self.get_x()
        y_start = self.get_y()

        self.set_fill_color(255, 255, 255)
        self.rect(x_start, y_start, card_width, card_height, style='F')

        padding = 4
        inner_width = card_width - 2 * padding
        image_max_height = card_height * 0.45

        # Resize proportionally
        img_width, img_height = image.size
        ratio = min(inner_width / img_width, image_max_height / img_height)
        new_w = img_width * ratio
        new_h = img_height * ratio

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_img:
            resized_image = image.resize((int(new_w), int(new_h)), Image.LANCZOS)
            resized_image.save(tmp_img.name)
            tmp_img_path = tmp_img.name

        img_x = x_start + (card_width - new_w) / 2
        img_y = y_start + padding
        self.image(tmp_img_path, x=img_x, y=img_y, w=new_w, h=new_h)
        os.unlink(tmp_img_path)

        # Text block
        self.set_xy(x_start + padding, img_y + new_h + 2)
        self.set_font("DejaVu", "", 9)
        self.set_text_color(0, 0, 0)

        self.multi_cell(card_width - 2 * padding, 5,
            f"Model: {data['Model']}\n"
            f"MRP: ₹{data['MRP']}\n"
            f"Offer: ₹{data['CSP']} ({data['Discount']})\n"
            f"Gender: {data['Gender']}\n"
            f"Stock: {data['Inventory']}\n"
            + (f"Note: {data['Remarks']}" if data['Remarks'] else ""),
            align="L"
        )

        self.set_xy(x_start + card_width, y_start)

    def add_product_grid(self, grouped_products):
        card_width = (self.w - 2 * self.l_margin - (self.columns - 1) * 5) / self.columns
        card_height = 80

        for group in grouped_products:
            x_start = self.l_margin
            y_start = self.get_y()
            max_y = y_start
            for data, image in group:
                self.set_xy(x_start, y_start)
                self.product_card(data, image, card_width, card_height)
                x_start += card_width + 5
                max_y = max(max_y, self.get_y())
            self.set_y(max_y + card_height + 5)

# Streamlit UI
st.set_page_config(page_title="Giordano Catalogue Generator")
st.title("🛍️ Giordano WhatsApp-style Catalogue Generator")

excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])
image_zip = st.file_uploader("Upload Product Images (ZIP)", type=["zip"])
logo_file = st.file_uploader("Upload Brand Logo (PNG)", type=["png"])
columns = st.selectbox("Select number of products per row", [2, 3], index=0)

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

    pdf = WhatsAppPDF(logo_path=logo_path, columns=columns)
    pdf.add_page()

    grouped = []
    row_errors = []
    for idx, row in df.iterrows():
        model = os.path.splitext(str(row["Model"]).strip())[0]
        data = {
            "Model": model,
            "MRP": str(row["MRP"]),
            "CSP": str(row["CSP"]),
            "Discount": str(row["Discount"]) + "%",
            "Gender": str(row["Gender"]),
            "Inventory": str(row["Inventory"]),
            "Remarks": str(row.get("Remarks", ""))
        }
        image = images.get(model)
        if image:
            if len(grouped) == 0 or len(grouped[-1]) >= columns:
                grouped.append([])
            grouped[-1].append((data, image))
        else:
            row_errors.append((idx + 2, model))

    pdf.add_product_grid(grouped)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        pdf.output(tmp_pdf.name)
        with open(tmp_pdf.name, "rb") as f:
            st.download_button("📄 Download Catalogue PDF", f, file_name="giordano_catalogue.pdf")

    if row_errors:
        st.subheader("⚠️ Missing Images")
        for row_num, model in row_errors:
            st.write(f"Row {row_num}: No image found for model '{model}'")

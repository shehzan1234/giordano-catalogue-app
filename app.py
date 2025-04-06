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
                    model_name = os.path.splitext(os.path.basename(filename))[0]
                    image_dict[model_name.strip()] = img
    return image_dict

# PDF Class with Grid Layout
class WhatsAppPDF(FPDF):
    def __init__(self, logo_path):
        super().__init__()
        self.logo_path = logo_path
        self.set_auto_page_break(auto=True, margin=15)

        # Unicode font
        self.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        self.set_font("DejaVu", "", 12)

        self.card_width = 90
        self.card_height = 90
        self.margin_x = 10
        self.margin_y = 10

    def header(self):
        if self.logo_path:
            # Keep logo aspect ratio
            with Image.open(self.logo_path) as img:
                w, h = img.size
                max_w = 50
                aspect_ratio = h / w
                display_w = max_w
                display_h = max_w * aspect_ratio
                self.image(self.logo_path, x=10, y=8, w=display_w, h=display_h)
            self.ln(25)
        else:
            self.ln(10)

    def product_grid(self, data_list, image_dict):
        self.set_fill_color(220, 248, 198)
        x_start = self.l_margin
        y = self.get_y()
        col = 0

        for data in data_list:
            model = data["Model"]
            image = image_dict.get(model)

            x = x_start + col * (self.card_width + self.margin_x)

            # Check if new row needed
            if col >= 2:
                col = 0
                x = x_start
                y += self.card_height + self.margin_y

            self.set_xy(x, y)

            # Draw image preserving aspect ratio
            max_w = self.card_width
            max_h = 50
            if image:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_img:
                    image.save(tmp_img.name, format="JPEG")
                    iw, ih = image.size
                    ratio = min(max_w / iw, max_h / ih)
                    display_w = iw * ratio
                    display_h = ih * ratio
                    img_x = x + (self.card_width - display_w) / 2
                    self.image(tmp_img.name, img_x, y, w=display_w, h=display_h)
                    os.unlink(tmp_img.name)

            # Draw text box
            self.set_xy(x, y + max_h + 2)
            lines = [
                f"{data['Model']}",
                f"MRP: ₹{data['MRP']}",
                f"Offer Price: ₹{data['CSP']} ({data['Discount']} OFF)",
                f"Gender: {data['Gender']}",
                f"Inventory: {data['Inventory']}"
            ]
            if data.get("Remarks") and data["Remarks"].lower() != "nan":
                lines.append(f"Note: {data['Remarks']}")
            full_text = "\n".join(lines)
            self.multi_cell(self.card_width, 5, full_text, border=1, fill=True)

            col += 1

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

    if logo_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_logo:
            tmp_logo.write(logo_file.read())
            logo_path = tmp_logo.name
    else:
        logo_path = None

    pdf = WhatsAppPDF(logo_path=logo_path)
    pdf.add_page()

    data_list = []
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
        data_list.append(data)

    if not any(images.get(d["Model"]) for d in data_list):
        st.error("❌ No matching images found for the models.")
        st.stop()

    pdf.product_grid(data_list, images)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        pdf.output(tmp_pdf.name)
        with open(tmp_pdf.name, "rb") as f:
            st.download_button("📄 Download Catalogue PDF", f, file_name="giordano_catalogue.pdf")

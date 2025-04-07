import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
from PIL import Image
import tempfile
import zipfile

# Set page config
st.set_page_config(page_title="Giordano Catalogue Generator", layout="wide")

# Title
st.title("Giordano Catalogue PDF Generator")

# Uploads
logo_file = st.file_uploader("Upload Logo", type=["png", "jpg"])
excel_file = st.file_uploader("Upload Product Excel File", type=["xlsx"])
zip_file = st.file_uploader("Upload Product Images (ZIP)", type=["zip"])
font_file = st.file_uploader("Upload Font (TTF for Unicode like ₹, %)", type=["ttf"])

cards_per_row = st.selectbox("Select number of product cards per row", [2, 3])

if st.button("Generate Catalogue"):
    if not all([logo_file, excel_file, zip_file, font_file]):
        st.error("Please upload all required files.")
    else:
        with tempfile.TemporaryDirectory() as tempdir:
            # Save and extract images
            zip_path = os.path.join(tempdir, "images.zip")
            with open(zip_path, "wb") as f:
                f.write(zip_file.read())
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tempdir)

            image_folder = tempdir

            # Save font
            font_path = os.path.join(tempdir, "custom_font.ttf")
            with open(font_path, "wb") as f:
                f.write(font_file.read())

            # Read Excel
            df = pd.read_excel(excel_file)
            df.fillna('', inplace=True)

            # Prepare PDF
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=10)
            pdf.add_page()
            pdf.add_font("Custom", "", font_path, uni=True)
            pdf.set_font("Custom", size=12)

            # Add logo
            logo_path = os.path.join(tempdir, "logo.png")
            with open(logo_path, "wb") as f:
                f.write(logo_file.read())
            logo = Image.open(logo_path)
            logo_width_mm = 60
            aspect_ratio = logo.height / logo.width
            logo_height_mm = logo_width_mm * aspect_ratio
            page_width = pdf.w
            x_pos = (page_width - logo_width_mm) / 2
            pdf.image(logo_path, x=x_pos, y=10, w=logo_width_mm)
            pdf.ln(logo_height_mm + 10)

            # Card layout
            card_width = (pdf.w - 20 - (cards_per_row - 1) * 10) / cards_per_row
            card_height = 80

            x_start = 10
            y_start = pdf.get_y()
            x = x_start
            y = y_start

            mismatch_rows = []

            for idx, row in df.iterrows():
                model_name = str(row["Model"]).strip()
                image_name = model_name + ".jpg"
                image_path = os.path.join(image_folder, image_name)

                if not os.path.exists(image_path):
                    mismatch_rows.append((idx + 2, model_name))
                    continue

                if x + card_width > pdf.w - 10:
                    x = x_start
                    y += card_height + 10
                    if y + card_height > pdf.h - 20:
                        pdf.add_page()
                        y = 20
                        x = x_start

                pdf.set_xy(x, y)
                pdf.set_fill_color(255, 255, 255)
                pdf.rect(x, y, card_width, card_height, 'F')

                try:
                    img = Image.open(image_path)
                    img_w, img_h = img.size
                    max_img_w = card_width - 10
                    max_img_h = 40
                    ratio = min(max_img_w / img_w, max_img_h / img_h)
                    new_w = img_w * ratio
                    new_h = img_h * ratio
                    img_x = x + (card_width - new_w) / 2
                    img_y = y + 5
                    pdf.image(image_path, img_x, img_y, w=new_w, h=new_h)
                except Exception:
                    mismatch_rows.append((idx + 2, model_name))
                    continue

                text_y = y + 50
                pdf.set_xy(x + 5, text_y)
                pdf.set_font("Custom", size=10)

                pdf.cell(card_width - 10, 5, f"Model: {model_name}", ln=1)

                for col in df.columns:
                    if col == "Model":
                        continue
                    val = str(row[col])
                    if "discount" in col.lower() and "%" not in val:
                        val += "%"
                    line = f"{col}: {val}"
                    pdf.set_x(x + 5)
                    pdf.cell(card_width - 10, 5, txt=line, ln=1)

                x += card_width + 10

            output_path = os.path.join(tempdir, "giordano_catalogue.pdf")
            pdf.output(output_path)

            with open(output_path, "rb") as f:
                st.download_button("Download Catalogue PDF", data=f, file_name="giordano_catalogue.pdf")

            if mismatch_rows:
                st.warning("Some image(s) were missing for the following Excel rows:")
                for row_num, model in mismatch_rows:
                    st.text(f"Row {row_num}: Model '{model}'")

import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path
from fpdf import FPDF
import zipfile
import shutil

# Setup directories
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("output")
IMAGE_DIR = UPLOAD_DIR / "images"
CARD_DIR = OUTPUT_DIR / "cards"
for d in [UPLOAD_DIR, OUTPUT_DIR, IMAGE_DIR, CARD_DIR]:
    d.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="Giordano Catalogue Generator", layout="wide")
st.title("🛍️ Giordano WhatsApp-Style Catalogue Generator")

logo_file = st.file_uploader("Upload Brand Logo", type=["png", "jpg"])
excel_file = st.file_uploader("Upload Excel file", type=["xlsx"])
zip_file = st.file_uploader("Upload ZIP of Product Images", type="zip")
cards_per_row = st.selectbox("Cards per row", [2, 3])

if st.button("Generate Catalogue") and excel_file and zip_file:
    with st.spinner("Processing..."):
        # Clear previous images/cards
       import shutil

# Safely delete files and folders
for f in IMAGE_DIR.iterdir():
    if f.is_file():
        f.unlink()
    elif f.is_dir():
        shutil.rmtree(f)

for f in CARD_DIR.iterdir():
    if f.is_file():
        f.unlink()
    elif f.is_dir():
        shutil.rmtree(f)

        # Extract ZIP
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(IMAGE_DIR)

        # Show all extracted image filenames
        extracted_files = list(IMAGE_DIR.glob("*"))
        st.write("🖼️ Extracted image files:")
        for f in extracted_files:
            st.write("-", f.name)

        # Read Excel file and detect header row
        raw_df = pd.read_excel(excel_file, header=None)
        header_row_index = None
        for i, row in raw_df.iterrows():
            if row.astype(str).str.contains("Model", case=False).any():
                header_row_index = i
                break
        if header_row_index is None:
            st.error("Could not find 'Model' column in Excel.")
            st.stop()
        df = pd.read_excel(excel_file, header=header_row_index)
        df.dropna(how='all', inplace=True)
        st.write("✅ Product Data Preview:", df.head())

        # Load logo
        logo = Image.open(logo_file).convert("RGBA") if logo_file else None

        # Font setup
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()

        card_paths = []

        for _, row in df.iterrows():
            model = str(row.get("Model", "")).strip()
            if not model or model.lower() == "nan":
                continue

            # Look for matching image file with any extension
            image_path = None
            for ext in [".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"]:
                test_path = IMAGE_DIR / f"{model}{ext}"
                if test_path.exists():
                    image_path = test_path
                    break

            if not image_path or not image_path.exists():
                st.warning(f"⚠️ Image not found for model: {model}")
                continue

            # Create card image
            base = Image.open(image_path).convert("RGB").resize((500, 500))
            draw = ImageDraw.Draw(base)
            draw.rectangle([(0, 420), (500, 500)], fill="white")
            draw.text((10, 430), f"Model: {model}", fill="black", font=font)

            try:
                mrp = int(float(row.get("MRP", 0)))
                csp = int(float(row.get("CSP", 0)))
                draw.text((10, 455), f"MRP: ₹{mrp}  Offer: ₹{csp}", fill="black", font=font)
            except:
                draw.text((10, 455), "MRP: ₹-  Offer: ₹-", fill="black", font=font)

            draw.text((10, 480), f"Stock: {row.get('Inventory', '')} {row.get('Remarks', '')}", fill="black", font=font)

            out_path = CARD_DIR / f"{model}.jpg"
            base.save(out_path)
            card_paths.append(out_path)

        if not card_paths:
            st.error("❌ No product cards were created. Check image names in Excel and ZIP.")
            st.stop()

        # Create PDF
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        cards_per_page = cards_per_row * 2
        logo_path = None

        if logo:
            logo_path = OUTPUT_DIR / "temp_logo.png"
            logo.save(logo_path)

        for i in range(0, len(card_paths), cards_per_page):
            pdf.add_page()
            if i == 0 and logo_path:
                pdf.image(str(logo_path), x=75, y=5, w=60)
            chunk = card_paths[i:i+cards_per_page]
            x_offsets = {2: [10, 110], 3: [10, 75, 140]}[cards_per_row]
            y_positions = [30, 155]
            for idx2, card in enumerate(chunk):
                col = idx2 % cards_per_row
                row = idx2 // cards_per_row
                if row < 2:
                    pdf.image(str(card), x=x_offsets[col], y=y_positions[row], w=65)

        final_pdf_path = OUTPUT_DIR / "Giordano_Catalogue.pdf"
        pdf.output(str(final_pdf_path))
        st.success("🎉 Catalogue created successfully!")
        st.download_button("📄 Download PDF", data=final_pdf_path.read_bytes(), file_name="Giordano_Catalogue.pdf")

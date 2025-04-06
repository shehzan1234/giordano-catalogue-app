import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from fpdf import FPDF
import zipfile
import shutil
import os

# Setup directories
UPLOAD_DIR = Path("uploads")
IMAGE_DIR = UPLOAD_DIR / "images"
OUTPUT_DIR = Path("output")
CARD_DIR = OUTPUT_DIR / "cards"

for folder in [UPLOAD_DIR, IMAGE_DIR, OUTPUT_DIR, CARD_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# Clean previous data
for folder in [IMAGE_DIR, CARD_DIR]:
    for f in folder.glob("*"):
        if f.is_file():
            f.unlink()
        elif f.is_dir():
            shutil.rmtree(f)

st.set_page_config(page_title="Giordano Catalogue Generator", layout="wide")
st.title("🛍️ Giordano WhatsApp-Style Catalogue Generator")

# Uploads
logo_file = st.file_uploader("Upload Brand Logo", type=["png", "jpg"])
excel_file = st.file_uploader("Upload Excel/CSV file with product data", type=["xlsx", "csv"])
images_zip = st.file_uploader("Upload ZIP of Product Images (named by Model No.)", type="zip")
cards_per_row = st.selectbox("Cards per row", [2, 3])

if st.button("Generate Catalogue") and excel_file and images_zip:

    with st.spinner("Processing..."):

        # ✅ Extract ZIP
        try:
            with zipfile.ZipFile(images_zip, 'r') as zip_ref:
                zip_ref.extractall(IMAGE_DIR)
            st.success("✅ Images extracted successfully.")
        except Exception as e:
            st.error(f"Failed to extract ZIP: {e}")
            st.stop()

        # ✅ Load Excel
        if excel_file.name.endswith(".csv"):
            df = pd.read_csv(excel_file)
        else:
            raw_df = pd.read_excel(excel_file, header=None)
            header_row = None
            for i, row in raw_df.iterrows():
                if row.astype(str).str.contains("Model", case=False).any():
                    header_row = i
                    break
            if header_row is not None:
                df = pd.read_excel(excel_file, header=header_row)
            else:
                st.error("❌ Could not detect header row. Ensure a 'Model' column exists.")
                st.stop()

        df.dropna(how="all", inplace=True)
        st.write("📊 Preview of product data:", df.head())

        # ✅ Load Logo
        logo = Image.open(logo_file).convert("RGBA") if logo_file else None

        # ✅ Font
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()

        card_paths = []

        # ✅ Card creation
        st.write("🖼️ Matching products and images...")
        for idx, row in df.iterrows():
            model = str(row.get("Model", "")).strip()
            if not model or model.lower() == "nan":
                continue

            # Look for matching image
            found = False
            for ext in ["jpg", "jpeg", "png"]:
                matches = list(IMAGE_DIR.rglob(f"{model}.{ext}"))
                if matches:
                    image_path = matches[0]
                    found = True
                    break

            if not found:
                st.warning(f"⚠️ No image found for model: {model}")
                continue

            # Create card
            try:
                base = Image.open(image_path).convert("RGB").resize((500, 500))
                draw = ImageDraw.Draw(base)
                draw.rectangle([(0, 420), (500, 500)], fill="white")
                draw.text((10, 430), f"Model: {model}", fill="black", font=font)

                try:
                    mrp = f"₹{int(float(row['MRP']))}"
                    csp = f"₹{int(float(row['CSP']))}"
                except:
                    mrp = csp = "₹-"

                draw.text((10, 455), f"MRP: {mrp}  Offer: {csp}", fill="black", font=font)
                draw.text((10, 480), f"Stock: {row.get('Inventory', '')}  {row.get('Remarks', '')}", fill="black", font=font)

                card_file = CARD_DIR / f"{model}.jpg"
                base.save(card_file)
                card_paths.append(card_file)

            except Exception as e:
                st.error(f"Error creating card for {model}: {e}")

        if not card_paths:
            st.error("❌ No product cards were created. Check image names in Excel and ZIP.")
            st.stop()

        # ✅ PDF creation
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        cards_per_page = cards_per_row * 2
        x_positions = {2: [10, 110], 3: [10, 75, 140]}[cards_per_row]
        y_positions = [30, 155]

        for i in range(0, len(card_paths), cards_per_page):
            pdf.add_page()
            if i == 0 and logo:
                logo_path = OUTPUT_DIR / "logo_temp.png"
                logo.save(logo_path)
                pdf.image(str(logo_path), x=75, y=5, w=60)

            chunk = card_paths[i:i+cards_per_page]
            for idx2, card in enumerate(chunk):
                col = idx2 % cards_per_row
                row = idx2 // cards_per_row
                if row < 2:
                    pdf.image(str(card), x=x_positions[col], y=y_positions[row], w=65)

        pdf_path = OUTPUT_DIR / "Giordano_Catalogue.pdf"
        pdf.output(str(pdf_path))

        st.success("🎉 Catalogue created successfully!")
        st.download_button("📄 Download PDF", data=pdf_path.read_bytes(), file_name="Giordano_Catalogue.pdf")

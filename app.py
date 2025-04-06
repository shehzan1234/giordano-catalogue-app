import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path
from fpdf import FPDF
import zipfile
import tempfile

st.set_page_config(page_title="Giordano Catalogue Generator", layout="wide")
st.title("🛍️ Giordano WhatsApp-Style Catalogue Generator")

# Select layout
cards_per_row = st.selectbox("Cards per row", [2, 3])

# Uploads
logo_file = st.file_uploader("Upload Brand Logo", type=["png", "jpg"])
excel_file = st.file_uploader("Upload Excel/CSV file with product data", type=["xlsx", "csv"])
images_zip = st.file_uploader("Upload ZIP of Product Images (named by Model No.)", type="zip")

if st.button("Generate Catalogue") and excel_file and images_zip:
    with st.spinner("Processing..."):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            image_dir = tmp_path / "images"
            image_dir.mkdir(parents=True, exist_ok=True)

            # Save uploaded logo
            logo = None
            if logo_file is not None:
                logo_path = tmp_path / "logo.png"
                with open(logo_path, "wb") as f:
                    f.write(logo_file.getbuffer())
                logo = Image.open(logo_path).convert("RGBA")

            # Save and extract ZIP images
            zip_path = tmp_path / "images.zip"
            with open(zip_path, "wb") as f:
                f.write(images_zip.getbuffer())

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(image_dir)

            # Read product data
            if excel_file.name.endswith(".csv"):
                df = pd.read_csv(excel_file)
            else:
                raw_df = pd.read_excel(excel_file, header=None)
                header_row_index = None
                for i, row in raw_df.iterrows():
                    if row.astype(str).str.contains("Model", case=False).any():
                        header_row_index = i
                        break
                if header_row_index is not None:
                    df = pd.read_excel(excel_file, header=header_row_index)
                else:
                    st.error("❌ Could not find header row with 'Model'.")
                    st.stop()

            df.dropna(how='all', inplace=True)
            st.write("✅ Preview of uploaded product data:", df.head())

            # Prepare output
            card_dir = tmp_path / "cards"
            card_dir.mkdir(parents=True, exist_ok=True)
            card_paths = []

            # Font
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except:
                font = ImageFont.load_default()

            # Generate product cards
            for idx, row in df.iterrows():
                model = str(row.get("Model", "")).strip()
                if not model or model.lower() == 'nan':
                    continue

                image_file = image_dir / f"{model}.jpg"
                if not image_file.exists():
                    image_file = image_dir / f"{model}.png"
                if not image_file.exists():
                    st.warning(f"⚠️ Image not found for model: {model}")
                    continue

                base = Image.open(image_file).convert("RGB").resize((500, 500))
                draw = ImageDraw.Draw(base)
                draw.rectangle([(0, 420), (500, 500)], fill="white")
                draw.text((10, 430), f"Model: {model}", fill="black", font=font)
                try:
                    draw.text((10, 455), f"MRP: ₹{int(float(row['MRP']))}  Offer: ₹{int(float(row['CSP']))}", fill="black", font=font)
                except:
                    draw.text((10, 455), "MRP: ₹-  Offer: ₹-", fill="black", font=font)
                draw.text((10, 480), f"Stock: {row.get('Inventory', '')}  {row.get('Remarks', '')}", fill="black", font=font)

                out_path = card_dir / f"{model}.jpg"
                base.save(out_path)
                card_paths.append(out_path)

            # Create PDF
            pdf = FPDF(orientation='P', unit='mm', format='A4')
            cards_per_page = cards_per_row * 2
            x_offsets = {2: [10, 110], 3: [10, 75, 140]}[cards_per_row]
            y_positions = [30, 155]

            for i in range(0, len(card_paths), cards_per_page):
                pdf.add_page()
                if i == 0 and logo:
                    temp_logo_path = tmp_path / "temp_logo.png"
                    logo.save(temp_logo_path)
                    pdf.image(str(temp_logo_path), x=75, y=5, w=60)

                for j, card in enumerate(card_paths[i:i+cards_per_page]):
                    col = j % cards_per_row
                    row = j // cards_per_row
                    if row < 2:
                        pdf.image(str(card), x=x_offsets[col], y=y_positions[row], w=65)

            pdf_bytes = pdf.output(dest='S').encode('latin1')
            st.success("🎉 Catalogue created successfully!")
            st.download_button("📄 Download Catalogue PDF", data=pdf_bytes, file_name="Giordano_Catalogue.pdf", mime="application/pdf")

import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path
from zipfile import ZipFile

# App title
st.set_page_config(page_title="Giordano Catalogue Generator", layout="wide")
st.title("🛍️ Giordano WhatsApp Catalogue Generator")

# Upload section
st.sidebar.header("Upload Files")
product_file = st.sidebar.file_uploader("Upload Excel File", type=["xlsx"])
image_zip_file = st.sidebar.file_uploader("Upload Product Images ZIP", type=["zip"])
logo_file = st.sidebar.file_uploader("Upload Brand Logo (PNG)", type=["png"])

# Output folder
output_dir = Path("output")
card_dir = output_dir / "cards"
output_dir.mkdir(exist_ok=True)
card_dir.mkdir(exist_ok=True)

# Clear existing cards
for f in card_dir.glob("*.jpg"):
    f.unlink()

# Font setup
try:
    font = ImageFont.truetype("arial.ttf", 20)
except:
    font = ImageFont.load_default()

if product_file and image_zip_file:
    # Read Excel
    df = pd.read_excel(product_file)

    # Extract images
    image_dir = output_dir / "images"
    image_dir.mkdir(exist_ok=True)

    with ZipFile(image_zip_file, 'r') as zip_ref:
        zip_ref.extractall(image_dir)

    # Load logo
    logo = None
    if logo_file:
        logo = Image.open(logo_file).convert("RGBA").resize((80, 80))

    # Generate product cards
    for idx, row in df.iterrows():
        model = str(row.get("Model", "")).strip()
        if not model or model.lower() == 'nan':
            continue

        # Match image file regardless of extension or case
        image_file = None
        model_lower = model.lower()
        for file in image_dir.iterdir():
            if file.stem.lower() == model_lower and file.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                image_file = file
                break

        if not image_file:
            st.warning(f"⚠️ Image not found for model: {model}")
            continue

        base = Image.open(image_file).convert("RGB").resize((500, 500))
        draw = ImageDraw.Draw(base)
        draw.rectangle([(0, 420), (500, 500)], fill="white")
        draw.text((10, 430), f"Model: {model}", fill="black", font=font)

        try:
            draw.text((10, 455), f"MRP: ₹{int(float(row['MRP']))}   Offer: ₹{int(float(row['CSP']))}", fill="black", font=font)
        except:
            draw.text((10, 455), "MRP: ₹-   Offer: ₹-", fill="black", font=font)

        draw.text((10, 480), f"Stock: {row.get('Inventory', '')}   {row.get('Remarks', '')}", fill="black", font=font)

        if logo:
            base.paste(logo, (410, 10), logo)

        out_path = card_dir / f"{model}.jpg"
        base.save(out_path)

    # Display cards
    st.subheader("Generated Catalogue")
    images = list(card_dir.glob("*.jpg"))
    for i in range(0, len(images), 3):
        cols = st.columns(3)
        for j, img_path in enumerate(images[i:i+3]):
            with cols[j]:
                st.image(str(img_path), use_column_width=True)

    # Download ZIP
    zip_path = output_dir / "giordano_catalogue.zip"
    with ZipFile(zip_path, "w") as zipf:
        for img in card_dir.glob("*.jpg"):
            zipf.write(img, arcname=img.name)

    with open(zip_path, "rb") as f:
        st.download_button("📦 Download Catalogue ZIP", f, file_name="giordano_catalogue.zip")
else:
    st.info("👈 Please upload the Excel and ZIP files to generate the catalogue.")

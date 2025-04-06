import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import zipfile
import os
from pathlib import Path
from io import BytesIO

# Constants
UPLOAD_DIR = Path("uploaded_data")
UPLOAD_DIR.mkdir(exist_ok=True)
image_dir = UPLOAD_DIR / "images"
image_dir.mkdir(parents=True, exist_ok=True)

# UI
st.title("📦 Giordano WhatsApp Catalogue Generator")

excel_file = st.file_uploader("Upload Excel file", type=["xlsx"])
images_zip = st.file_uploader("Upload Product Images ZIP", type=["zip"])

if excel_file and images_zip:
    # Save and extract images
    with zipfile.ZipFile(images_zip, "r") as zip_ref:
        zip_ref.extractall(image_dir)

    df = pd.read_excel(excel_file)
    card_dir = UPLOAD_DIR / "cards"
    card_dir.mkdir(exist_ok=True)

    image_paths = []
    font = ImageFont.load_default()

    for idx, row in df.iterrows():
        model = str(row.get("Model", "")).strip()
        if not model or model.lower() == "nan":
            continue

        image_file_jpg = image_dir / f"{model}.jpg"
        image_file_png = image_dir / f"{model}.png"
        image_file = None

        if image_file_jpg.exists():
            image_file = image_file_jpg
        elif image_file_png.exists():
            image_file = image_file_png
        else:
            st.warning(f"⚠️ Image not found for model: {model}")
            continue

        base = Image.open(image_file).convert("RGB").resize((500, 500))
        draw = ImageDraw.Draw(base)

        # Background rectangle
        draw.rectangle([(0, 420), (500, 500)], fill="white")

        # Text info
        draw.text((10, 430), f"Model: {model}", fill="black", font=font)
        try:
            mrp = float(row.get("MRP", 0))
            csp = float(row.get("CSP", 0))
            draw.text((10, 455), f"MRP: ₹{int(mrp)}   Offer: ₹{int(csp)}", fill="black", font=font)
        except:
            draw.text((10, 455), "MRP: ₹-   Offer: ₹-", fill="black", font=font)

        inventory = str(row.get("Inventory", ""))
        remarks = str(row.get("Remarks", ""))
        draw.text((10, 480), f"Stock: {inventory}   {remarks}", fill="black", font=font)

        card_path = card_dir / f"{model}.jpg"
        base.save(card_path)
        image_paths.append(card_path)

    # Generate PDF
    if image_paths:
        pdf_bytes = BytesIO()
        images = [Image.open(path).convert("RGB") for path in image_paths]
        images[0].save(pdf_bytes, format="PDF", save_all=True, append_images=images[1:])
        pdf_bytes.seek(0)

        st.success("✅ Catalogue generated!")

        st.download_button(
            label="📥 Download WhatsApp Catalogue (PDF)",
            data=pdf_bytes,
            file_name="giordano_catalogue.pdf",
            mime="application/pdf"
        )
    else:
        st.error("❌ No product cards were created. Check image names in Excel and ZIP.")


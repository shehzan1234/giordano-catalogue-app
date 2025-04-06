import streamlit as st
import pandas as pd
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# Constants
UPLOAD_DIR = Path("uploaded_files")
UPLOAD_DIR.mkdir(exist_ok=True)
image_dir = UPLOAD_DIR / "images"
image_dir.mkdir(exist_ok=True)
card_dir = UPLOAD_DIR / "cards"
card_dir.mkdir(exist_ok=True)

# Font
try:
    font = ImageFont.truetype("arial.ttf", 20)
except:
    font = ImageFont.load_default()

# App UI
st.set_page_config(page_title="Giordano Catalogue Generator", layout="centered")
st.title("🛍️ Giordano Product Catalogue Generator")

# Uploads
excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])
images_zip = st.file_uploader("Upload Product Images ZIP", type=["zip"])
logo_file = st.file_uploader("Upload Logo (optional)", type=["png", "jpg", "jpeg"])

# Process
if st.button("Generate Catalogue"):
    if not excel_file or not images_zip:
        st.error("Please upload both Excel file and ZIP of images.")
    else:
        # Save Excel
        excel_path = UPLOAD_DIR / "data.xlsx"
        with open(excel_path, "wb") as f:
            f.write(excel_file.read())

        # Extract Images
        with zipfile.ZipFile(images_zip, 'r') as zip_ref:
            zip_ref.extractall(image_dir)

        # Read Excel
        df = pd.read_excel(excel_path)

        # Optional logo
        logo = None
        if logo_file:
            logo = Image.open(logo_file).convert("RGBA").resize((100, 100))

        product_cards = []

        for idx, row in df.iterrows():
            model = str(row.get("Model", "")).strip()
            if not model or model.lower() == 'nan':
                continue

            # Try JPG and PNG
            image_file_jpg = image_dir / f"{model}.jpg"
            image_file_png = image_dir / f"{model}.png"
            image_file = image_file_jpg if image_file_jpg.exists() else image_file_png if image_file_png.exists() else None

            if not image_file:
                st.warning(f"⚠️ Image not found for model: {model}")
                continue

            # Create card
            try:
                base = Image.open(image_file).convert("RGB").resize((500, 500))
                draw = ImageDraw.Draw(base)
                draw.rectangle([(0, 420), (500, 500)], fill="white")

                draw.text((10, 430), f"Model: {model}", fill="black", font=font)

                try:
                    mrp = int(float(row.get("MRP", 0)))
                    offer = int(float(row.get("CSP", 0)))
                    draw.text((10, 455), f"MRP: ₹{mrp}    Offer: ₹{offer}", fill="black", font=font)
                except:
                    draw.text((10, 455), "MRP: ₹-    Offer: ₹-", fill="black", font=font)

                stock = str(row.get("Inventory", "")).strip()
                remarks = str(row.get("Remarks", "")).strip()
                draw.text((10, 480), f"Stock: {stock}  {remarks}", fill="black", font=font)

                # Add logo if uploaded
                if logo:
                    base.paste(logo, (390, 0), logo)

                # Save card
                card_path = card_dir / f"{model}.jpg"
                base.save(card_path)
                product_cards.append(card_path)
            except Exception as e:
                st.error(f"Error generating card for {model}: {e}")

        if not product_cards:
            st.error("❌ No product cards were created. Check image names in Excel and ZIP.")
        else:
            # Create PDF
            pdf_path = UPLOAD_DIR / "Giordano_Catalogue.pdf"
            images = [Image.open(p).convert("RGB") for p in product_cards]
            images[0].save(pdf_path, save_all=True, append_images=images[1:])

            with open(pdf_path, "rb") as f:
                st.download_button("📥 Download PDF Catalogue", f, file_name="Giordano_Catalogue.pdf")

            st.success(f"✅ Created {len(product_cards)} product cards and compiled them into a PDF.")

import streamlit as st
from fpdf import FPDF
import pandas as pd
import zipfile
import os
from PIL import Image
import io
import tempfile
import base64

# Streamlit app UI
st.set_page_config(page_title="Giordano Catalogue Generator", layout="centered")
st.title("🕒 Giordano Catalogue Generator")

logo_file = st.file_uploader("Upload Logo (PNG)", type=["png"])
excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])
zip_file = st.file_uploader("Upload Product Images (ZIP)", type=["zip"])
cards_per_row = st.radio("Select number of product cards per row:", [2, 3])

# Load DejaVuSans font (required for ₹ and % symbols)
FONT_PATH = "DejaVuSans.ttf"
if not os.path.exists(FONT_PATH):
    st.error("Missing DejaVuSans.ttf font file in app directory.")
    st.stop()

# Helper: Resize image while maintaining aspect ratio
def resize_image(image, max_width, max_height):
    img = image.copy()
    img.thumbnail((max_width, max_height))
    return img

# Helper: Add a product card to PDF
def add_product_card(pdf, x, y, w, h, data, image, font_path):
    padding = 4
    img_height = h * 0.55
    text_start_y = y + img_height + padding
    corner_radius = 3

    # Card background
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(x, y, w, h, 'F')

    # Draw soft shadow
    pdf.set_draw_color(230, 230, 230)
    pdf.rect(x+1, y+1, w, h, style='D')

    # Draw product image
    if image:
        img_buf = io.BytesIO()
        image.save(img_buf, format='PNG')
        img_buf.seek(0)
        img_w, img_h = image.size
        ratio = min(w - 2*padding, img_height) / max(img_w, img_h)
        draw_w = img_w * ratio
        draw_h = img_h * ratio
        img_x = x + (w - draw_w) / 2
        img_y = y + padding
        pdf.image(img_buf, x=img_x, y=img_y, w=draw_w, h=draw_h)

    # Add text content
    pdf.set_xy(x + padding, text_start_y)
    pdf.set_font("DejaVu", '', 9)

    def bold(label, value):
        pdf.set_font("DejaVu", '', 8)
        pdf.multi_cell(w - 2 * padding, 4, f"{label}:", 0)
        pdf.set_font("DejaVu", 'B', 9)
        pdf.multi_cell(w - 2 * padding, 5, str(value), 0)

    bold("Model", data["Model"])
    bold("Price", f"₹{data['Price']}")
    bold("Discount", f"{data['Discount']}%")
    bold("Offer Price", f"₹{data['Offer Price']}")

# Generate PDF from Excel and Images
def generate_pdf(excel_df, image_dict, logo_img, cards_per_row, font_path):
    pdf = FPDF(unit="mm", format="A4")
    pdf.add_page()
    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.add_font("DejaVu", "B", font_path, uni=True)

    page_w = 210
    page_h = 297
    margin = 10
    card_spacing = 6
    usable_w = page_w - 2 * margin - (cards_per_row - 1) * card_spacing
    card_w = usable_w / cards_per_row
    card_h = 80
    start_y = 40

    # Add centered logo
    if logo_img:
        img_buf = io.BytesIO()
        logo_img.save(img_buf, format='PNG')
        img_buf.seek(0)
        logo_width = 50
        logo_aspect = logo_img.height / logo_img.width
        logo_height = logo_width * logo_aspect
        logo_x = (page_w - logo_width) / 2
        pdf.image(img_buf, x=logo_x, y=10, w=logo_width, h=logo_height)

    col = 0
    row = 0
    y = start_y
    mismatch_rows = []

    for idx, row_data in excel_df.iterrows():
        model_key = str(row_data["Model"]).strip()
        image_name = model_key + ".jpg"
        image = image_dict.get(image_name)

        if not image:
            mismatch_rows.append((idx + 2, model_key))  # +2 for header offset
            continue

        x = margin + col * (card_w + card_spacing)
        add_product_card(pdf, x, y, card_w, card_h, row_data, image, font_path)

        col += 1
        if col >= cards_per_row:
            col = 0
            y += card_h + card_spacing
            if y + card_h > page_h - margin:
                pdf.add_page()
                y = start_y

    return pdf.output(dest='S').encode('latin1'), mismatch_rows

# On form submit
if st.button("Generate Catalogue"):
    if not all([logo_file, excel_file, zip_file]):
        st.error("Please upload all files to proceed.")
    else:
        # Load Excel
        try:
            df = pd.read_excel(excel_file)
            df["Model"] = df["Model"].astype(str).str.strip().str.replace(".jpg", "", case=False)
        except Exception as e:
            st.error(f"Error reading Excel: {e}")
            st.stop()

        # Extract images
        image_dict = {}
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)
            for root, _, files in os.walk(tmpdir):
                for file in files:
                    if file.lower().endswith((".jpg", ".jpeg", ".png")):
                        try:
                            img_path = os.path.join(root, file)
                            img = Image.open(img_path).convert("RGB")
                            image_dict[file] = img
                        except:
                            continue

        # Load logo
        logo_img = None
        try:
            logo_img = Image.open(logo_file).convert("RGBA")
        except:
            st.warning("Invalid logo image.")

        pdf_bytes, mismatches = generate_pdf(df, image_dict, logo_img, cards_per_row, FONT_PATH)

        # Download button
        st.success("✅ PDF generated successfully!")
        st.download_button("📥 Download Catalogue", pdf_bytes, file_name="giordano_catalogue.pdf", mime="application/pdf")

        # Show mismatches
        if mismatches:
            st.warning("⚠️ Some models had no matching image:")
            for row_num, model in mismatches:
                st.text(f"Row {row_num}: '{model}'")

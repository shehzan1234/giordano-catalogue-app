
import streamlit as st
from fpdf import FPDF
from PIL import Image
import pandas as pd
import os

# Constants
FONT_PATH = "DejaVuSans.ttf"
LOGO_PATH = "giordano timewear.png"
IMAGE_FOLDER = "APP IMAGES (2)"
OUTPUT_PDF = "giordano_catalogue.pdf"

# PDF class with advanced layout
class PDF(FPDF):
    def __init__(self, logo_path, cards_per_row):
        super().__init__()
        self.logo_path = logo_path
        self.cards_per_row = cards_per_row
        self.card_width = (190 - (cards_per_row - 1) * 5) / cards_per_row
        self.card_height = 90
        self.margin_top = 50
        self.card_y_start = self.margin_top
        self.set_auto_page_break(auto=True, margin=15)
        self.add_font("DejaVu", "", FONT_PATH, uni=True)
        self.set_font("DejaVu", size=10)

    def header(self):
        if self.page_no() == 1:
            self.image(self.logo_path, x=65, y=10, w=80)

    def add_product_cards(self, products):
        x_positions = [10 + i * (self.card_width + 5) for i in range(self.cards_per_row)]
        col = 0
        for idx, product in products.iterrows():
            if col == 0:
                self.ln(self.card_height + 10)
            x = x_positions[col]
            y = self.get_y()
            self.add_product_card(x, y, product)
            col += 1
            if col == self.cards_per_row:
                col = 0

    def add_product_card(self, x, y, product):
        self.set_xy(x, y)
        self.set_fill_color(255, 255, 255)
        self.rect(x, y, self.card_width, self.card_height, 'DF')
        img_path = os.path.join(IMAGE_FOLDER, product["Model"] + ".jpg")
        if os.path.exists(img_path):
            self.image(img_path, x + 5, y + 5, w=self.card_width - 10, h=40)
        self.set_xy(x + 5, y + 47)
        self.set_font("DejaVu", size=9)
        self.multi_cell(self.card_width - 10, 5, f"{product['Model']}", align='C')
        self.set_font("DejaVu", style="B", size=9)
        self.set_xy(x + 5, y + 60)
        self.cell(self.card_width - 10, 5, f"MRP: ₹{product['MRP']}", ln=1, align='L')
        self.set_font("DejaVu", style="", size=9)
        self.set_xy(x + 5, y + 65)
        self.cell(self.card_width - 10, 5, f"SP: ₹{product['SP']}", ln=1, align='L')
        self.set_text_color(255, 0, 0)
        self.set_xy(x + 5, y + 70)
        self.cell(self.card_width - 10, 5, f"Discount: {product['Discount']}%", ln=1, align='L')
        self.set_text_color(0, 0, 0)

# Streamlit app
def main():
    st.title("Giordano Catalogue Generator")
    cards_per_row = st.selectbox("Select number of cards per row", [2, 3])
    if st.button("Generate PDF"):
        df = pd.read_excel("sample_products.xlsx")
        df["Model"] = df["Model"].str.replace(".jpg", "", regex=False)
        pdf = PDF(logo_path=LOGO_PATH, cards_per_row=cards_per_row)
        pdf.add_page()
        pdf.add_product_cards(df)
        pdf.output(OUTPUT_PDF)
        st.success("PDF generated successfully!")
        with open(OUTPUT_PDF, "rb") as f:
            st.download_button("Download PDF", f, file_name=OUTPUT_PDF)

if __name__ == "__main__":
    main()

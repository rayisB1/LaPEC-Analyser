import pdfplumber

with pdfplumber.open(r"C:\Users\rayis\Desktop\STAGE LABO\DIDOUX-V1.pdf") as pdf:
    for i, page in enumerate(pdf.pages):
        print(f"\n=== PAGE {i+1} ===")
        text = page.extract_text()
        if text:
            for line in text.splitlines()[:30]:
                print(repr(line))
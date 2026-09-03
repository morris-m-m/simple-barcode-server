import io, os, tempfile
import base64
import barcode
from barcode.writer import ImageWriter

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.responses import Response
from fpdf import FPDF



current_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(current_dir, "templates")

# Initialize Jinja2 with the absolute path
templates = Jinja2Templates(directory=templates_dir)

font_path = os.path.join(current_dir, "fonts", "Arial.ttf")



class UnscaledFPDF(FPDF):
    def _putcatalog(self):
        """Overrides the catalog generation block to inject strict scaling rules."""
        super()._putcatalog()
        self._out('/ViewerPreferences <</PrintScaling /None>>')




def truncate_to_three_lines(pdf, text: str, max_width: float) -> str:
    """Calculates string width mathematically and caps input strictly at 3 lines."""
    words = text.split()
    if not words:
        return ""

    lines = []
    current_line = []

    for word in words:
        test_line = " ".join(current_line + [word]) if current_line else word
        
        if pdf.get_string_width(test_line) <= max_width:
            current_line.append(word)
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
            
            # Break early when we have populated 3 full lines
            if len(lines) == 3:
                break
    else:
        if current_line and len(lines) < 3:
            lines.append(" ".join(current_line))

    # Append ellipsis strictly to the end of the 3rd line if text overflowed
    if len(lines) >= 3:
        final_lines = [lines[0], lines[1], lines[2]]
        return "\n".join(final_lines)
        
    return "\n".join(lines)









app = FastAPI(
    title="Barcode Generator",
    description="Barcodes Generator",
)



def is_valid_gs1_check_digit(number_str: str) -> bool:
    """Strictly validates the GS1 check digit for lengths 8, 12, 13, 14."""
    if not number_str.isdigit():
        return False
        
    body = number_str[:-1]
    provided_check_digit = int(number_str[-1])
    
    total = 0
    for i, digit in enumerate(reversed(body)):
        weight = 3 if i % 2 == 0 else 1
        total += int(digit) * weight
        
    calculated_check_digit = (10 - (total % 10)) % 10
    return calculated_check_digit == provided_check_digit

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4////fwAJ+wP9KobjigAAAABJRU5ErkJggg=="
    icon_bytes = base64.b64decode(png_base64)
    return Response(content=icon_bytes, media_type="image/png")


@app.get("/", response_class=HTMLResponse)
async def read_form(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/", response_class=HTMLResponse)
async def handle_form(
    request: Request, 
    barcode_input: str = Form(...), 
    description: str = Form(...)
):
    barcode_clean = barcode_input.strip()
    
    # 1. Reject if not numbers only
    if not barcode_clean.isdigit():
        error = "Invalid input. Barcode must contain numbers only."
        return templates.TemplateResponse("index.html", {"request": request, "error": error, "description": description, "barcode_input": barcode_input})

    # 2. Reject if length is incorrect
    valid_lengths = {8, 12, 13, 14}
    if len(barcode_clean) not in valid_lengths:
        error = "Invalid length. Barcode must be exactly 8, 12, 13, or 14 digits long."
        return templates.TemplateResponse("index.html", {"request": request, "error": error, "description": description, "barcode_input": barcode_input})

    # 3. Reject if the check digit math is wrong
    if not is_valid_gs1_check_digit(barcode_clean):
        error = "Invalid barcode. The final check digit does not match the sequence."
        return templates.TemplateResponse("index.html", {"request": request, "error": error, "description": description, "barcode_input": barcode_input})

    # Determine barcode type based on length
    length = len(barcode_clean)
    if length == 8:
        bar_class = barcode.get_barcode_class('ean8')
    elif length == 12:
        bar_class = barcode.get_barcode_class('upca')
    elif length == 13:
        bar_class = barcode.get_barcode_class('ean13')
    else:
        bar_class = barcode.get_barcode_class('itf')

    # --- GENERATE BARCODE IN MEMORY ---
    # We pass an in-memory BytesIO stream to writer.save instead of a filepath

    barcode_tmp = tempfile.NamedTemporaryFile(delete=False)
    barcode_base = barcode_tmp.name
    barcode_tmp.close()
    
    options = {"write_text": True}
    barcode_file = bar_class(barcode_clean, writer=ImageWriter()).save(barcode_base, options=options)

    # Initialize your A4 canvas with zeroed margins to prevent auto-shifting
    pdf = UnscaledFPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(0, 0, 0)
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()

    # Official Avery L7160 Template Dimensions (in millimeters)
    columns = 3
    rows = 7
    label_width = 63.5
    label_height = 38.1
    margin_top = 15.1       # Top margin down to the first label row
    margin_left = 7.0       # Left margin across to the first label column
    horizontal_gap = 2.0    # Crucial 2mm physical gap between the columns
    vertical_gap = 0.0      # Label edges touch vertically row-to-row

    for row in range(rows):
        for col in range(columns):
            # Calculate coordinates factoring in the column gaps
            x = margin_left + (col * (label_width + horizontal_gap))
            y = margin_top + (row * (label_height + vertical_gap))
            
            # 1. Outer label bounding box (faint grey line to guide scissor cuts or alignment checks)
            pdf.set_draw_color(200, 200, 200)
            pdf.rect(x, y, label_width, label_height)
            
            # 2. Add description text (Centered, slightly padded from the top edge)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", style="B", size=10)
            text_bounding_width = label_width - 4
            safe_description = truncate_to_three_lines(pdf, description, text_bounding_width)
            pdf.set_xy(x + 2, y + 2.5)

            pdf.multi_cell(
                w=text_bounding_width, 
                h=4, 
                txt=safe_description, 
                border=0, 
                align="C"
            )
            
            # 3. Embed the in-memory barcode image stream

            pdf.image(
                barcode_file, 
                x=x + 4, 
                y=y + 17, 
                w=int(label_width - 4),
                h=20, 
            )



    # Output PDF layout contents directly into an in-memory byte buffer string

    pdf_output_stream = io.BytesIO(bytes(pdf.output(dest='S'), encoding='latin1'))


    for path in (barcode_base, f"{barcode_base}.png"):
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


    # Return the file stream back to the browser window tab layout immediately
    return StreamingResponse(
        pdf_output_stream, 
        media_type="application/pdf", 
        headers={
            "Content-Disposition": "inline; filename=labels.pdf",
            "X-Apple-Print-Scaling": "none",
            "PRAGMA": "no-cache"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8025)
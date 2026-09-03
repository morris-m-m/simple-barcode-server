# Barcode Server

 A small and simple FastAPI web application that generates printable barcode label sheets as PDF files.

 Enter a barcode number and item description in the web interface. The server validates the number, generates the matching barcode, and returns an A4 PDF containing 21 labels in an Avery L7160-compatible layout.

 ## Features

 - Supports EAN-8, UPC-A, EAN-13, and ITF-14 barcodes
 - Validates barcode length and check digits before generating a file
 - Adds a description to each label
 - Generates a print-ready A4 PDF in memory
 - Runs as a non-root user inside Docker

 ## Quick Start with Docker Compose

 1. Clone the repository and change into its directory.

 2. Start the service:

		```bash
		docker compose up -d --build
		```

 3. Open [http://localhost:8025](http://localhost:8025) in a browser.

 4. Enter the barcode digits and item description, then select **Generate Barcode PDF**.

 The generated PDF opens in a new browser tab. For correct label alignment, print at 100% scale and disable options such as **Fit to page** or **Shrink oversized pages**.

 Stop the service with:

 ```bash
 docker compose down
 ```

 ## Local Development

 The application requires Python 3.12 or newer.

 ```bash
 python -m venv .venv
 source .venv/bin/activate
 pip install -r requirements.txt
 uvicorn app.main:app --reload --host 0.0.0.0 --port 8025
 ```

 Then visit [http://localhost:8025](http://localhost:8025).

 ## Accepted Barcodes

 | Digits | Barcode format |
 | ---: | --- |
 | 8 | EAN-8 |
 | 12 | UPC-A |
 | 13 | EAN-13 |
 | 14 | ITF-14 |

 The input must contain digits only and must have a valid final check digit. Invalid values are rejected with an explanation in the web interface.

 ## Configuration

 The default service port is `8025`. To use another host port, change the left side of the port mapping in `docker-compose.yml`:

 ```yaml
 ports:
	 - "8080:8025"
 ```

 The application will then be available at [http://localhost:8080](http://localhost:8080).

 ## Project Structure

 ```text
 .
 ├── app/
 │   ├── main.py
 │   └── templates/
 │       └── index.html
 ├── docker-compose.yml
 ├── Dockerfile
 ├── readme.md
 ├── LICENSE
 └── requirements.txt
 ```

 ## License

 This project is licensed under the [MIT License](LICENSE).

import os
import subprocess
import tempfile
import pypdfium2

SWIFT_SCRIPT = """
import Vision
import Cocoa

let imageURL = URL(fileURLWithPath: CommandLine.arguments[1])
guard let image = NSImage(contentsOf: imageURL),
      let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    exit(1)
}

let request = VNRecognizeTextRequest { req, err in
    guard let obs = req.results as? [VNRecognizedTextObservation] else { return }
    for o in obs {
        if let top = o.topCandidates(1).first {
            print(top.string)
        }
    }
}
request.recognitionLevel = .accurate
let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
try? handler.perform([request])
"""


def run_ocr():
    swift_file = "vision_ocr.swift"
    with open(swift_file, "w") as f:
        f.write(SWIFT_SCRIPT)

    pdf = pypdfium2.PdfDocument("pdf_downloads/SIGNED-PROPERTY-RATES-2025.pdf")
    print(f"Total pages in SIGNED-PROPERTY-RATES-2025: {len(pdf)}\n")

    all_page_texts = []

    for i, page in enumerate(pdf, start=1):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
        page.render(scale=2).to_pil().save(tmp_path)

        cmd = ["swift", swift_file, tmp_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        os.remove(tmp_path)

        text = res.stdout.strip()
        all_page_texts.append(text)
        print(f"=== PAGE {i} OCR ({len(text)} characters) ===")
        lines = text.split("\n")
        for line in lines[:30]:
            print("  ", line)
        if len(lines) > 30:
            print(f"   ... [{len(lines)-30} more lines] ...")
        print()

    # Save complete OCR text
    with open("property_rates_ocr.txt", "w", encoding="utf-8") as f:
        f.write("\n\n=== PAGE BREAK ===\n\n".join(all_page_texts))
    print("Saved complete OCR output to property_rates_ocr.txt")


if __name__ == "__main__":
    run_ocr()

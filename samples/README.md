# Sample Corpus — Law & Medicine

Fabricated, synthetic documents for demoing the RAG pipeline's cross-domain
retrieval and citation grounding. Every document is fictional (fake people,
companies, statutes, drugs, and case citations) — none of this reflects real
legal or medical facts, and none should be used as actual guidance.

```
samples/
├── law/
│   ├── lease_agreement_meridian_apartments.txt
│   ├── case_brief_alvarez_v_northgate.txt
│   ├── statute_summary_data_privacy_act.txt
│   └── legal_memo_nda_breach_dispute.txt
└── med/
    ├── clinical_progress_note_hypertension.txt
    ├── medication_information_sheet_metforglide.txt
    ├── discharge_summary_appendectomy.txt
    └── clinical_trial_abstract_glideptin_study.txt
```

## Using them as-is (text ingestion)

Drop the `.txt` files straight into the app's upload flow (or `data/uploads/`)
— they're already in a format the ingestion pipeline handles natively.

Good sample queries to show off retrieval + citations:
- "What happens if the tenant wants to terminate the lease early?" (law)
- "What was the outcome of Alvarez v. Northgate and why?" (law)
- "What rights does a consumer have under the CCDPA?" (law)
- "What dose adjustment was made for the hypertension patient and why?" (med)
- "What's the boxed warning for Metforglide?" (med)
- "What were the most common adverse events in the GLIDE-7 trial?" (med)

## Converting to images (to exercise the OCR/image pipeline)

Any of these approaches works — the goal is just a rendered image containing
the text, so OCR (OpenCV + pytesseract) has something to extract:

```bash
# macOS: screenshot a Preview/TextEdit window, or use a quick HTML->PNG render
# e.g. with wkhtmltoimage / a headless browser, or simply:
textutil -convert html samples/law/lease_agreement_meridian_apartments.txt -output /tmp/lease.html
# then screenshot /tmp/lease.html in a browser, or print-to-PDF and rasterize a page
```

Or use any "txt to image" / "text to JPG" utility — visual fidelity doesn't
matter, only that the text is legible enough for OCR.

## Converting to audio (to exercise the transcription pipeline)

Use any TTS tool to read a file aloud and save it as WAV/MP3, e.g. macOS's
built-in `say`:

```bash
say -f samples/med/clinical_progress_note_hypertension.txt \
    -o samples/med/clinical_progress_note_hypertension.aiff
ffmpeg -i samples/med/clinical_progress_note_hypertension.aiff \
    samples/med/clinical_progress_note_hypertension.wav
```

Repeat per file, then ingest the resulting audio the same way as
`test-files/harvard.wav` to confirm faster-whisper transcription and
timestamped citations work end-to-end on this content.

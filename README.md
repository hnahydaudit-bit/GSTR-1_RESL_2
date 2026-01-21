# GSTR-1 Excel Processor

A Streamlit web app for processing and consolidating Excel files related to GST and revenue data. It allows users to upload files, perform consolidations, filtering, and summarization, then download the results.

## Features
- **Consolidate SD and SR Files**: Combines data from two Excel files into one, keeping headers from the first.
- **Filter GL Dump Data**: Creates separate sheets for GST Payable and Revenue in a new workbook.
- **Generate Summary**: Summarizes amounts and differences across files for GST types.
- **Web-Based UI**: No local installation needed—runs in a browser via Streamlit.

## Requirements
- Python 3.8 or higher
- Dependencies: Install via `pip install -r requirements.txt`

## Installation and Setup
1. Clone or download this repository.
2. Install Python if not already installed (from [python.org](https://www.python.org/downloads/)).
3. Install dependencies:

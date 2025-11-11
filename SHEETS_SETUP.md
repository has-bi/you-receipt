# Google Sheets Setup Guide

This guide will help you set up the required Google Sheets for the Pharmacy Stock Management System.

## Overview

You need to create **TWO** Google Sheets:
1. **Master Data Sheet** - Contains reference data (ASMs, Stores, Products, Areas)
2. **Output Sheet** - Stores stock entries submitted through the app

## 1. Master Data Sheet Setup

Create a new Google Sheet and name it "Pharmacy Master Data" (or any name you prefer).

### Sheet 1: ASM_Area

Create a sheet named exactly `ASM_Area` with these columns:

| ASM Name  | Area Code | Area Name |
|-----------|-----------|-----------|
| John Doe  | JKT       | Jakarta   |
| Jane Doe  | BDG       | Bandung   |
| Bob Smith | SBY       | Surabaya  |

**Column Definitions:**
- **ASM Name**: Full name of the Area Sales Manager
- **Area Code**: Short code for the area (e.g., JKT, BDG)
- **Area Name**: Full name of the area

### Sheet 2: Stores

Create a sheet named exactly `Stores` with these columns:

| Store ID | Store Name      | Area Code | Alamat           | Kota    |
|----------|-----------------|-----------|------------------|---------|
| ST001    | Apotek Sehat A  | JKT       | Jl. Sudirman 10  | Jakarta |
| ST002    | Apotek Kimia B  | JKT       | Jl. Thamrin 20   | Jakarta |
| ST003    | Apotek Farma C  | BDG       | Jl. Asia Afrika  | Bandung |
| ST004    | Apotek Medika D | SBY       | Jl. Pemuda 15    | Surabaya|

**Column Definitions:**
- **Store ID**: Unique identifier for the store
- **Store Name**: Full name of the pharmacy/store
- **Area Code**: Must match an area code from ASM_Area sheet
- **Alamat**: Street address
- **Kota**: City name

### Sheet 3: Products

Create a sheet named exactly `Products` with these columns:

| Product Name         | SKU Code  | Category      |
|---------------------|-----------|---------------|
| Paracetamol 500mg   | SKU-P001  | Pain Relief   |
| Amoxicillin 500mg   | SKU-A001  | Antibiotic    |
| Vitamin C 1000mg    | SKU-V001  | Supplement    |
| Ibuprofen 400mg     | SKU-I001  | Pain Relief   |
| Aspirin 100mg       | SKU-A002  | Cardiovascular|

**Column Definitions:**
- **Product Name**: Full product name with dosage
- **SKU Code**: Unique stock keeping unit code
- **Category**: Product category

### Sheet 4: Areas

Create a sheet named exactly `Areas` with these columns:

| Area Code | Area Name | Region      |
|-----------|-----------|-------------|
| JKT       | Jakarta   | Jabodetabek |
| BDG       | Bandung   | West Java   |
| SBY       | Surabaya  | East Java   |

**Column Definitions:**
- **Area Code**: Short code (must match ASM_Area)
- **Area Name**: Full area name
- **Region**: Broader regional classification

### Get the Sheet ID

1. Open your Master Data Sheet in Google Sheets
2. Look at the URL: `https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit`
3. Copy the `SHEET_ID` portion
4. Add it to your `.env` file as `MASTER_SHEET_ID`

---

## 2. Output Sheet Setup

Create a **NEW** Google Sheet and name it "Pharmacy Stock Output" (or any name you prefer).

### Sheet: Stock_Output

Create a sheet named exactly `Stock_Output` with these columns (just the header row):

| Timestamp           | Area | ASM      | Store          | SKU      | Stock Awal | Stock Akhir | Stock Terjual | Link Foto        | Method |
|---------------------|------|----------|----------------|----------|------------|-------------|---------------|------------------|--------|

**Leave the data rows empty** - the application will automatically append data here.

**Column Definitions:**
- **Timestamp**: Auto-generated (format: YYYY-MM-DD HH:MM:SS)
- **Area**: Area code from ASM lookup
- **ASM**: ASM name from user input
- **Store**: Store name (from master for manual, free text for OCR)
- **SKU**: Product SKU code
- **Stock Awal**: Beginning stock (optional)
- **Stock Akhir**: Ending stock (optional)
- **Stock Terjual**: Sold quantity (MANDATORY)
- **Link Foto**: GCS public URL (for OCR entries, empty for manual)
- **Method**: "manual" or "ocr"

### Get the Sheet ID

1. Open your Output Sheet in Google Sheets
2. Look at the URL: `https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit`
3. Copy the `SHEET_ID` portion
4. Add it to your `.env` file as `OUTPUT_SHEET_ID`

---

## 3. Share Sheets with Service Account

**IMPORTANT**: You must share both sheets with your service account.

1. Open your `credentials.json` file
2. Find the `client_email` field (looks like: `xxx@xxx.iam.gserviceaccount.com`)
3. Copy this email address
4. For **both** Google Sheets:
   - Click "Share" button (top right)
   - Paste the service account email
   - Give "Editor" permissions
   - Uncheck "Notify people"
   - Click "Share"

---

## 4. Example Data Template

You can copy this example data to test the system:

### ASM_Area Example:
```
ASM Name,Area Code,Area Name
John Doe,JKT,Jakarta
Jane Smith,BDG,Bandung
Robert Johnson,SBY,Surabaya
Alice Brown,MDN,Medan
```

### Stores Example:
```
Store ID,Store Name,Area Code,Alamat,Kota
ST001,Apotek Sehat Sentosa,JKT,Jl. Sudirman No. 123,Jakarta
ST002,Kimia Farma Jakarta Pusat,JKT,Jl. Thamrin No. 45,Jakarta
ST003,Guardian Bandung,BDG,Jl. Asia Afrika No. 67,Bandung
ST004,Century Healthcare Surabaya,SBY,Jl. Pemuda No. 89,Surabaya
```

### Products Example:
```
Product Name,SKU Code,Category
Paracetamol 500mg Strip,SKU-PAR-500,Analgesik
Amoxicillin 500mg Kapsul,SKU-AMX-500,Antibiotik
Vitamin C 1000mg Tablet,SKU-VTC-1000,Suplemen
Ibuprofen 400mg Tablet,SKU-IBU-400,Analgesik
Omeprazole 20mg Kapsul,SKU-OMP-20,Lambung
```

### Areas Example:
```
Area Code,Area Name,Region
JKT,Jakarta,Jabodetabek
BDG,Bandung,Jawa Barat
SBY,Surabaya,Jawa Timur
MDN,Medan,Sumatera Utara
```

---

## 5. Verification Checklist

Before running the application, verify:

- [✅] Master Data Sheet created with 4 sheets (ASM_Area, Stores, Products, Areas)
- [✅] Output Sheet created with 1 sheet (Stock_Output)
- [✅] All sheets have correct column headers (exact spelling matters!)
- [✅] At least 1-2 rows of sample data in master sheets
- [✅] Both sheets shared with service account email (Editor permissions)
- [✅] MASTER_SHEET_ID added to .env file
- [✅] OUTPUT_SHEET_ID added to .env file

---

## Common Issues

**"Service account doesn't have access"**
- Make sure you shared the sheet with the service account email
- Check that you gave "Editor" permissions, not just "Viewer"

**"Sheet not found" error**
- Verify the sheet names are exactly: `ASM_Area`, `Stores`, `Products`, `Areas`, `Stock_Output`
- Sheet names are case-sensitive!

**"Invalid SHEET_ID"**
- Double-check the SHEET_ID from the URL
- Make sure there are no extra spaces in your .env file

**Data not appearing in output sheet**
- Check that Stock_Output sheet exists
- Verify column headers match exactly (including spacing)
- Check application logs for specific errors

---

## Tips

1. **Backup**: Make a copy of your sheets regularly
2. **Validation**: Use Google Sheets data validation to prevent invalid entries
3. **Formatting**: You can format the Output sheet (colors, borders) - the app only appends data
4. **Analysis**: Add additional sheets to the Output spreadsheet for charts/analytics
5. **History**: Don't delete old data - use filters to view recent entries

---

For more help, see the main README.md file.

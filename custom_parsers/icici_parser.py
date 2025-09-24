import pdfplumber
import pandas as pd
import re

def parse(pdf_path):
    try:
        all_data = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    if table:  # Check if table is not empty
                        for row in table[1:]: # Skip header row if present
                            if row and len(row) == 5:  # Ensure 5 columns and not empty row
                                try:
                                    date, description, debit, credit, balance = row

                                    # Sanitize values
                                    date = str(date).strip()
                                    description = str(description).strip()
                                    debit = float(str(debit).replace(",", "").strip()) if debit and str(debit).strip() else None
                                    credit = float(str(credit).replace(",", "").strip()) if credit and str(credit).strip() else None
                                    balance = float(str(balance).replace(",", "").strip()) if balance and str(balance).strip() else None

                                    row_data = {
                                        'Date': date,
                                        'Description': description,
                                        'Debit Amt': debit,
                                        'Credit Amt': credit,
                                        'Balance': balance,
                                    }
                                    all_data.append(row_data)

                                except (ValueError, IndexError) as e:
                                    print(f"Error processing row: {row}. Error: {e}")  # Log the error but continue
                            elif row and len(row) !=5: # Handle variations in row length due to merged cells
                                print(f"Skipping row due to incorrect number of columns: {row}")


        df = pd.DataFrame(all_data)
        return df

    except FileNotFoundError:
        print(f"Error during parsing: [Errno 2] No such file or directory: '{pdf_path}'")
        return None
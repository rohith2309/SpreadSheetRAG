import pandas as pd

def extract_sheet_data(file_path:str):
    
    sheets_peek={}

        
    with pd.ExcelFile(file_path) as xls:
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet, header=None, nrows=20)
            
            df = df.dropna(how="all", axis=1)
            
            sheets_peek[sheet] = df.fillna("").astype(str).values.tolist()

    return sheets_peek
    

        
        
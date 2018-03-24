import openpyxl
from rkka-staffing import StaffingInfile

out_dir = r'.\input_data'


class ExcelReader(object):
    def __init__(self, xlsx_file_path: str):
        self.workbook = openpyxl.load_workbook(xlsx_file_path, read_only=True, data_only=True)

    def save_sheets(self) -> list:
        for sheet in self.workbook:
            print(sheet.title)
            fname = out_dir + '\\rkka-staff-%s.orig.txt' % sheet.title.replace('-', '')
            with open(fname, 'w', encoding='utf-8') as file:
                for row in sheet.iter_rows():
                    line = '\t'.join([str(c.value) for c in row])
                    line = line.replace(' 00:00:00', '').replace('None', '')
                    file.write(line)
                    file.write('\n')
            sf = StaffingInfile(fname)
            sf.preprocess_and_write_inputs_back()


if __name__ == '__main__':
    ExcelReader(r'c:\Users\yehor\OneDrive\Projects\com.schemeofwar\Боевой состав.xlsm').save_sheets()
    # ExcelReader(r'f:\repos\onedrive\yehor.churilov\OneDrive\Projects\com.schemeofwar\Боевой состав.xlsm').save_sheets()

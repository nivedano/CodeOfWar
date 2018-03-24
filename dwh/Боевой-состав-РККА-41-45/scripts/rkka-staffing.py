import os
import json
from datetime import datetime
from htmlmarkup import *
import re
from typing import Union


def cutout(s: str, m):
    return s[:m.start()] + s[m.end():]


text_separator = '\t'
rkka_staffing_input_file_dir = './input_data'
rkka_staffing_output_file_dir = './output_data'
rkka_staffing_files = ['%s/%s' % (rkka_staffing_input_file_dir, f) for f in os.listdir(rkka_staffing_input_file_dir) if f.endswith('.orig.txt')]

rx_unqual_unit = re.compile(r'(?P<unit>\b\d+),? ?')
rx_unqual_unit_w = re.compile(r'(?P<unit>\b[\w.-]+),? ?')
# 130, 156, 262, 315 кап
rx_unit_list = re.compile(r'(?P<list>(\b\d+,? ?)+)(?P<unitOrg>(\b[\w./]* ?)+),? ?')
# Выборгский, Мурманский, Псковский, Лужский, Петрозаводский бригадный район ПВО
rx_brigade_region_list = re.compile(r'(?P<list>(\b[\w-]+,? ?)+)(?P<unitOrg>бригадный район ПВО),? ?')
# 42 ск (104, 122 сд)
rx_compound_unit_list = re.compile(r'(?P<compUnit>\b\d+[\w ./]+?)[ ]*\((?P<unitList>.*)\),? ?')


class StaffingInfile(object):

    @property
    def cur_line(self) -> str:
        return self.intable[self.cur_line_num]

    @property
    def num_cols(self) -> int:
        return len(self.cur_line_col_map) - 1;

    def __init__(self, path: str):
        self.errors = []
        self.input_linenum = 0
        self.output_linenum = 0
        self.input_filename = path
        root, filename = os.path.split(self.input_filename)
        (name, ext) = os.path.splitext(filename)
        name = name.replace('.orig', '')
        self.out_file_path: str = os.path.join(rkka_staffing_output_file_dir, '%s.out%s' % (name, ext))
        self.error_file_path: str = os.path.join(rkka_staffing_output_file_dir, '%s.errors%s' % (name, ext))
        self.html_markup_filename = os.path.join(rkka_staffing_output_file_dir, '%s.%s' % (name, 'html'))

        self.contents: List[str] = open(path, 'r', encoding='utf-8').readlines()

        self.intable = [self.preprocess_line(self.contents[i], i) for i in range(len(self.contents))]
        # self.intable =  [l.split(text_separator) for l in self.contents]
        self.outtable = []
        # здесь для каждой строки записываются (start-index, end-index) для опознанных подстрок
        # размер должен совпадать с рамером входной таблицs
        self.parsed_ranges: list = [[] for _ in self.intable]
        self.parsed_end: int = 0
        self.cur_line_num: int = 0
        # индексы разделителей в текущей строке, обновляется после сброса в None
        self.cur_line_col_map = None
        self.cur_record_head = None

    def process(self, only_line: int = -1):
        if only_line > len(self.intable):
            self.error('номер строки вне диапазона')
            return
        self.outtable = []
        self.input_linenum = 0
        self.output_linenum = 0
        for self.cur_line_num in range(len(self.intable)) if only_line < 0 else [only_line]:
            self.cur_line_col_map = None
            self.input_linenum += 1
            line: str = self.intable[self.cur_line_num]
            if len(line) == 0:
                self.error('пустая строка')
                continue
            if len(line) < 5:
                self.error('в строке меньше 5 позиций')
                continue
            try:
                # col 0
                curdate = self.take_col(0)
                try:
                    this_date = datetime.strptime(curdate[0], '%Y-%m-%d')
                    self.record_parsed(curdate[1], curdate[2])
                    self.cur_record_head = [this_date.strftime('%Y-%m-%d')]
                except ValueError:
                    self.error('не могу распознать дату')
                    raise ImportError
                # col 1
                if self.num_cols < 2:
                    continue
                self.process_hq_resource_type(1)
                # col 2
                if self.num_cols < 3:
                    continue
                self.process_front(2)
                # col 3
                if self.num_cols < 4:
                    continue
                self.process_army(3)
                # cols from 4
                if len(self.cur_line_col_map) < 5 + 1:
                    continue
                self.process_units(4)
            except ImportError:
                continue
        outtable = []
        tset = set()
        for l in self.outtable:
            key = ''.join(l[2:])
            if key not in tset:
                tset.add(key)
                outtable.append(l)
        self.outtable = outtable
        self.outtable = [l[1:] for l in self.outtable]

    def process_hq_resource_type(self, col: int):
        hq = self.take_col(col)
        if len(hq[0]) < 2:
            self.error('тип стратегического задействования не распознан')
            raise ImportError
        self.record_parsed(hq[1], hq[2])
        self.cur_record_head += [hq[0]]
        self.write_fact(None)

    def process_front(self, col: int):
        front = self.take_col(col)
        if len(front[0]) < 2:
            # self.error('имя фронта не распознано')
            return
        self.record_parsed(front[1], front[2])
        self.cur_record_head += [front[0]]
        self.write_fact(None)

    def process_army(self, col: int):
        army = self.take_col(col)
        if len(army[0]) < 2:
            # self.error('имя армии не распознано')
            return
        self.record_parsed(army[1], army[2])
        self.cur_record_head += [army[0]]
        self.write_fact(None)

    def process_units(self, start_col: int):

        def process_unit_list(end_pos: int):
            return self.process_general_unit_list(rx_unit_list, start_pos, end_pos)

        def process_brigade_region_list(end_pos: int):
            return self.process_general_unit_list(rx_brigade_region_list, start_pos, end_pos)

        cur_line = self.cur_line
        start_pos = self.cur_line_col_map[start_col] + 1
        while True:
            cul = rx_compound_unit_list.search(cur_line, start_pos)
            if cul is None:
                break
            record = cul['compUnit']
            self.write_fact(record)
            self.record_parsed(cul.start('compUnit'), cul.end('compUnit'))
            start_pos = cul.end('compUnit') + 1
            process_unit_list(cul.end())
            start_pos = cul.end() + 1
        if start_pos < len(cur_line):
            start_pos = process_unit_list(len(cur_line))
        if start_pos < len(cur_line):
            start_pos = process_brigade_region_list(len(cur_line))

    # возвращает конечную позицию поиска
    def process_general_unit_list(self, rx, start_pos: int, end_pos: int) -> int:
        cur_line = self.cur_line
        while True:
            ul = rx.search(cur_line, start_pos, end_pos)
            if ul is None:
                break
            self.record_parsed(ul.start(), ul.end())
            units = [x['unit'] for x in rx_unqual_unit_w.finditer(ul['list'])]
            for u in units:
                unit = '%s %s' % (u, ul['unitOrg'])
                self.write_fact(unit)
            start_pos = ul.end() + 1
        return start_pos

    def record_parsed(self, start: int, end: int):
        self.parsed_ranges[self.cur_line_num] += [(start, end)]

    # возвращает строку из колонки, начальную и конечную позицию
    def take_col(self, col_num: int) -> (str, int, int):
        line: str = self.intable[self.cur_line_num]
        if self.cur_line_col_map is None:
            # -1 потому как мы указываем позиции разделителей, пусть и виртуальных, а 0 указывает на начало колонки
            self.cur_line_col_map = [-1] + [i for i in range(len(line)) if line[i] == text_separator]
            self.cur_line_col_map += [len(line)]
        if 0 <= col_num < len(self.cur_line_col_map) - 1:
            tab1 = self.cur_line_col_map[col_num] + 1
            tab2 = self.cur_line_col_map[col_num + 1]
            return line[tab1:tab2], tab1, tab2
        raise IndexError

    def write_fact(self, unit: Union[str, None]):
        self.output_linenum += 1
        record = [format(self.output_linenum, '03d'),  format(self.input_linenum, '03d')]
        record += self.cur_record_head
        if unit is not None:
            record += [unit]
        self.outtable.append(record)

    def preprocess_line(self, line: str, line_num: int) -> str:
        result = line.strip()
        str_to_replace = [(' и ', ', '), ('-я ', ' ')]
        for repl in str_to_replace:
            orig = repl[0]
            count = result.count(orig)
            if count > 0:
                target = repl[1]
                result = result.replace(orig, target)
                self.error('произведена замена "%s": %d' % (orig, count), line_num)
        return result

    def error(self, message: str, line_num: Union[int, None] = None):
        self.errors.append(['%s: ' % self.cur_line_num if line_num is None else line_num, message])

    # здесь line 1-based
    def get_units_for(self, line_num: int) -> list:
        self.process(line_num - 1)
        return self.outtable

    def write_input_back(self):
        with open(self.input_filename, 'w', encoding='utf-8') as f:
            [f.write(x + ('\n' if not x.endswith('\n') else '')) for x in self.intable]

    def write_out_file(self):
        with open(self.out_file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(['\t'.join(l) for l in self.outtable]))

    def write_errors(self):
        if len(self.errors) > 0:
            with open(self.error_file_path, 'w', encoding='utf-8') as f:
                f.write('=== %s ===\n' % self.take_col(0)[0])
                for l in self.errors:
                    f.write('\t'.join([str(x) for x in l]) + '\n')

    def process_and_write(self):
        self.process()
        self.write_out_file()
        self.write_errors()
        hw = LinewiseHtmlMarkup(self.parsed_ranges, self.contents, self.html_markup_filename)
        hw.doc_title = self.cur_record_head[0]
        hw.process()

    def preprocess_and_write_inputs_back(self):
        self.write_input_back()
        self.write_errors()


def process_and_write_all():
    infiles = [StaffingInfile(x) for x in rkka_staffing_files]
    for f in infiles:
        f.process_and_write()
        print(f.input_filename)


def process_and_write_all_inputs_back():
    infiles = [StaffingInfile(x) for x in rkka_staffing_files]
    [f.preprocess_and_write_inputs_back() for f in infiles]


def analyze_line(file: str, line: int):
    infile = StaffingInfile(rkka_staffing_input_file_dir + '/' + file)
    out_facts = infile.get_units_for(line)
    (name, ext) = os.path.splitext(file)
    with open(rkka_staffing_output_file_dir + '/%s.analysys.txt' % name, 'w', encoding='utf-8') as f:
        raw_line = infile.contents[line - 1]
        f.write(raw_line)
        f.write('\n')
        out_lines = ['\t'.join([str(e) for e in f[1:]]) + '\n' for f in out_facts]
        f.writelines(out_lines)


if __name__ == '__main__':
    # analyze_line('rkka-staff-19410622.txt', 17)
    # process_and_write_all_inputs_back()
    process_and_write_all()

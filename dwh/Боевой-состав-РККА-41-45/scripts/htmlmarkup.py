from typing import List


class LinewiseHtmlMarkup(object):

    def __init__(self, ranges: list, in_lines: List[str], out_file_name: str):
        if len(ranges) != len(in_lines):
            raise ValueError('lenths must be the same')
        self.line_ranges = ranges
        self.input_lines = in_lines
        self.out_file_name = out_file_name
        self.outf = None

        self.body_bgcolor: str = 'white'
        self.mark_bgcolor: str = 'yellow'
        self.delim_replacement: str = '<span class="delim">|</span>'
        self.doc_title = 'Document'
        self.whitespace = ', ()'
        self.delimeter = '\t'

    def process(self):
        self.preprocess()
        with open(self.out_file_name, 'w', encoding='utf-8') as self.outf:
            self.write_header()
            for i in range(len(self.input_lines)):
                line = ''
                cur_line = self.input_lines[i]
                cur_line_ranges = self.line_ranges[i]
                last_pos = 0
                for r in cur_line_ranges:
                    line += self.format_marked(cur_line[last_pos:r[0]])
                    line += self.format_plain(cur_line[r[0]:r[1]])
                    last_pos = r[1]
                line += self.format_plain(cur_line[last_pos:len(cur_line)])
                line = self.format_line(line)
                self.outf.write(line)
            self.write_footer()

    def preprocess(self):
        try:
            self.line_ranges = [sorted(r, key=lambda x: x[0]) for r in self.line_ranges]
        except IndexError:
            pass

    def write_header(self):
        header = '<html><head>\n<title>%s</title>\n</head>\n' % self.doc_title
        header += '<style>.marked { background: %s; }\n' % self.mark_bgcolor
        header += 'body {\nbackground: %s;\nfont-family: Verdana, sans-serif;\n'' \
            ''font-size: 10pt;\nwhite-space: nowrap;\noverflow:scroll;\n}\n' % self.body_bgcolor
        header += 'p { margin: 1pt 1pt 1pt 1pt }\n'
        header += '.delim { background: %s; padding-left: 5pt; padding-right: 5pt; }\n' % self.body_bgcolor
        header += '</style>\n'
        header += '<body>\n'
        self.outf.write(header)

    def write_footer(self):
        footer = '</body></html>'
        self.outf.write(footer)

    def format_plain(self, s: str):
        return s

    def format_marked(self, s: str):
        wp = self.delimeter + self.whitespace
        allwp = all([c in wp for c in s])
        s = s.replace(self.delimeter, self.delim_replacement)
        res = s if allwp else '<span class="marked">%s</span>' % s
        return res

    def format_line(self, line):
        res = '<p>%s</p>\n' % line
        return res

from dwh import *


class D3SankeyAnalys(object):
    def __init__(self, facts:list):
        self.facts = facts
        self.roots = {}
        self.all_nodes = []

    def gen_sankey_for_items(self, items: list) -> str:
        nodes = set()
        facts = []
        for item in items:
            factsl = self.filter_by(item)
            for f in factsl:
                for c in f:
                    nodes.add(c)
            facts += factsl

        rels_bin = []

        def already_added(link: list):
            return link in rels_bin

        for r in facts:
            for i in range(1, len(r)):
                if i + 1 < len(r):
                    link = [r[i], r[i + 1]]
                    if not already_added(link):
                        rels_bin.append(link)

        nodes = list(nodes)
        node_idx = dict(zip(nodes, [i for i in range(1, len(nodes))]))
        rel_struct = [(node_idx[r[0]], node_idx[r[1]]) for r in rels_bin]

    def gen_sankey_for_date(self, date: str):
        if self.roots is None:
            return None
        root = self.roots[date]
        if root is None:
            return None

    def gen_hierarchy(self) -> dict:
        self.roots = {}
        for fact in self.facts:
            date = fact[0]
            if date not in self.roots:
                root = self.create_node('РККА')
                self.roots[date] = root
            else:
                root = self.roots[date]
            for i in range(1, len(fact)):
                root = self.ensure_child(root, fact[i])
        for n in self.all_nodes:
            if len(n['children']) == 0:
                n['size'] = 100
                del n['children']

    def create_node(self, name: str) -> dict:
        node = {'name': name, 'children': []}
        self.all_nodes.append(node)
        return node

    def ensure_child(self, root: dict, node_name: str) -> dict:
        l: list = root['children']
        for n in l:
            if n['name'] == node_name:
                return n
        n = self.create_node(node_name)
        l.append(n)
        return n

    def filter_by(self, item: str) -> list:
        result = []
        for r in self.facts:
            i = 0
            for c in r:
                if c == item:
                    result.append(r[1:i + 1])
                    break
                i += 1
        return result


def gen_d3():
    infiles = [StaffingInfile(x) for x in rkka_staffing_files]
    [f.process() for f in infiles]
    sf = []
    for f in infiles:
        [sf.append(l[1:]) for l in f.outtable]

    d3 = D3SankeyAnalys(sf)
    # d3.gen_for_items(['71 сд'])
    d3.gen_hierarchy()
    dump = json.dumps(d3.roots['1941-06-22'], ensure_ascii=False, indent=4)
    open('../rkka-staffing/rkka.json', 'w', encoding='utf-8')\
        .write(dump)


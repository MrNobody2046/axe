# coding: utf-8
import logging
from optparse import OptionParser
from collections import OrderedDict

from lxml import etree


class Node(object):
    def __init__(self, name, parent=None):
        self.name = name
        self.children = OrderedDict()
        self.parent = parent
        self.value = None

    def add_child(self, name):
        child = self.children.get(name)
        if not child:
            child = Node(name, parent=self)
            self.children[name] = child
        return child

    get_child = add_child

    def bfs(self, call_back=lambda x: x, sort=False):
        call_back(self)
        if sort:
            children = sorted(self.children.values(), key=lambda x: (not x.is_leaf, x.name))
        else:
            children = self.children.values()
        for c in children:
            c.bfs(call_back=call_back, sort=sort)

    @property
    def is_leaf(self):
        return self.children == {}

    @property
    def deepness(self):
        if self.parent:
            return 1 + self.parent.deepness
        else:
            return 1

    @property
    def is_root(self):
        return not self.parent


class NodeMgr(object):
    def __init__(self, fp):
        self.fp = fp
        self.path_keys = set()
        self.root = None
        self.parse()

    def set_root(self, root):
        if not self.root:
            self.root = Node(root)
        return self.root

    def get_elem_path(self, elem):
        res = [elem.tag]
        while elem.getparent() is not None:
            elem = elem.getparent()
            res.append(elem.tag)
        return res

    def parse(self):
        context = etree.iterparse(self.fp, events=('end',))
        for action, elem in context:
            try:
                if len(elem.getchildren()) == 0:
                    path = self.get_elem_path(elem)
                    path_key = tuple(path)
                    if path_key not in self.path_keys:
                        self.path_keys.add(path_key)
                        self.append_path_on_tree(path)
            except Exception, e:
                logging.exception(e)
            finally:
                elem.clear()

    def append_path_on_tree(self, path):
        node = self.set_root(path.pop())
        while path:
            node = node.add_child(path.pop())

    @staticmethod
    def make_print_tree(indent):
        def print_tree(node):
            if node.is_root:
                print node.name + "(root)"
            else:
                print '|' + indent * (node.deepness - 2) + "--- " + node.name
        return print_tree

    def show_tree(self, indent="|   ", sort=False):
        self.root.bfs(call_back=self.make_print_tree(indent), sort=sort)


def show_tree(filename, sort, indent):
    NodeMgr(open(filename)).show_tree(indent=indent, sort=sort)


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="filename", help="xml file path", metavar="FILE")
    parser.add_option("-s", "--sort", dest="sort", default=False, help="sorted xml node by node name")
    parser.add_option("-i", "--indent", dest="indent", default="    |", help="your tree indent")

    (options, args) = parser.parse_args()
    filename = options.filename if options.filename else args[-1]
    print options, args

    show_tree(filename, options.sort and True, options.indent)

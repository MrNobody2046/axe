# coding: utf-8
import cStringIO
from lxml import etree


class Node(object):
    def __init__(self, name, parent=None):
        self.name = name
        self.children = {}
        self.parent = parent
        self.value = None

    def add_child(self, name):
        child = self.children.get(name)
        if not child:
            child = Node(name, parent=self)
            self.children[name] = child
        return child

    get_child = add_child

    def bfs(self, call_back=lambda x: x, leaf_stickied=True):
        call_back(self)
        if leaf_stickied:
            children = sorted(self.children.values(), key=lambda x: x.is_leaf, reverse=True)
        else:
            children = self.children.values()
        for c in children:
            c.bfs(call_back=call_back, leaf_stickied=leaf_stickied)

    @property
    def is_leaf(self):
        return self.children == {}

    @property
    def deepness(self):
        if self.parent:
            return 1 + self.parent.deepness
        else:
            return 1


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
                print e
            finally:
                elem.clear()

    def append_path_on_tree(self, path):
        node = self.set_root(path.pop())
        while path:
            node = node.add_child(path.pop())

    @staticmethod
    def make_print_tree(indent):
        def print_tree(node):
            print indent * (node.deepness - 1) + node.name

        return print_tree

    def print_tree(self, indent="\t|"):
        self.root.bfs(call_back=self.make_print_tree(indent))


if __name__ == "__main__":
    pass


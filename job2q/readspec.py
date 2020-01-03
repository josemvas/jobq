# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from xml.etree import ElementTree
from job2q.spectags import listTags, scriptTags, dictTags, runtimeTags, commandTags, textTags
from job2q import messages

class ScriptTestDict(dict):
    def __init__(self, script='', boolean=True):
        self.script = script
        self.boolean = boolean
    def __bool__(self):
        return not self.boolean if 'not' in self else self.boolean
    __nonzero__ = __bool__
    def __str__(self):
        return self.script

class XmlTreeList(list):
    def __init__(self, parent):
        for child in parent:
            if not len(child):
                if child.tag == 'e':
                    if parent.tag in scriptTags:
                        self.append(ScriptTestDict(script=child.text))
                        for attr in child.attrib:
                            self[-1][attr] = child.attrib[attr]
                    else:
                        self.append(child.text)
                elif child.tag in commandTags:
                    self.append(commandTags[child.tag] + ' ' + child.text)
                else:
                    messages.cfgerr('Invalid XmlTreeList Tag <{0}><{1}>'.format(parent.tag, child.tag))
            else:
                messages.cfgerr('XmlTreeList Tag <{0}><{1}> must not have grandchildren'.format(parent.tag, child.tag))
    def merge(self, other):
        for i in other:
            if i in self:
                if hasattr(self[i], 'merge') and type(other[i]) is type(self[i]):
                    self[i].merge(other[i])
                elif other[i] == self[i]:
                    pass # same leaf value
                else:
                    raise Exception('Conflict at' + ' ' + str(i))
            else:
                self.append(other[i])


class XmlTreeDict(dict):
    def __init__(self, parent):
        for child in parent:
            if len(child):
                if child.tag == 'e':
                    if 'key' in child.attrib:
                        self[child.attrib['key']] = XmlTreeDict(child)
                    else:
                        messages.cfgerr('XmlTreeDict Tag <{0}><e> must have a key attribute'.format(parent.tag))
                elif child.tag in listTags + scriptTags:
                    self[child.tag] = XmlTreeList(child)
                elif child.tag in dictTags + runtimeTags:
                    self[child.tag] = XmlTreeDict(child)
                else:
                    messages.cfgerr('Invalid XmlTreeDict Tag <{0}><{1}>'.format(parent.tag, child.tag))
            else:
                if child.tag == 'e':
                    if 'key' in child.attrib:
                        self[child.attrib['key']] = child.text
                    else:
                        self[child.text] = child.text
                elif child.tag in textTags or parent.tag in runtimeTags:
                    self[child.tag] = child.text
                else:
                    messages.cfgerr('Invalid XmlTreeDict Tag <{0}><{1}>'.format(parent.tag, child.tag))
    def __getattr__(self, item):
        try: return self.__getitem__(item)
        except KeyError:
            raise AttributeError(item)
    def __setattr__(self, item, value):
            self.__setitem__(item, value)
    def __missing__(self, item):
        if item in listTags + scriptTags + dictTags + runtimeTags:
            return []
    def merge(self, other):
        for i in other:
            if i in self:
                if hasattr(self[i], 'merge') and type(other[i]) is type(self[i]):
                    self[i].merge(other[i])
                elif other[i] == self[i]:
                    pass # same leaf value
                else:
                    raise Exception('Conflict at' + ' ' + str(i))
            else:
                self[i] = other[i]

def readspec(xmlfile, xmltag=None):
    root = ElementTree.parse(xmlfile).getroot()
    if xmltag is None:
        return XmlTreeDict(root)
    else:
        try: return root.find(xmltag).text
        except AttributeError:
            return None


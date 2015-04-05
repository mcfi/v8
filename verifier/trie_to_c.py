# Copyright (c) 2011 The Native Client Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# This file was modified from Mark Seaborn's verifier for nacl:
# https://github.com/mseaborn/x86-decoder

import sys
import trie

# Converts the trie/DFA to a C file.


# As an optimisation, group together accepting states of the same
# type.  This makes it possible to check for an accepting type with a
# range check.
def SortKey(node):
  if node.accept != False:
    return [0, node.accept]
  else:
    return [1]


def WriteTransitionTable(out, nodes, node_to_id):
  out.write('static const uint16_t trie_table[][256] = {\n')
  for node in nodes:
    out.write('  /* state %i: accept=%s */ {\n' %
              (node_to_id[node], node.accept))
    if 'XX' in node.children:
      assert len(node.children) == 1, node#, node.children
      bytes = [node_to_id[node.children['XX']]] * 256
    else:
      bytes = [0] * 256
      for byte, dest_node in node.children.iteritems():
        #print byte
        bytes[int(byte, 16)] = node_to_id[dest_node]
    out.write(' ' * 11 + '/* ')
    out.write('  '.join('X%x' % lower for lower in xrange(16)))
    out.write(' */\n')
    for upper in xrange(16):
      out.write('    /* %xX */  ' % upper)
      out.write(', '.join('%2i' % bytes[upper*16 + lower]
                          for lower in xrange(16)))
      out.write(',\n')
    out.write('  },\n')
  out.write('};\n')
  #out.write("""
#static inline uint16_t trie_lookup(uint16_t state, uint16_t byte) {
#  return trie_table[state][byte];
#}
#""")


def Main(trie_file):
  root_node = trie.TrieFromFile(trie_file)
  nodes = sorted(trie.GetAllNodes(root_node), key=SortKey)
  #for node in nodes:
  #  trie.Pr(node, sys.stderr)  
  # Node ID 0 is reserved as the rejecting state.  For a little extra
  # safety, all transitions from node 0 lead to node 0.
  nodes = [trie.EmptyNode] + nodes
  node_to_id = dict((node, index) for index, node in enumerate(nodes))

  out = open('trie_table.h', 'w')
  out.write('\n#include <stdint.h>\n\n')

  accept_types = set(node.accept for node in nodes
                     if node.accept != False)
  # This accept type disappears when relative jumps with 16-bit
  # offsets are disallowed, but it is nice to keep the C handler code
  # around.  Such jumps are not unsafe and could be allowed.
  #accept_types.add('jump_rel2')
  assert 'jmp_rel1' in accept_types
  assert 'jmp_rel4' in accept_types
  assert 'icall' in accept_types
  assert 'dcall' in accept_types
  assert 'mcficall' in accept_types
  assert 'mcficheck' in accept_types
  assert 'mcfiret' in accept_types

  WriteTransitionTable(out, nodes, node_to_id)
  states = len(nodes)
  verifier_template = """static const struct verifier_t {
  uint16_t *dfa;
  int states;
  uint16_t start;
  uint16_t dcall;
  uint16_t icall;
  uint16_t jmp_rel1;
  uint16_t jmp_rel4;
  uint16_t mcficall;
  uint16_t mcficheck;
  uint16_t mcfiret;
  int count; // number of accept states
  uint16_t accept[16]; // point to an array of accept states
} verifier = {
  (uint16_t*)trie_table,
  %d, /* states */
  %d, /* start */
  %d, /* dcall */
  %d, /* icall */
  %d, /* jmp_rel1 */
  %d, /* jmp_rel4 */
  %d, /* mcficall */
  %d, /* mcficheck */
  %d, /* mcfiret */
  %d, /* count */
  { %s } /* accept */
};"""

  icall = 0
  dcall = 0
  jmp_rel1 = 0
  jmp_rel4 = 0
  mcficall = 0
  mcficheck = 0
  mcfiret = 0
  count = 0
  accept = ''
  for accept_type in sorted(accept_types):
    acceptors = [node_to_id[node] for node in nodes
                 if node.accept == accept_type]
    print 'Type %r has %i acceptors' % (accept_type, len(acceptors))
    if accept_type == True:
      count = len(acceptors)
      accept = ', '.join(str(node_id) for node_id in acceptors)
    if accept_type == 'dcall':
      dcall = acceptors[0]
    if accept_type == 'icall':
      icall = acceptors[0]
    if accept_type == 'jmp_rel1':
      jmp_rel1 = acceptors[0]
    if accept_type == 'jmp_rel4':
      jmp_rel4 = acceptors[0]
    if accept_type == 'mcficall':
      mcficall = acceptors[0]
    if accept_type == 'mcficheck':
      mcficheck = acceptors[0]
    if accept_type == 'mcfiret':
      mcfiret = acceptors[0]

  start = node_to_id[root_node]
  verifier = verifier_template % (states, start, dcall, icall, jmp_rel1, jmp_rel4,\
                                  mcficall, mcficheck, mcfiret, \
                                  count, accept)
  print verifier
  out.write(verifier)
  #for accept_type in sorted(accept_types):
  #  acceptors = [node_to_id[node] for node in nodes
  #               if node.accept == accept_type]
  #  print 'Type %r has %i acceptors' % (accept_type, len(acceptors))
  #  if len(acceptors) > 0:
  #    expr = ' || '.join('node_id == %i' % node_id for node_id in acceptors)
  #  else:
  #    expr = '0 /* These instructions are currently disallowed */'
  #  out.write('static inline int trie_accepts_%s(int node_id) '
  #            '{\n  return %s;\n}\n\n'
  #            % (accept_type, expr))
  #out.write('static const uint16_t trie_start = %i;\n\n' % node_to_id[root_node])

  out.close()


if __name__ == '__main__':
  Main(sys.argv[1])

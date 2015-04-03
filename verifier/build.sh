#!/bin/bash

echo "Enumerating instructions..."
./instr.py > inst
echo "Generating Trie..."
python trie.py inst
echo "Converting Trie..."
python trie_to_c.py inst.trie
echo "Compiling..."
gcc -O3 dfa_ncval.c -o dfa_ncval

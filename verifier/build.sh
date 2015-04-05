#!/bin/bash

echo "Enumerating instructions..."
./instr.py > inst
echo "Generating Trie..."
python trie.py inst
echo "Converting Trie..."
python trie_to_c.py inst.trie
cp trie_table.h ../src/x64/
echo "Done"
#echo "Compiling..."
#gcc -O3 dfa_ncval.c -o dfa_ncval

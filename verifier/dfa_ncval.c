/*
 * Copyright (c) 2011 The Native Client Authors. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 * This file was modified from Mark Seaborn's verifier for nacl:
 * https://github.com/mseaborn/x86-decoder
 */

#include <assert.h>
#include <elf.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "trie_table.h"

static const int kBitsPerByte = 8;

static const uint32_t ConstLoadAddr = 0x80000000; // 2GB

static inline uint8_t *BitmapAllocate(uint32_t indexes) {
  uint32_t byte_count = (indexes + kBitsPerByte - 1) / kBitsPerByte;
  uint8_t *bitmap = malloc(byte_count);
  if (bitmap != NULL) {
    memset(bitmap, 0, byte_count);
  }
  return bitmap;
}

static inline int BitmapIsBitSet(uint8_t *bitmap, uint32_t index) {
  return (bitmap[index / kBitsPerByte] & (1 << (index % kBitsPerByte))) != 0;
}

static inline void BitmapSetBit(uint8_t *bitmap, uint32_t index) {
  bitmap[index / kBitsPerByte] |= 1 << (index % kBitsPerByte);
}

int CheckJumpTargets(uint8_t *valid_targets, uint8_t *jump_dests,
                     size_t size) {
  int i;
  for (i = 0; i < size / 32; i++) {
    uint32_t jump_dest_mask = ((uint32_t *) jump_dests)[i];
    uint32_t valid_target_mask = ((uint32_t *) valid_targets)[i];
    if ((jump_dest_mask & ~valid_target_mask) != 0) {
      printf("bad jump to around %lx\n", i * sizeof(uint32_t));
      return 1;
    }
  }
  return 0;
}

// starting from state 'start', test whether the current stream will eventually
// lead to acceptance
static int validate(uint8_t *cur, uint8_t *end,
                    uint16_t start, uint16_t *end_state, uint8_t** endptr) {
  uint16_t state = start;
  while (cur < end) {
    state = trie_lookup(state, *cur++);
    if (0 == state) {
      return -1;
    } else if (trie_accepts_mcficall(state) ||
               trie_accepts_mcfiret(state) ||
               trie_accepts_mcficheck(state) ||
               trie_accepts_icall(state) ||
               trie_accepts_dcall(state) ||
               trie_accepts_jmp_rel1(state) ||
               trie_accepts_jmp_rel4(state)) {
      *end_state = state;
      *endptr = cur;
      return 0;
    } else if (trie_accepts_True(state)) {
      *end_state = state;
      *endptr = cur;
      validate(cur, end, state, end_state, endptr);
      return 0;
    }
  }
  return 1;
}

int ValidateChunk(uint32_t load_addr, uint8_t *data, size_t size) {
  int result = 0;

  uint8_t *valid_targets = BitmapAllocate(size);
  uint8_t *jump_dests = BitmapAllocate(size);
  uint32_t offset = 0;
  uint8_t *ptr = data;
  uint8_t *end = data + size;
  uint8_t *endptr = 0;
  uint16_t state;
  uint8_t *i;

  int line = 1;
  while (ptr < end) {
    result = validate(ptr, end, trie_start, &state, &endptr);
    //for (i = ptr; i < endptr; i++)
    //  fprintf(stderr, "0x%02x ", *i);
    //fprintf(stderr, "\n");

    if (result != 0) {
      fprintf(stderr, "Error: 0x%02x, %lx\n", *ptr, ptr - data);
      exit(-1);
    }
    ptr = endptr;
  }
  /*
  while (ptr < end) {
    printf("0x%02x ", *ptr);
    state = trie_lookup(state, *ptr);
    if (0 == state) {
      printf("rejected at %d, (byte 0x%02x)\n",
             line, *ptr);
      return 1;
    }
    if (trie_accepts_mcficall(state) ||
        trie_accepts_mcfiret(state) ||
        trie_accepts_mcficheck(state) ||
        trie_accepts_icall(state) ||
        trie_accepts_dcall(state) ||
        trie_accepts_jmp_rel1(state) ||
        trie_accepts_jmp_rel4(state)) {
      state = trie_start;
      ++line;
      printf("\n");
    }

    if(trie_accepts_True(state)) {
      state = trie_start;
      ++line;
      printf("\n");
    }

    ptr++;
    offset++;
    }*/

  /*if (CheckJumpTargets(valid_targets, jump_dests, size)) {
    return 1;
    }*/

  free(valid_targets);
  free(jump_dests);
  return result;
}

void ReadFile(const char *filename, uint8_t **result, size_t *result_size) {
  FILE *fp;
  uint8_t *data;
  size_t file_size;
  size_t got;

  fp = fopen(filename, "rb");
  if (fp == NULL) {
    fprintf(stderr, "Failed to open input file: %s\n", filename);
    exit(1);
  }
  /* Find the file size. */
  fseek(fp, 0, SEEK_END);
  file_size = ftell(fp);
  data = malloc(file_size);
  if (data == NULL) {
    fprintf(stderr, "Unable to create memory image of input file: %s\n",
            filename);
    exit(1);
  }
  fseek(fp, 0, SEEK_SET);
  got = fread(data, 1, file_size, fp);
  if (got != file_size) {
    fprintf(stderr, "Unable to read data from input file: %s\n",
            filename);
    exit(1);
  }
  fclose(fp);

  *result = data;
  *result_size = file_size;
}

int ValidateFile(const char *filename) {
  size_t data_size;
  uint8_t *data;
  ReadFile(filename, &data, &data_size);
  return ValidateChunk(0x80000000,data, data_size);
}

int main(int argc, char **argv) {
  int index;
  if (argc == 1) {
    printf("%s: no input files\n", argv[0]);
  }
  for (index = 1; index < argc; index++) {
    const char *filename = argv[index];
    int rc = ValidateFile(filename);
    if (rc != 0) {
      printf("file '%s' failed validation\n", filename);
      return 1;
    }
  }
  return 0;
}

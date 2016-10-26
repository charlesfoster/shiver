#!/usr/bin/env python
from __future__ import print_function

## Author: Chris Wymant, c.wymant@imperial.ac.uk
## Acknowledgement: I wrote this while funded by ERC Advanced Grant PBDR-339251
##
## Overview:
ExplanatoryMessage = '''This script converts each base in a set of aligned
sequences in fasta format to one of four codes, as a first step towards
visualisation of the alignment (the four codes will be displayed differently).
The codes are 'g' for a base that agrees with the most common base at this
position in the alignment, 'b' for a base that disagrees with the most common
base at this position in the alignment (used for all bases when there is no
unique most common base, i.e. two bases are equally most common), 'd' for a gap
character that has at least one base somewhere to its left and at least one base
somewhere to its right (i.e. internal gaps, i.e. deletions), and 'n' for gap
characters before the sequence starts or after it finishes. Output is printed to
stdout, suitable for redirection, in csv format (column 1 the seqeunce name,
column 2 the sequence translated to these codes).
'''

import argparse
import os
import sys
import re
from Bio import AlignIO
from Bio import Seq  
import collections

# Define a function to check files exist, as a type for the argparse.
def File(MyFile):
  if not os.path.isfile(MyFile):
    raise argparse.ArgumentTypeError(MyFile+' does not exist or is not a file.')
  return MyFile

# Set up the arguments for this script
ExplanatoryMessage = ExplanatoryMessage.replace('\n', ' ').replace('  ', ' ')
parser = argparse.ArgumentParser(description=ExplanatoryMessage)
parser.add_argument('alignment', type=File)
parser.add_argument('-R', '--reorder', action='store_true', help='''Does some 
hard-coded reordering and renaming of sequences, specific to the sequence names
found in the shiver publication. (Unlikely to be useful to anyone but the code's
author.)''')
args = parser.parse_args()

# Read in the alignment
try:
  alignment = AlignIO.read(args.alignment, "fasta")
except:
  print('Problem reading', args.alignment + ':', file=sys.stderr)
  raise
AlignmentLength = alignment.get_alignment_length()

# Convert the alignment to upper case
for i in range(len(alignment)):
  alignment[i].seq = Seq.Seq(str(alignment[i].seq).upper())

# Construct a list whose nth element is the consensus base at position n in the
# alignment, or the value None if there is no consensus at position n (all gaps,
# or a tie for the most common base).
ConsensusBases = []
for position in range(0, AlignmentLength):
  BasesHere = alignment[:, position]
  BasesHereNoGaps = BasesHere.replace('-','')
  if len(BasesHereNoGaps) == 0:
    ConsensusBases.append(None)
    continue
  BaseCounts = collections.Counter(BasesHereNoGaps)
  MostCommonTwoBases = BaseCounts.most_common(2)
  if len(MostCommonTwoBases) > 1 and \
  MostCommonTwoBases[1][1] == MostCommonTwoBases[0][1]:
    ConsensusBases.append(None)
  else:
    ConsensusBases.append(MostCommonTwoBases[0][0])

OutList = []
for seq in alignment:

  # Assign colour codes
  ColourCodes = ''
  for position, base in enumerate(str(seq.seq)):
    if base == '-':
      ColourCodes += 'd'
    elif base == ConsensusBases[position]:
      ColourCodes += 'g'
    else:
      ColourCodes += 'b'

  # Replace leading and trailing deletions by their own character
  try:
    FirstBasePos = 0
    while ColourCodes[FirstBasePos] == 'd':
      FirstBasePos += 1
  except IndexError:
    # This 'sequence' is nothing but gaps.
    ColourCodes = 'n' * AlignmentLength
  else:
    LastBasePos = AlignmentLength - 1
    while ColourCodes[LastBasePos] == 'd':
      LastBasePos -= 1
    ColourCodes = 'n' * FirstBasePos + ColourCodes[FirstBasePos:LastBasePos+1] \
    + 'n' * (AlignmentLength -1 - LastBasePos)

  OutList.append((seq.id, ColourCodes))

if args.reorder:

  # Regular expressions (regexs) to find consensuses and references, and what
  # we want to rename them to:
  regexs  = []
  NewNames = []
  regexs.append('^B.FR.83.HXB2_LAI_IIIB_BRU.K03455$')
  NewNames.append('HXB2')
  regexs.append('_ConsensusRound1_GapsFilled$')
  NewNames.append('shiver reference')
  regexs.append('_remap_consensus$')
  NewNames.append('shiver consensus')
  regexs.append('_HXB2_consensus$')
  NewNames.append('HXB2 consensus')

  # Find, rename and reorder consensuses and references; collect other sequences
  # (contigs) separately.
  NumRegexs = len(regexs)
  CompiledRegexs = [re.compile(regex) for regex in regexs]
  RegexsFound = [False for regex in regexs]
  ColourCodesRefsAndConsensuses = ['' for i in range(NumRegexs)]
  ColourCodesContigs = []
  for SeqID, ColourCodes in OutList:
    for i, CompiledRegex in enumerate(CompiledRegexs):
      IsContig = True
      if CompiledRegex.search(SeqID):
        ColourCodesRefsAndConsensuses[i] = ColourCodes
        RegexsFound[i] = True
        IsContig = False
        break
    if IsContig:
      ColourCodesContigs.append(ColourCodes)

  # Check we found all regexs
  MissingRegexs = [regexs[i] for i in range(NumRegexs) if not RegexsFound[i]]
  if len(MissingRegexs) > 0:
    print('The following regexes were not found in', args.alignment + ':', \
    ' '.join(MissingRegexs) + '. Quitting.', file=sys.stderr)
    exit(1)

  # Combine consensuses, references and contigs
  OutListReordered = [(NewNames[i], ColourCodesRefsAndConsensuses[i]) \
  for i in range(NumRegexs)]
  for i, ContigColourCode in enumerate(ColourCodesContigs):
    OutListReordered.append(('contig ' +str(i+1), ContigColourCode))
  OutList = OutListReordered

# Print output
for seq.id, ColourCodes in OutList:
  print(seq.id + ',' + ColourCodes)



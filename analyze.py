#!/usr/bin/env python
# Copyright (c) 2012 Gregory L. Rosenblatt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
from collections import defaultdict, namedtuple
from math import sqrt
import string
from subprocess import Popen, PIPE
import sys

class Repr(object):
  def _repr(self): return ()
  def __repr__(self): return '%s(%s)' % (self.__class__.__name__, self._repr())

class FileMod(Repr):
  def __init__(self, line):
    insertions, deletions, self.fname = line.split('\t')
    self.insertions = int(insertions)
    self.deletions = int(deletions)
  def _repr(self): return [self.fname, self.insertions, self.deletions]

def sum_changes(objs, pred=lambda _: True):
  return [sum(getattr(obj, attr) for obj in objs if pred(obj))
          for attr in ('insertions', 'deletions')]

class Commit(Repr):
  def __init__(self, fields):
    self.time, self.author, self.uid = fields[:3]
    self.fmods = map(FileMod, fields[3:])
    self.insertions, self.deletions = sum_changes(self.fmods)
  def _repr(self):
    return [self.time, self.author, self.uid, self.insertions, self.deletions]

def commits(branch=None, merges=None, delimeter='BEGINCOMMIT'):
  fmt = delimeter + '%n%at%n%an%n%H' # unixtime, author, hash
  cmd = ['git', 'log', '--format='+fmt, '--numstat']
  if merges is not None:
    if merges: cmd.append('--merges')
    else: cmd.append('--no-merges')
  if branch is not None: cmd.append(branch)
  proc = Popen(cmd, stdout=PIPE)
  out, _ = proc.communicate()
  blobs = map(string.strip, out.split(delimeter))[1:]
  return [Commit(filter(None, commit.split('\n'))) for commit in blobs]

def by_author(cmts):
  author_to_commits = defaultdict(list)
  for commit in cmts: author_to_commits[commit.author].append(commit)
  return author_to_commits

Changes = namedtuple('Changes', 'insertions deletions')
Stats = namedtuple('Stats', 'count total mean std')
def compute_stats(attr, cmts, pred=lambda _, __: True):
  xs = [getattr(commit, attr) for commit in cmts if pred(commit, attr)]
  if not xs: return Stats(0, 0, 0, 0)
  count = float(len(xs))
  total = sum(xs)
  mean = total / count
  std = sqrt(sum((xx - mean)**2 for xx in xs) / count)
  return Stats(count, total, mean, std)

class CommitStats(Repr):
  def __init__(self, cmts):
    self.commits = cmts
    # todo: ignore certain file formats?
    self.changes = Changes(*[compute_stats(attr, cmts)
      for attr in ('insertions', 'deletions')])
    stdlimits = [1.96, 2.3263]
    def significant(stdlimit):
      def _significant(commit, attr):
        stats = getattr(self.changes, attr)
        xx = getattr(commit, attr)
        var = abs(xx - stats.mean)
        return var < stats.std * stdlimit
      return _significant
    self.sig_changes = [(stdlimit, Changes(*[compute_stats(attr, cmts, significant(stdlimit)) for attr in ('insertions', 'deletions')])) for stdlimit in (1.96, 2.3263)]
  def _repr(self): return [self.changes, self.sig_changes]

def author_stats():
  return dict((author, CommitStats(cmts))
              for author, cmts in by_author(commits()).iteritems())

def print_cstats(cstats):
  print 'all changes:'
  print '   ', cstats.changes
  print 'significant changes:'
  for stdlimit, changes in cstats.sig_changes:
    print '  stdev <=', stdlimit
    print '   ', changes

def main(argv):
  all_stats = author_stats()
  if len(argv) == 1:
    print 'all author stats:'
    for author, stats in all_stats.iteritems():
      print
      print author
      print_cstats(stats)
  else:
    author = argv[1]
    print author
    print_cstats(all_stats.get(author, CommitStats(())))

if __name__ == '__main__': main(sys.argv)

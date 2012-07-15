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
from csv import writer
import errno
import math
import os
import string
from subprocess import Popen, PIPE
import sys

class Repr(object):
  def _repr(self): return ()
  def __repr__(self): return '%s(%s)' % (self.__class__.__name__, self._repr())

FileMod = namedtuple('FileMod', 'fname insertions deletions')
def file_mod(line):
  insertions, deletions, fname = line.split('\t')
  if '-' in (insertions, deletions): return None
  return FileMod(fname, int(insertions), int(deletions))

def sum_changes(objs, pred=lambda _: True):
  return [sum(getattr(obj, attr) for obj in objs if pred(obj))
          for attr in ('insertions', 'deletions')]

class Commit(Repr):
  def __init__(self, fields):
    non_fmod_count = 4
    self.time, self.author, self.uid, self.subject = fields[:non_fmod_count]
    self.fmods = filter(None, map(file_mod, fields[non_fmod_count:]))
    self.insertions, self.deletions = sum_changes(self.fmods)
  def _repr(self):
    return [self.time, self.author, self.uid, self.subject,
            self.insertions, self.deletions, int(self.is_merge)]

def commits(branch=None, merges=None, delimeter='BEGINCOMMIT'):
  cmts = []
  fmt = delimeter + '%n%at%n%an%n%H%n%s' # unixtime, author, hash, subject
  merge_choices = [True, False]
  for is_merge in merge_choices:
    cmd = ['git', 'log', '--format='+fmt, '--numstat']
    if is_merge: cmd.append('--merges')
    else: cmd.append('--no-merges')
    if branch is not None: cmd.append(branch)
    proc = Popen(cmd, stdout=PIPE)
    out, _ = proc.communicate()
    blobs = map(string.strip, out.split(delimeter))[1:]
    new_commits = [Commit(filter(None, commit.split('\n'))) for commit in blobs]
    for commit in new_commits: commit.is_merge = is_merge
    cmts.extend(new_commits)
  return cmts

def write_csv(path, cmts):
  csvf = writer(open(path, 'wb'))
  for commit in cmts: csvf.writerow(commit._repr())

def by_author(cmts):
  author_to_commits = defaultdict(list)
  for commit in cmts: author_to_commits[commit.author].append(commit)
  return author_to_commits

def write_author_csvs(dirpath, author_commits=None):
  try: os.makedirs(dirpath)
  except OSError as e:
    if e.errno != errno.EEXIST: raise
  if author_commits is None: author_commits = by_author(commits()).items()
  for author, cmts in author_commits:
    write_csv(os.path.join(dirpath, author + '.csv'), cmts)

Changes = namedtuple('Changes', 'insertions deletions')
Stats = namedtuple('Stats', 'count total mean std')
def compute_stats(attr, cmts, pred=lambda _, __: True):
  xs = [getattr(commit, attr) for commit in cmts if pred(commit, attr)]
  if not xs: return Stats(0, 0, 0, 0)
  count = float(len(xs))
  total = sum(xs)
  mean = total / count
  std = math.sqrt(sum((xx - mean)**2 for xx in xs) / count)
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

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
import string
from subprocess import Popen, PIPE

class Repr(object):
  def _repr(self): return ()
  def __repr__(self): return '%s(%s)' % (self.__class__.__name__, self._repr())

class FileMod(Repr):
  def __init__(self, line):
    insertions, deletions, self.fname = line.split('\t')
    self.insertions = int(insertions)
    self.deletions = int(deletions)
  def _repr(self): return [self.fname, self.insertions, self.deletions]

class Commit(Repr):
  def __init__(self, fields):
    self.time, self.author, self.uid = fields[:3]
    self.fmods = map(FileMod, fields[3:])
    self.insertions, self.deletions = [
      sum(getattr(fmod, attr) for fmod in self.fmods)
        for attr in ('insertions', 'deletions')]
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

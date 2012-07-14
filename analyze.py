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

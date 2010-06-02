import bdb

def cond_inc(o):
  if 'a' not in o['a']:
    o['a'].append('a')
  return o

def wrapped_inc(o):
  return cond_inc(o)

def break_me(b, f):
  fail = b.set_break(f.func_code.co_filename, f.func_code.co_firstlineno + 1)
  if fail:
    raise fail

  return b

class WeaverBdb(bdb.Bdb):
  woven_func = None
  line = 0
  interrupt = 0
  args = None
  kw = None
  last_return_line = 0
  depth = 0

  def __init__(self, woven_func, *args, **kw):
    self.woven_func = woven_func
    self.args = args
    self.kw = kw

  def set_interrupt(self, interrupt):
    self.interrupt = interrupt

  def user_line(self, frame):
    #if self.line <= self.interrupt:
    print "main line %d (%d)" % (self.line, frame.f_lineno)

    if self.line == self.interrupt:
      print "executing secondary: %s" % self.woven_func.func_name
      self.woven_func(*self.args, **self.kw)

    self.line += 1

  def user_call(self, frame, argument_list=None):
    hist = [frame.f_code.co_name]
    prev = frame.f_back

    while prev:
      if hist[-1] == self.main_name:
        break
      if prev.f_code.co_name != hist[-1]:
        hist.append(prev.f_code.co_name)
      prev = prev.f_back

    hist = ' > '.join(reversed(hist))
    print "CALL", dir(frame.f_code)

  def user_return(self, frame, return_value=None):
    self.last_return_line = frame.f_lineno
    print "RETURN", return_value

  def runcall(self, func, *args, **kw):
    self.main_name = func.func_name
    bdb.Bdb.runcall(self, func, *args, **kw)

class Weaver(object):
  loop_count = 0

  before_func = None
  after_func = None

  main_func = None
  main_args = None
  main_kw = None

  secondary_func = None
  secondary_args = None
  secondary_kw = None

  def __init__(self, before=None, after=None):
    self.before_func = before
    self.after_func = after

  def before(self, func):
    """ called before each weave """
    self.before_func = func
    return func

  def after(self, func):
    """ called after each weave with the return value of the weave """
    self.after_func = func
    return func

  def main(self, func, *args, **kw):
    """ this is the main code we will step through """
    self.main_func = func
    self.main_args = args
    self.main_kw = kw

  def secondary(self, func, *args, **kw):
    """ this is the secondary code we will execute at the same time """
    self.secondary_func = func
    self.secondary_args = args
    self.secondary_kw = kw


  def weave(self, breaks_only=False):
    last_return_line = 0

    while last_return_line >= self.loop_count:
      print "LOOP", self.loop_count
      self.before_func()
      runner = WeaverBdb(self.main_func, *self.main_args, **self.main_kw)
      runner.set_interrupt(self.loop_count)
      rv = runner.runcall(self.secondary_func,
                          *self.secondary_args,
                          **self.secondary_kw)
      self.after_func(rv)
      last_return_line = runner.last_return_line
      self.loop_count += 1



def test():
  w = Weaver()
  a = {'a': []}
  @w.before
  def before():
    a['a'] = []


  w.main(wrapped_inc, a)
  w.secondary(wrapped_inc, a)

  @w.after
  def after(rv):
    assert len(rv['a']) == 1

  #b = WovenBdb(wrapped_inc, 2, a)
  ##b = break_me(b, cond_inc)
  #b.set_step()
  ##print b.get_all_breaks()

  #c = b.runcall(wrapped_inc, a)
  #print c

  w.weave()

if __name__ == "__main__":
  test()

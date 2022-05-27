"""Defines the interface we use for logging."""
class Logger:
  def d(self, *args):
    "Logs a message intended for additional debugging-related info only."
    raise NotImplementedError()
    
  def v(self, *args):
    "Logs additional verbose message."
    raise NotImplementedError()
  
  def i(self, *args):
    "Logs a general-purpose info message, the equivalent of `print`."
    raise NotImplementedError()
  
  def w(self, *args):
    "Logs a warning (message)."
    raise NotImplementedError()
  
  def e(self, *args):
    "Logs an error (message)."
    raise NotImplementedError()

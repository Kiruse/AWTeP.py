from .source_reader import SourceReader, StateError
import pytest

def test_construct():
  reader = SourceReader('abc')
  assert reader.source == 'abc'
  assert reader.file == ''
  assert reader.offset == 0
  assert reader.line == 1
  assert reader.column == 0
  assert reader.is_line_start == True

def test_next():
  reader = SourceReader('abcdefg')
  assert reader.next() == 'a'
  assert reader.next() == 'b'
  assert reader.next(2) == 'cd'
  assert str(reader) == 'efg'

def test_consume():
  reader = SourceReader('abc')
  assert reader.consume('a')
  assert reader.consume('b')
  assert reader.consume('c')
  
  assert reader.consume('d') == False
  with pytest.raises(EOFError):
    reader.consume('d', no_eof=True)

def test_peek():
  reader = SourceReader('abc')
  assert reader.peek() == 'a'
  assert reader.peek(2) == 'ab'
  assert reader.peek(3) == 'abc'
  
  with pytest.raises(EOFError):
    reader.peek(4)

def test_peeks():
  reader = SourceReader('abc')
  assert reader.peeks('a')
  assert reader.peeks('ab')
  assert reader.peeks('abc')
  
  assert reader.peeks('A', case_sensitive=False)
  assert reader.peeks('Ab', case_sensitive=False)
  assert reader.peeks('AbC', case_sensitive=False)
  
  assert not reader.peeks('cba')
  
  with pytest.raises(EOFError):
    reader.peeks('abcd')

def test_skip():
  reader = SourceReader('abc')
  
  reader.skip()
  assert reader.offset == 1
  
  reader.skip(2)
  assert reader.offset == 3
  
  with pytest.raises(EOFError):
    reader.skip(4)

def test_consume_until():
  reader = SourceReader('abc')
  assert reader.consume_until('a') == ''
  assert reader.consume_until('c') == 'ab'
  
  reader = SourceReader('foobar abc')
  assert reader.consume_until(lambda r: r.peek().isspace()) == 'foobar'
  
  reader = SourceReader('foobar abc')
  assert reader.consume_until(['abc']) == 'foobar '
  
  reader = SourceReader('foobar abc123')
  assert reader.consume_until(lambda r: not len(r)) == 'foobar abc123'

def test_copy():
  reader = SourceReader('hello, world')
  reader.consume('hello', no_eof=False)
  
  copy = reader.copy()
  assert copy.source == 'hello, world'
  assert copy.file == ''
  assert copy.offset == 5
  assert copy.line == 1
  assert copy.column == 5
  assert copy.is_line_start == False
  
  reader.next()
  assert copy.offset == 5
  assert reader.offset == 6

def test_is_line_start():
  reader = SourceReader('  \t foo\n\n - bar')
  assert reader.is_line_start == True
  
  reader.consume_until(['foo'])
  assert reader.is_line_start == True
  reader.consume('foo')
  assert reader.is_line_start == False
  
  reader.consume_until('\n')
  assert reader.is_line_start == False
  reader.consume('\n\n')
  assert reader.is_line_start == True
  
  reader.consume_until(['bar'])
  assert reader.is_line_start == False

def test_indexing():
  reader = SourceReader('abc')
  assert reader[0] == 'a'
  assert reader[:3] == 'abc'
  
  reader.next()
  assert reader[0] == 'b'
  assert reader[:3] == 'bc'
  
  reader.next()
  assert reader[0] == 'c'
  assert reader[:3] == 'c'

def test_consumer():
  reader = SourceReader('foo bar baz')
  with pytest.raises(StateError):
    with reader.consumer() as consumer:
      reader.consume('foo ')
      assert consumer != reader
      assert consumer.offset == 0
  
  reader = SourceReader('foo bar baz')
  with reader.consumer() as consumer:
    consumer.consume('foo ')
  assert reader.offset == 4
  
  reader = SourceReader('foo bar baz')
  with reader.consumer() as consumer:
    consumer.consume('foo ')
    assert consumer.offset == 4
    consumer.revert()
  assert reader.offset == 0

# jsonredis
# https://github.com/NoyaInRain/micro/blob/master/jsonredis.py
# part of Micro
# released into the public domain

"""Extended :class:`Redis` client for convinient use with JSON objects.

Also includes :class:`JSONRedisMapping`, an utility map interface for JSON objects.

.. data:: ExpectFunc

   Function of the form `expect(obj: T) -> U` which asserts that an object *obj* is of a certain
   type *U* and raises a :exc:`TypeError` if not.
"""

import json
import sys
from typing import (Callable, Dict, Generic, Iterator, List, Mapping, Optional, Sequence, Set,
                    Tuple, Type, TypeVar, Union, cast, overload)
from weakref import WeakValueDictionary

from redis import StrictRedis
from redis.exceptions import ResponseError

T = TypeVar('T')
U = TypeVar('U')

ExpectFunc = Callable[[T], U]

class JSONRedis(Generic[T]):
    """Extended :class:`Redis` client for convenient use with JSON objects.

    Objects are stored as JSON-encoded strings in the Redis database and en-/decoding is handled
    transparently.

    The translation from an arbitrary object to a JSON-serializable form is carried out by a given
    ``encode(object)`` function. A JSON-serializable object is one that only cosists of the types
    given in https://docs.python.org/3/library/json.html#py-to-json-table . *encode* is passed as
    *default* argument to :func:`json.dumps()`.

    The reverse translation is done by a given ``decode(json)`` function. *decode* is passed as
    *object_hook* argument to :func:`json.loads()`.

    When *caching* is enabled, objects loaded from the Redis database are cached and subsequently
    retrieved from the cache. An object stays in the cache as long as there is a reference to it and
    it is automatically removed when the Python interpreter destroys it. Thus, it is guaranteed that
    getting the same key multiple times will yield the identical object.

    .. attribute:: r

       Underlying :class:`Redis` client.

    .. attribute:: encode

       Function to encode an object to a JSON-serializable form.

    .. attribute:: decode

       Function to decode an object from a JSON-serializable form.

    .. attribute:: caching

        Switch to enable / disable object caching.
    """

    def __init__(
            self, r: StrictRedis, encode: Callable[[T], Dict[str, object]] = None,
            decode: Callable[[Dict[str, object]], Union[T, Dict[str, object]]] = None,
            caching: bool = True) -> None:
        self.r = r
        self.encode = encode
        self.decode = decode
        self.caching = caching
        self._cache = WeakValueDictionary() # type: WeakValueDictionary[str, T]

    @overload
    def oget(self, key: str, *, default: None = None, expect: None = None) -> Optional[T]:
        # pylint: disable=function-redefined,missing-docstring; overload
        pass
    @overload
    def oget(self, key: str, *, default: Union[T, Type[Exception]], expect: None = None) -> T:
        # pylint: disable=function-redefined,missing-docstring; overload
        pass
    @overload
    def oget(self, key: str, *, default: None = None, expect: ExpectFunc[T, U]) -> Optional[U]:
        # pylint: disable=function-redefined,missing-docstring; overload
        pass
    @overload
    def oget(self, key: str, *, default: Union[T, Type[Exception]], expect: ExpectFunc[T, U]) -> U:
        # pylint: disable=function-redefined,missing-docstring; overload
        pass
    def oget(self, key: str, default: Union[T, Type[Exception]] = None,
             expect: ExpectFunc[T, U] = None) -> Union[Optional[T], T, U, Optional[U]]:
        """Return the object at *key*.

        If *key* does not exist, *default* is returned. If *default* is an :exc:`Exception`, it is
        raised instead. The object type can be narrowed with *expect*.
        """
        # pylint: disable=function-redefined,missing-docstring; overload
        object = self._cache.get(key) if self.caching else None
        if object is None:
            value = cast(Optional[bytes], self.get(key))
            if value is not None:
                if not value.startswith(b'{'):
                    raise ResponseError()
                try:
                    # loads() actually returns Union[T, Dict[str, object]], but as T may be dict
                    # there is no way to eliminate it here
                    object = cast(T, json.loads(value.decode(), object_hook=self.decode))
                except ValueError:
                    raise ResponseError()
                if self.caching:
                    self._cache[key] = object
        if object is None:
            if isinstance(default, type) and issubclass(default, Exception): # type: ignore
                raise cast(Exception, default(key))
            object = cast(Optional[T], default)
        return expect(object) if expect and object is not None else object

    def oset(self, key: str, object: T) -> None:
        """Set *key* to hold *object*."""
        if self.caching:
            self._cache[key] = object
        self.set(key, json.dumps(object, default=self.encode))

    @overload
    def omget(self, keys: Sequence[str], *, default: None = None,
              expect: None = None) -> List[Optional[T]]:
        # pylint: disable=function-redefined,missing-docstring; overload
        pass
    @overload
    def omget(self, keys: Sequence[str], *, default: Union[T, Type[Exception]],
              expect: None = None) -> List[T]:
        # pylint: disable=function-redefined,missing-docstring; overload
        pass
    @overload
    def omget(self, keys: Sequence[str], *, default: None = None,
              expect: ExpectFunc[T, U]) -> List[Optional[U]]:
        # pylint: disable=function-redefined,missing-docstring; overload
        pass
    @overload
    def omget(self, keys: Sequence[str], *, default: Union[T, Type[Exception]],
              expect: ExpectFunc[T, U]) -> List[U]:
        # pylint: disable=function-redefined,missing-docstring; overload
        pass
    def omget(
            self, keys: Sequence[str], default: Union[T, Type[Exception]] = None,
            expect: ExpectFunc[T, U] = None
        ) -> Union[List[Optional[T]], List[T], List[Optional[U]], List[U]]:
        """Return a list of objects for the given *keys*.

        *default* and *expect* correspond to the arguments of :meth:`oget`."""
        # pylint: disable=function-redefined,missing-docstring; overload
        # NOTE: Not atomic at the moment
        objects = [self.oget(k, default=default, expect=expect) for k in keys]
        return cast(Union[List[Optional[T]], List[T], List[Optional[U]], List[U]], objects)

    def omset(self, mapping: Mapping[str, T]) -> None:
        """Set each key in *mapping* to its corresponding object."""
        # NOTE: Not atomic at the moment
        for key, object in mapping.items():
            self.oset(key, object)

    def __getattr__(self, name):
        # proxy
        return getattr(self.r, name)

class RedisSequence(Sequence[bytes]):
    """Read-Only sequence interface for Redis collections.

    .. attribute:: key

       Key of the Redis collection.

    .. attribute:: r

       Underlying Redis client.
    """

    def __init__(self, key: str, r: StrictRedis) -> None:
        self.key = key
        self.r = r

class RedisList(RedisSequence):
    """Read-Only sequence interface for Redis lists.

    Redis operations:

    * index(): 1 full query
    * count(): 1 full query
    * len(l): 1
    * l[k]: 1
    * iter(l): 1 full query
    * k in l: 1 full query
    """

    def index(self, x: bytes, start: int = 0, stop: int = sys.maxsize) -> int:
        # pylint: disable=missing-docstring; inherited
        # Optimized
        return self[:].index(x, start, stop)

    def __len__(self) -> int:
        return self.r.llen(self.key)

    @overload
    def __getitem__(self, key: int) -> bytes:
        # pylint: disable=function-redefined,missing-docstring; overload
        pass
    @overload
    def __getitem__(self, key: slice) -> List[bytes]:
        # pylint: disable=function-redefined,missing-docstring; overload
        pass
    def __getitem__(self, key: Union[int, slice]) -> Union[bytes, List[bytes]]:
        # pylint: disable=function-redefined,missing-docstring; overload
        if isinstance(key, slice):
            if key.step:
                raise NotImplementedError()
            return self.r.lrange(self.key, *redis_range(key))
        id = self.r.lindex(self.key, key)
        if not id:
            raise IndexError()
        return id

    def __iter__(self) -> Iterator[bytes]:
        # Optimized and used by count() and k in l
        return iter(self[:])

class RedisSortedSet(RedisSequence, Set[bytes]):
    """Read-Only set / sequence interface for Redis sorted sets.

    Redis operations:

    * index(): 1
    * count(): 1 full query
    * len(s): 1
    * s[k]: 1
    * iter(s): 1 full query
    * k in s: 1
    """

    def index(self, x: bytes, start: int = 0, stop: int = sys.maxsize) -> int:
        # pylint: disable=missing-docstring; inherited
        # Optimized
        if start < 0 or stop < 0:
            raise NotImplementedError()
        rank = self.r.zrank(self.key, x)
        if rank is None or not start <= rank < stop:
            raise ValueError()
        return rank

    def __len__(self) -> int:
        return self.r.zcard(self.key)

    @overload
    def __getitem__(self, key: int) -> bytes:
        # pylint: disable=function-redefined,missing-docstring; overload
        pass
    @overload
    def __getitem__(self, key: slice) -> List[bytes]:
        # pylint: disable=function-redefined,missing-docstring; overload
        pass
    def __getitem__(self, key: Union[int, slice]) -> Union[bytes, List[bytes]]:
        # pylint: disable=function-redefined,missing-docstring; overload
        if isinstance(key, slice):
            if key.step:
                raise NotImplementedError()
            return self.r.zrange(self.key, *redis_range(key))
        # Raises IndexError for empty range
        return self.r.zrange(self.key, key, key)[0]

    def __iter__(self) -> Iterator[bytes]:
        # Optimized and used by count()
        return iter(self[:])

    def __contains__(self, item: object) -> bool:
        # Optimized
        return isinstance(item, bytes) and self.r.zscore(self.key, item) is not None

class JSONRedisSequence(Sequence[T]):
    """Read-Only list interface for JSON objects stored in Redis.

    .. attribute:: r

       Underlying :class:`JSONRedis` client.

    .. attribute:: list_key

       Key of the Redis list that tracks the (keys of the) objects that the sequence contains.

    .. attribute:: pre

       Function of the form *pre()*, which is called before an object is retrieved from the
       database. May be ``None``.
    """

    def __init__(self, r: JSONRedis[T], list_key: str, pre: Callable[[], None] = None) -> None:
        self.r = r
        self.list_key = list_key
        self.pre = pre
        self._ids = RedisList(self.list_key, self.r.r)

    @overload
    def __getitem__(self, key: int) -> T:
        # pylint: disable=function-redefined,missing-docstring; overload
        pass
    @overload
    def __getitem__(self, key: slice) -> List[T]:
        # pylint: disable=function-redefined,missing-docstring; overload
        pass
    def __getitem__(self, key: Union[int, slice]) -> Union[T, List[T]]:
        # pylint: disable=function-redefined,missing-docstring; overload
        if self.pre:
            self.pre()
        if isinstance(key, slice):
            return self.r.omget([id.decode() for id in self._ids[key]], default=ReferenceError)
        return self.r.oget(self._ids[key].decode(), default=ReferenceError)

    def __len__(self) -> int:
        return len(self._ids)

class JSONRedisMapping(Generic[T, U], Mapping[str, T]):
    """Simple, read-only map interface for JSON objects stored in Redis.

    Which items the map contains is determined by the Redis list at *map_key*. Because a list is
    used, the map is ordered, i.e. items are retrieved in the order they were inserted.

    .. attribute:: r

       Underlying :class:`JSONRedis` client.

    .. attribute:: map_key

       Key of the Redis list that tracks the (keys of the) objects that the map contains.

    .. attribute:: expect

       Function narrowing the type of retrieved objects. May be ``None``.
    """

    def __init__(self, r: JSONRedis[U], map_key: str, expect: ExpectFunc[U, T] = None) -> None:
        self.r = r
        self.map_key = map_key
        self.expect = expect
        self._ids = RedisList(self.map_key, self.r.r)

    def __getitem__(self, key: str) -> T:
        if key.encode() not in self._ids:
            raise KeyError()
        return cast(T, self.r.oget(key, default=ReferenceError, expect=self.expect))

    def __iter__(self):
        return (id.decode() for id in self._ids)

    def __len__(self) -> int:
        return len(self._ids)

    def __repr__(self):
        return str(dict(self))

def redis_range(slc: slice) -> Tuple[int, int]:
    """Convert the slice *slc* to Redis range indices."""
    if slc.stop == 0:
        return (1, 0)
    return (0 if slc.start is None else slc.start, -1 if slc.stop is None else slc.stop - 1)

def expect_type2(cls: Type[T]) -> ExpectFunc[Optional[object], Optional[T]]:
    """Return a function which asserts that a given *obj* is an instance of *cls*."""
    def _f(obj: Optional[object]) -> Optional[T]:
        if obj is not None and not isinstance(obj, cls):
            raise TypeError()
        return obj
    return _f

def expect_type(cls: Type[T]) -> ExpectFunc[object, T]:
    """Return a function which asserts that a given *obj* is an instance of *cls*."""
    def _f(obj: object) -> T:
        if not isinstance(obj, cls):
            raise TypeError()
        return obj
    return _f

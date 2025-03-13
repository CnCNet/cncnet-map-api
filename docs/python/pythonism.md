# Python-isms that are used often


## Find if list has *any* matches

This is a common problem. Say you have a list of objects with a `parent_id` attribute.
You want to see if there is at least one object in the list where `parent_id` is `117`.

Python offers a one-liner to do this by abusing the [`next()`](https://docs.python.org/3/library/functions.html#next)
function.

```python
# my_objects is a list of objects with parent_id
found_match = next(iter([x for x in my_list if x.parent_id == 117]))

if found_match:
    ...
```

- `[x for x in my_list if x.parent_id == 117]` is a python list comprehension that
makes a list of all objects matching the `if` statement.
- `iter()` converts the list to an iterator.
- `next()` grabs the next item in the iterator.

This is an alternative to:

```python
found_match: bool = False

for my_object in my_list:
    if my_object.parent_id == 117:
        found_match = True
        break

if found_match:
    ...
```

##### Pros

- One line
- Easy to read for people familiar with this trick

##### Cons

- On massive lists, it is better to do the looping method. This is because the list comprehension creates a second
    list of **all** matches before calling `next()` on it.
- Looping can be more legible for people unfamiliar with the trick.

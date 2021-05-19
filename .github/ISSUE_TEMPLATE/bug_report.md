---
name: Bug report
about: Create a report to help us improve
title: ''
labels: bug
assignees: ''

---

**Describe the bug**
A clear and concise description of what the bug is.

**How to reproduce***

Provide both code and a small JSON document that triggers the problem.

```python
JSON = b"""
[1, 2, 3, 4]
"""
for o in ijson.items(JSON, 'item'):
    raise ValueError('this failed')
```

**Expected behavior**
A clear and concise description of what you expected to happen.

**Execution information:**
 - Python version [e.g. 3.7]
 - ijson version [e.g. 3.1.2]
 - ijson backend (if applies) [e.g. yajl2_c]
 - ijson installation method [e.g. package manager, pip, git sources, conda]
 - OS [e.g. linux]

**Additional context**
Add any other context about the problem here.

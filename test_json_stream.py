from decimal import Decimal
from io import BytesIO
from unittest import TestCase

from ijson.json_stream import StreamObjects

JSON = b'''
{
  "1": {
    "docs=101441.1": [
      {
        "integer": 5551,
        "string": "test text",
        "double": 196.8
      },
      {
        "integer": 3686,
        "string": "test text",
        "double": 196.8
      },
      {
        "integer": null,
        "string": "test text",
        "double": 194.0
      }
    ]
  },
  "3": {
    "docs=101881.1": [
      {
        "integer": 3983,
        "string": "test text 2",
        "double": 359.0
      },
      {
        "integer": 5561,
        "string": "test text 2",
        "double": 359.0
      }
    ],
    "docs=95260.1": [
      {
        "integer": null,
        "string": "test text 3",
        "double": 433.5
      }
    ]
  },
  "4": {
    "docs=108150.1": []
  },
  "5": {}
}
'''

DEEP_1 = (
    (['1'], {
        'docs=101441.1': [{
            'integer': 5551,
            'string': "test text",
            'double': Decimal('196.8')
        }, {
            'integer': 3686,
            'string': "test text",
            'double': Decimal('196.8')
        }, {
            'integer': None,
            'string': "test text",
            'double': Decimal('194.0')
        }]
    }),
    (['3'], {
        'docs=95260.1': [{
            'integer': None,
            'string': "test text 3",
            'double': Decimal('433.5')
        }],
        'docs=101881.1': [{
            'integer': 3983,
            'string': "test text 2",
            'double': Decimal('359.0')
        }, {
            'integer': 5561,
            'string': "test text 2",
            'double': Decimal('359.0')
        }]
    }),
    (['4'], {
        'docs=108150.1': []
    }),
    (['5'], {}),
)
DEEP_2 = (
    (['1', 'docs=101441.1'], [{
        'integer': 5551,
        'string': "test text",
        'double': Decimal('196.8')
    }, {
        'integer': 3686,
        'string': "test text",
        'double': Decimal('196.8')
    }, {
        'integer': None,
        'string': "test text",
        'double': Decimal('194.0')
    }]),
    (['3', 'docs=101881.1'], [{
        'integer': 3983,
        'string': "test text 2",
        'double': Decimal('359.0')
    }, {
        'integer': 5561,
        'string': "test text 2",
        'double': Decimal('359.0')
    }]),
    (['3', 'docs=95260.1'], [{
        'integer': None,
        'string': "test text 3",
        'double': Decimal('433.5')
    }]),
    (['4', 'docs=108150.1'], []),
)
DEEP_3 = (
    (['1', 'docs=101441.1'], {
        'integer': 5551,
        'string': "test text",
        'double': Decimal('196.8')
    }),
    (['1', 'docs=101441.1'], {
        'integer': 3686,
        'string': "test text",
        'double': Decimal('196.8')
    }),
    (['1', 'docs=101441.1'], {
        'integer': None,
        'string': "test text",
        'double': Decimal('194.0')
    }),
    (['3', 'docs=101881.1'], {
        'integer': 3983,
        'string': "test text 2",
        'double': Decimal('359.0')
    }),
    (['3', 'docs=101881.1'], {
        'integer': 5561,
        'string': "test text 2",
        'double': Decimal('359.0')
    }),
    (['3', 'docs=95260.1'], {
        'integer': None,
        'string': "test text 3",
        'double': Decimal('433.5')
    }),
)


class TestStreamObjectBuilder(TestCase):
    def test_stream_objects(self):
        for i, (keys, obj) in enumerate(StreamObjects(BytesIO(JSON), deep=1)):
            self.assertTupleEqual(DEEP_1[i], (keys, obj))

        for i, (keys, obj) in enumerate(StreamObjects(BytesIO(JSON), deep=2)):
            self.assertTupleEqual(DEEP_2[i], (keys, obj))

        for i, (keys, obj) in enumerate(StreamObjects(BytesIO(JSON), deep=3)):
            self.assertTupleEqual(DEEP_3[i], (keys, obj))

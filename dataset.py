import collections
import json
import os

import xarray as xr


FeatureSize = collections.namedtuple(
    'FeatureSize', ['chars', 'fonts', 'fontsizes'])

EmbeddingSize = collections.namedtuple(
    'EmbeddingSize', ['chars', 'fonts', 'fontsizes', 'tokens']
)


class Dataset:
    def __init__(self, data):
        self.data = data
        self.num_examples = len(data['example'])

        self.epochs_completed = 0
        self._index_in_epoch = 0

    @property
    def features(self):
        return self.data.features

    @property
    def tokens(self):
        return self.data.tokens

    def next_batch(self, batch_size):
        start = self._index_in_epoch
        if start + batch_size >= self.num_examples:
            self.epochs_completed += 1
            start = 0
            self._index_in_epoch = 0
            # TODO: Include the examples skipped over at the tail end
        self._index_in_epoch += batch_size
        end = self._index_in_epoch
        batch = self.data[dict(example=slice(start, end))]
        return batch.features.values, batch.tokens.values


class Datasets:
    def __init__(self, train, validate, test, encodings):
        self.train = train
        self.validate = validate
        self.test = test
        self.encodings = encodings
        self.encodings['tokens']['GO'] = len(self.encodings['tokens'])
        self.GO_TOKEN = self.encodings['tokens']['GO']
        input_vocab_sizes = {k: len(v)
                             for k, v in encodings.items()
                             if k != 'tokens'}
        self.feature_vocab_size = FeatureSize(**input_vocab_sizes, fontsizes=20)
        self.token_vocab_size = len(encodings['tokens'])
        self.token_sequence_length = train.tokens.shape[1]


def read_datasets(data_dir, validation_size=10000, test_size=10000):
    EXAMPLE_PDFS = 'examples*.nc'
    ENCODINGS = 'encodings.json'

    example_pdfs = _load_examples_file(os.path.join(data_dir, EXAMPLE_PDFS))
    with open(os.path.join(data_dir, ENCODINGS), 'r') as f:
        encodings = json.load(f)
    if not 0 <= validation_size + test_size <= len(example_pdfs['example']):
        raise ValueError(
            'Holdset set size should be between 0 and {}. Received: {}.'
            .format(len(example_pdfs['example']), validation_size + test_size))
    test = Dataset(example_pdfs[dict(example=slice(None, test_size))])
    validation = Dataset(
        example_pdfs[dict(example=slice(test_size,
                                        test_size + validation_size))])
    train = Dataset(
        example_pdfs[dict(example=slice(validation_size + test_size, None))])
    return Datasets(train, validation, test, encodings)


def _load_examples_file(pattern, chunksize=100):
    return xr.open_mfdataset(pattern, chunks={'example': chunksize},
                             concat_dim='example')
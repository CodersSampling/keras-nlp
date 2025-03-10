# Copyright 2023 The KerasNLP Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

try:
    import tensorflow as tf
except ImportError:
    raise ImportError(
        "To use `keras_nlp`, please install Tensorflow: `pip install tensorflow`. "
        "The TensorFlow package is required for data preprocessing with any backend."
    )

from keras_nlp.backend import ops
from keras_nlp.layers.preprocessing.masked_lm_mask_generator import (
    MaskedLMMaskGenerator,
)
from keras_nlp.tests.test_case import TestCase


class MaskedLMMaskGeneratorTest(TestCase):
    def setUp(self):
        super().setUp()
        self.VOCAB = [
            "[UNK]",
            "[MASK]",
            "[RANDOM]",
            "[CLS]",
            "[SEP]",
            "do",
            "you",
            "like",
            "machine",
            "learning",
            "welcome",
            "to",
            "keras",
        ]
        self.mask_token_id = self.VOCAB.index("[MASK]")
        self.vocabulary_size = len(self.VOCAB)

    def test_mask_ragged(self):
        masked_lm_masker = MaskedLMMaskGenerator(
            vocabulary_size=self.vocabulary_size,
            mask_selection_rate=1,
            mask_selection_length=4,
            mask_token_id=self.mask_token_id,
            mask_token_rate=1,
            random_token_rate=0,
        )
        inputs = [[5, 3, 2], [1, 2, 3, 4]]
        x = masked_lm_masker(inputs)
        self.assertAllEqual(x["token_ids"], [[1, 1, 1], [1, 1, 1, 1]])
        self.assertAllEqual(x["mask_positions"], [[0, 1, 2, 0], [0, 1, 2, 3]])
        self.assertAllEqual(x["mask_ids"], [[5, 3, 2, 0], [1, 2, 3, 4]])

    def test_mask_dense(self):
        masked_lm_masker = MaskedLMMaskGenerator(
            vocabulary_size=self.vocabulary_size,
            mask_selection_rate=1,
            mask_selection_length=4,
            mask_token_id=self.mask_token_id,
            mask_token_rate=1,
            random_token_rate=0,
        )
        inputs = [[5, 3, 2, 4], [1, 2, 3, 4]]
        x = masked_lm_masker(inputs)
        self.assertAllEqual(x["token_ids"], [[1, 1, 1, 1], [1, 1, 1, 1]])
        self.assertAllEqual(x["mask_positions"], [[0, 1, 2, 3], [0, 1, 2, 3]])
        self.assertAllEqual(x["mask_ids"], [[5, 3, 2, 4], [1, 2, 3, 4]])

    def test_unbatched(self):
        masked_lm_masker = MaskedLMMaskGenerator(
            vocabulary_size=self.vocabulary_size,
            mask_selection_rate=1,
            mask_selection_length=4,
            mask_token_id=self.mask_token_id,
            mask_token_rate=1,
            random_token_rate=0,
        )
        inputs = [5, 3, 2, 4]
        x = masked_lm_masker(inputs)
        self.assertAllEqual(x["token_ids"], [1, 1, 1, 1])
        self.assertAllEqual(x["mask_positions"], [0, 1, 2, 3])
        self.assertAllEqual(x["mask_ids"], [5, 3, 2, 4])

    def test_random_replacement(self):
        masked_lm_masker = MaskedLMMaskGenerator(
            vocabulary_size=10_000,
            mask_selection_rate=1,
            mask_selection_length=4,
            mask_token_id=self.mask_token_id,
            mask_token_rate=0,
            random_token_rate=1,
        )
        inputs = [5, 3, 2, 4]
        x = masked_lm_masker(inputs)
        self.assertNotAllEqual(x["token_ids"], [1, 1, 1, 1])
        self.assertAllEqual(x["mask_positions"], [0, 1, 2, 3])
        self.assertAllEqual(x["mask_ids"], [5, 3, 2, 4])

    def test_number_of_masked_position_as_expected(self):
        mask_selection_rate = 0.5
        mask_selection_length = 5
        inputs = [[0, 1, 2], [0, 1, 2, 3, 4, 5], [0, 1, 2, 3, 4]]
        # Cap the number of masked tokens at 0, so we can test if
        # mask_selection_length takes effect.
        mask_selection_length = 0
        masked_lm_masker = MaskedLMMaskGenerator(
            vocabulary_size=self.vocabulary_size,
            mask_selection_rate=mask_selection_rate,
            mask_token_id=self.mask_token_id,
            mask_selection_length=mask_selection_length,
        )
        outputs = masked_lm_masker(inputs)
        self.assertEqual(tf.reduce_sum(outputs["mask_positions"]), 0)

    def test_invalid_mask_token(self):
        with self.assertRaisesRegex(ValueError, "Mask token id should be*"):
            _ = MaskedLMMaskGenerator(
                vocabulary_size=self.vocabulary_size,
                mask_selection_rate=0.5,
                mask_token_id=self.vocabulary_size,
                mask_selection_length=5,
            )

    def test_unselectable_tokens(self):
        unselectable_token_ids = [
            self.vocabulary_size - 1,
            self.vocabulary_size - 2,
        ]
        masked_lm_masker = MaskedLMMaskGenerator(
            vocabulary_size=self.vocabulary_size,
            mask_selection_rate=1,
            mask_token_id=self.mask_token_id,
            mask_selection_length=5,
            unselectable_token_ids=unselectable_token_ids,
            mask_token_rate=1,
            random_token_rate=0,
        )
        outputs = masked_lm_masker([unselectable_token_ids])
        # Verify that no token is masked out.
        self.assertEqual(ops.sum(outputs["mask_weights"]), 0)

    def test_config(self):
        unselectable_token_ids = [
            self.vocabulary_size - 1,
            self.vocabulary_size - 2,
        ]
        masked_lm_masker = MaskedLMMaskGenerator(
            vocabulary_size=self.vocabulary_size,
            mask_selection_rate=0.5,
            mask_token_id=self.mask_token_id,
            mask_selection_length=5,
            unselectable_token_ids=unselectable_token_ids,
        )
        config = masked_lm_masker.get_config()
        expected_config = {
            "vocabulary_size": self.vocabulary_size,
            "unselectable_token_ids": unselectable_token_ids,
        }
        self.assertDictContainsSubset(expected_config, config)

        # Test cloned masked_lm_masker can be run.
        cloned_masked_lm_masker = MaskedLMMaskGenerator.from_config(config)
        inputs = [[5, 3, 2], [1, 2, 3, 4]]
        cloned_masked_lm_masker(inputs)

    def test_with_tf_data(self):
        ds = tf.data.Dataset.from_tensor_slices(
            tf.ones((100, 10), dtype="int32")
        )
        masked_lm_masker = MaskedLMMaskGenerator(
            vocabulary_size=self.vocabulary_size,
            mask_selection_rate=0.5,
            mask_token_id=self.mask_token_id,
            mask_selection_length=5,
        )
        batch_first = ds.batch(8).map(masked_lm_masker)
        batch_second = ds.map(masked_lm_masker).batch(8)
        self.assertEqual(
            batch_first.take(1).get_single_element()["token_ids"].shape,
            batch_second.take(1).get_single_element()["token_ids"].shape,
        )

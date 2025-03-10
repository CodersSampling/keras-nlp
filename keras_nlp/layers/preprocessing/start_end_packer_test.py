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

import keras
import pytest

try:
    import tensorflow as tf
except ImportError:
    raise ImportError(
        "To use `keras_nlp`, please install Tensorflow: `pip install tensorflow`. "
        "The TensorFlow package is required for data preprocessing with any backend."
    )

from keras_nlp.layers.preprocessing.start_end_packer import StartEndPacker
from keras_nlp.tests.test_case import TestCase


class StartEndPackerTest(TestCase):
    def test_dense_input(self):
        input_data = [5, 6, 7]
        start_end_packer = StartEndPacker(sequence_length=5)
        output = start_end_packer(input_data)
        expected_output = [5, 6, 7, 0, 0]
        self.assertAllEqual(output, expected_output)

    @pytest.mark.keras_3_only
    def test_bfloat16_dtype(self):
        # Core Keras has a strange bug where it converts int to floats in
        # ops.convert_to_tensor only with jax and bfloat16.
        floatx = keras.config.floatx()
        keras.config.set_floatx("bfloat16")
        input_data = [5, 6, 7]
        start_end_packer = StartEndPacker(sequence_length=5, dtype="bfloat16")
        output = start_end_packer(input_data)
        self.assertDTypeEqual(output, "int32")
        keras.config.set_floatx(floatx)

    def test_dense_2D_input(self):
        input_data = [[5, 6, 7]]
        start_end_packer = StartEndPacker(sequence_length=5)
        output = start_end_packer(input_data)
        expected_output = [[5, 6, 7, 0, 0]]
        self.assertAllEqual(output, expected_output)

    def test_ragged_input(self):
        input_data = [[5, 6, 7], [8, 9, 10, 11]]
        start_end_packer = StartEndPacker(sequence_length=5)
        output = start_end_packer(input_data)
        expected_output = [[5, 6, 7, 0, 0], [8, 9, 10, 11, 0]]
        self.assertAllEqual(output, expected_output)

    def test_start_end_token(self):
        input_data = [[5, 6, 7], [8, 9, 10, 11]]
        start_end_packer = StartEndPacker(
            sequence_length=6, start_value=1, end_value=2
        )
        output = start_end_packer(input_data)
        expected_output = [[1, 5, 6, 7, 2, 0], [1, 8, 9, 10, 11, 2]]
        self.assertAllEqual(output, expected_output)

    def test_multiple_start_end_tokens(self):
        input_data = [[5, 6, 7], [8, 9, 10, 11, 12, 13]]
        start_end_packer = StartEndPacker(
            sequence_length=8,
            start_value=[1, 2],
            end_value=[3, 4],
            pad_value=0,
        )
        output = start_end_packer(input_data)
        expected_output = [[1, 2, 5, 6, 7, 3, 4, 0], [1, 2, 8, 9, 10, 11, 3, 4]]
        self.assertAllEqual(output, expected_output)

    def test_start_end_padding_value(self):
        input_data = [[5, 6, 7], [8, 9, 10, 11]]
        start_end_packer = StartEndPacker(
            sequence_length=7, start_value=1, end_value=2, pad_value=3
        )
        output = start_end_packer(input_data)
        expected_output = [[1, 5, 6, 7, 2, 3, 3], [1, 8, 9, 10, 11, 2, 3]]
        self.assertAllEqual(output, expected_output)

    def test_end_token_value_during_truncation(self):
        input_data = [[5, 6], [8, 9, 10, 11, 12, 13]]
        start_end_packer = StartEndPacker(
            sequence_length=5, start_value=1, end_value=2, pad_value=0
        )
        output = start_end_packer(input_data)
        expected_output = [[1, 5, 6, 2, 0], [1, 8, 9, 10, 2]]
        self.assertAllEqual(output, expected_output)

    def test_string_input(self):
        input_data = [["KerasNLP", "is", "awesome"], ["amazing"]]
        start_end_packer = StartEndPacker(
            sequence_length=5,
            start_value="[START]",
            end_value="[END]",
            pad_value="[PAD]",
        )
        output = start_end_packer(input_data)
        expected_output = [
            ["[START]", "KerasNLP", "is", "awesome", "[END]"],
            ["[START]", "amazing", "[END]", "[PAD]", "[PAD]"],
        ]
        self.assertAllEqual(output, expected_output)

    def test_string_input_with_multiple_special_values(self):
        input_data = [["KerasNLP", "is", "awesome"], ["amazing"]]
        start_end_packer = StartEndPacker(
            sequence_length=6,
            start_value=["[END]", "[START]"],
            end_value="[END]",
            pad_value="[PAD]",
        )
        output = start_end_packer(input_data)
        expected_output = [
            ["[END]", "[START]", "KerasNLP", "is", "awesome", "[END]"],
            ["[END]", "[START]", "amazing", "[END]", "[PAD]", "[PAD]"],
        ]
        self.assertAllEqual(output, expected_output)

    def test_special_token_dtype_error(self):
        with self.assertRaises(ValueError):
            StartEndPacker(sequence_length=5, start_value=1.0)

    def test_batch(self):
        start_end_packer = StartEndPacker(
            sequence_length=7, start_value=1, end_value=2, pad_value=3
        )

        ds = tf.data.Dataset.from_tensor_slices(
            tf.ragged.constant([[5, 6, 7], [8, 9, 10, 11]])
        )
        ds = ds.batch(2).map(start_end_packer)
        output = ds.take(1).get_single_element()

        exp_output = [[1, 5, 6, 7, 2, 3, 3], [1, 8, 9, 10, 11, 2, 3]]
        self.assertAllEqual(output, exp_output)

    def test_call_overrides(self):
        x = [5, 6, 7]
        packer = StartEndPacker(start_value=1, end_value=2, sequence_length=4)
        self.assertAllEqual(packer(x), [1, 5, 6, 2])
        self.assertAllEqual(packer(x, add_start_value=False), [5, 6, 7, 2])
        self.assertAllEqual(packer(x, add_end_value=False), [1, 5, 6, 7])
        self.assertAllEqual(packer(x, sequence_length=2), [1, 2])

    def test_get_config(self):
        start_end_packer = StartEndPacker(
            sequence_length=512,
            start_value=10,
            end_value=20,
            pad_value=100,
            name="start_end_packer_test",
        )

        config = start_end_packer.get_config()
        expected_config_subset = {
            "sequence_length": 512,
            "start_value": 10,
            "end_value": 20,
            "pad_value": 100,
        }

        self.assertEqual(config, {**config, **expected_config_subset})

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

import numpy as np
import pytest

try:
    import tensorflow as tf
except ImportError:
    raise ImportError(
        "To use `keras_nlp`, please install Tensorflow: `pip install tensorflow`. "
        "The TensorFlow package is required for data preprocessing with any backend."
    )
from absl.testing import parameterized

from keras_nlp.backend import ops
from keras_nlp.samplers.top_p_sampler import TopPSampler
from keras_nlp.tests.test_case import TestCase


class TopPSamplerTest(TestCase):
    def setUp(self):
        super().setUp()
        # Use a simple alphabet of lowercase characters to [0, 26).
        self.int_lookup = {i: chr(i + ord("a")) for i in range(26)}
        self.char_lookup = {v: k for k, v in self.int_lookup.items()}
        self.batch_size = 1
        self.length = 12
        self.vocab_size = len(self.int_lookup)

        def next(prompt, cache, index):
            # Dummy hidden states.
            hidden_states = ops.ones([self.batch_size, 5])
            # Return a distribution favoring the next char in cache.
            logits = ops.one_hot(cache[:, index], self.vocab_size) * 1e9
            return logits, hidden_states, cache

        self.next = next
        self.sampler = TopPSampler(p=0.1)

    def join_as_string(self, x):
        x = ops.convert_to_numpy(x)
        return ["".join([self.int_lookup[i] for i in s]) for s in x]

    def test_stateless_call(self):
        def next(prompt, cache, index):
            # Dummy hidden states.
            hidden_states = ops.ones([self.batch_size, 5])
            # Return a distribution favoring the first token in the vocab.
            logits = (
                ops.one_hot(
                    ops.zeros(self.batch_size, dtype="int32"),
                    self.vocab_size,
                )
                * 1e9
            )
            return logits, hidden_states, cache

        prompt = ops.full((self.batch_size, self.length), self.char_lookup["z"])
        output = self.sampler(
            next=next,
            prompt=prompt,
            index=5,
        )
        self.assertEqual(self.join_as_string(output), ["zzzzzaaaaaaa"])

    def test_stateful_call(self):
        cache_chars = list("sequentially")
        cache = ops.array([[self.char_lookup[c] for c in cache_chars]])
        prompt = ops.full((self.batch_size, self.length), self.char_lookup["z"])
        output = self.sampler(
            next=self.next,
            prompt=prompt,
            cache=cache,
        )
        self.assertEqual(self.join_as_string(output), ["sequentially"])

    def test_early_stopping(self):
        cache_chars = list("sequentially")
        cache = ops.array([[self.char_lookup[c] for c in cache_chars]])
        prompt = ops.full((self.batch_size, self.length), self.char_lookup["z"])
        output = self.sampler(
            next=self.next,
            prompt=prompt,
            cache=cache,
            stop_token_ids=[self.char_lookup["t"]],
        )
        self.assertEqual(self.join_as_string(output), ["sequentzzzzz"])

    def test_only_sample_from_top_k_tokens(self):
        def next(prompt, cache, index):
            # Dummy hidden states.
            hidden_states = ops.ones([self.batch_size, 5])
            # Return a distribution where each id is progressively less likely.
            logits = ops.arange(self.vocab_size, 0, -1, dtype="float32")
            logits = ops.repeat(logits[None, :], self.batch_size, axis=0)
            return logits, hidden_states, cache

        prompt = ops.full((self.batch_size, self.length), self.char_lookup["z"])
        output = TopPSampler(p=1, k=5)(
            next=next,
            prompt=prompt,
            index=5,
        )
        generated_str = self.join_as_string(output[:, 5:])[0]
        token_set = set(generated_str)
        self.assertContainsSubset(token_set, set("abcde"))

    def test_outputs_in_top_p(self):
        def next(prompt, cache, index):
            # Dummy hidden states.
            hidden_states = ops.ones([self.batch_size, 5])
            logits = np.zeros((self.batch_size, self.vocab_size))
            logits[:, :3] = 1.0
            return ops.array(logits), hidden_states, cache

        prompt = ops.full((self.batch_size, self.length), self.char_lookup["z"])
        output = TopPSampler(p=(2.0 / self.vocab_size))(
            next=next,
            prompt=prompt,
        )
        output_ids = set(ops.convert_to_numpy(output[0]))
        self.assertContainsSubset(output_ids, range(3))

    def test_temperature(self):
        def next(prompt, cache, index):
            # Dummy hidden states.
            hidden_states = ops.ones([self.batch_size, 5])
            logits = ops.arange(self.vocab_size, 0, -1, dtype="float32")
            logits = ops.reshape(logits[None, :], (self.batch_size, -1))
            return ops.array(logits), hidden_states, cache

        prompt = ops.full((self.batch_size, self.length), self.char_lookup["z"])

        output = TopPSampler(p=0.5, temperature=1e-9)(
            next=next,
            prompt=prompt,
        )
        self.assertAllEqual(output, ops.zeros_like(output))

    @parameterized.named_parameters(
        ("jit_compile_false", False), ("jit_compile_true", True)
    )
    @pytest.mark.tf_only
    def test_compilation(self, jit_compile):
        cache_chars = list("sequentially")
        cache = ops.array([[self.char_lookup[c] for c in cache_chars]])
        prompt = ops.full((self.batch_size, self.length), self.char_lookup["z"])

        @tf.function(jit_compile=jit_compile)
        def generate(prompt, cache):
            return self.sampler(self.next, prompt=prompt, cache=cache)

        output = generate(prompt, cache)
        self.assertEqual(self.join_as_string(output), ["sequentially"])

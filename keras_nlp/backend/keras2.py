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

import types

try:
    import tensorflow as tf
except ImportError:
    raise ImportError(
        "To use `keras_nlp`, please install Tensorflow: "
        "`pip install tensorflow`. The TensorFlow package is required for "
        "data preprocessing with any backend."
    )

from tensorflow.keras import *  # noqa: F403, F401
from tensorflow.keras import utils

from keras_nlp.backend import config  # noqa: F401

# Shims to handle symbol renames for older `tf.keras` versions.
if not hasattr(tf.keras, "saving"):
    saving = types.SimpleNamespace()
else:
    from tensorflow.keras import saving

if not hasattr(saving, "deserialize_keras_object"):
    saving.deserialize_keras_object = utils.deserialize_keras_object
if not hasattr(saving, "serialize_keras_object"):
    saving.serialize_keras_object = utils.serialize_keras_object
if not hasattr(saving, "register_keras_serializable"):
    saving.register_keras_serializable = utils.register_keras_serializable

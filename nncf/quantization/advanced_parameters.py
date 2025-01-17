# Copyright (c) 2023 Intel Corporation
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#      http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields
from dataclasses import is_dataclass
from enum import Enum
from typing import Any, ClassVar, Dict, Optional, Protocol

from nncf.common.quantization.structs import QuantizationMode
from nncf.common.utils.api_marker import api
from nncf.quantization.range_estimator import AggregatorType
from nncf.quantization.range_estimator import RangeEstimatorParameters
from nncf.quantization.range_estimator import StatisticsType


class OverflowFix(Enum):
    """
    This option controls whether to apply the overflow issue fix for the 8-bit
    quantization.

    8-bit instructions of older Intel CPU generations (based on SSE, AVX-2, and AVX-512
    instruction sets) suffer from the so-called saturation (overflow) issue: in some
    configurations, the output does not fit into an intermediate buffer and has to be
    clamped. This can lead to an accuracy drop on the aforementioned architectures.
    The fix set to use only half a quantization range to avoid overflow for specific
    operations.

    If you are going to infer the quantized model on the architectures with AVX-2, and
    AVX-512 instruction sets, we recommend using FIRST_LAYER option as lower aggressive
    fix of the overflow issue. If you still face significant accuracy drop, try using
    ENABLE, but this may get worse the accuracy.

    :param ENABLE: All weights of all types of Convolutions and MatMul operations
        are be quantized using a half of the 8-bit quantization range.
    :param FIRST_LAYER: Weights of the first Convolutions of each model inputs
        are quantized using a half of the 8-bit quantization range.
    :param DISABLE: All weights are quantized using the full 8-bit quantization range.
    """

    ENABLE = "enable"
    FIRST_LAYER = "first_layer_only"
    DISABLE = "disable"


@dataclass
class QuantizationParameters:
    """
    Contains quantization parameters for weights or activations.

    :param num_bits: The number of bits to use for quantization.
    :param mode: The quantization mode to use, such as 'symmetric', 'asymmetric', etc.
    :param signedness_to_force: Whether to force the weights or activations to be
        signed (True), unsigned (False)
    :param per_channel: True if per-channel quantization is used, and False if
        per-tensor quantization is used.
    :param narrow_range: Whether to use a narrow quantization range. If narrow range is
        False then the input will be quantized into quantizaiton range
        [0; 2^num_bits - 1] for unsigned qunatization and
        [-2^(num_bits - 1); 2^(num_bits - 1) - 1] for signed quantization, otherwise
        [0; 2^num_bits - 2] for unsigned qunatization and
        [-2^(num_bits - 1) + 1; 2^(num_bits - 1) - 1] for signed quantization
        when it is True.
    """

    num_bits: Optional[int] = None
    mode: Optional[QuantizationMode] = None
    signedness_to_force: Optional[bool] = None
    per_channel: Optional[bool] = None
    narrow_range: Optional[bool] = None


@dataclass
class AdvancedBiasCorrectionParameters:
    """
    Contains advanced parameters for fine-tuning bias correction algorithm.

    :param apply_for_all_nodes: Whether to apply the correction to all nodes in the
        model, or only to nodes that have a bias.
    :param threshold: The threshold value determines the maximum bias correction value.
        The bias correction are skipped If the value is higher than threshold.
    """

    apply_for_all_nodes: bool = False
    threshold: Optional[float] = None


@api()
@dataclass
class AdvancedQuantizationParameters:
    """
    Contains advanced parameters for fine-tuning qunatization algorithm.

    :param overflow_fix: This option controls whether to apply the overflow issue fix
        for the 8-bit quantization, defaults to OverflowFix.FIRST_LAYER.
    :param quantize_outputs: Whether to insert additional quantizers right before each
        of the model outputs.
    :param inplace_statistics: Defines wheather to calculate quantizers statistics by
        backend graph operations or by default Python implementation, defaults to True.
    :param disable_bias_correction: Whether to disable the bias correction.
    :param activations_quantization_params: Quantization parameters for activations.
    :param weights_quantization_params: Quantization parameters for weights.
    :param activations_range_estimator_params: Range estimator parameters for
        activations.
    :param weights_range_estimator_params: Range estimator parameters for weights.
    :param bias_correction_params: Advanced bias correction paramters.
    :param backend_params: Backend-specific parameters.
    """

    # General parameters
    overflow_fix: OverflowFix = OverflowFix.FIRST_LAYER
    quantize_outputs: bool = False
    inplace_statistics: bool = True
    disable_bias_correction: bool = False

    # Advanced Quantization parameters
    activations_quantization_params: QuantizationParameters = field(default_factory=QuantizationParameters)
    weights_quantization_params: QuantizationParameters = field(default_factory=QuantizationParameters)

    # Range estimator parameters
    activations_range_estimator_params: RangeEstimatorParameters = field(default_factory=RangeEstimatorParameters)
    weights_range_estimator_params: RangeEstimatorParameters = field(default_factory=RangeEstimatorParameters)

    # Advanced BiasCorrection algorithm parameters
    bias_correction_params: AdvancedBiasCorrectionParameters = field(default_factory=AdvancedBiasCorrectionParameters)

    # backend specific parameters
    backend_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AdvancedAccuracyRestorerParameters:
    """
    Contains advanced parameters for fine-tuning the accuracy restorer algorithm.

    :param max_num_iterations: The maximum number of iterations of the algorithm.
        In other words, the maximum number of layers that may be reverted back to
        floating-point precision. By default, it is limited by the overall number of
        quantized layers.
    :param tune_hyperparams: Whether to tune of quantization parameters as a
        preliminary step before reverting layers back to the floating-point precision.
        It can bring an additional boost in performance and accuracy, at the cost of
        increased overall quantization time. The default value is `False`.
    :param convert_to_mixed_preset: Whether to convert the model to mixed mode if
        the accuracy criteria of the symmetrically quantized model are not satisfied.
        The default value is `False`.
    :param ranking_subset_size: Size of a subset that is used to rank layers by their
        contribution to the accuracy drop.
    """

    max_num_iterations: int = sys.maxsize
    tune_hyperparams: bool = False
    convert_to_mixed_preset: bool = False
    ranking_subset_size: Optional[int] = None


class IsDataclass(Protocol):
    """
    Type hint class for the dataclass
    """

    __dataclass_fields__: ClassVar[Dict]


def changes_asdict(params: IsDataclass) -> Dict[str, Any]:
    """
    Returns non None fields as dict

    :param params: A dataclass instance
    :return: A dict with non None fields
    """
    changes = {}
    for f in fields(params):
        value = getattr(params, f.name)
        if value is not None:
            changes[f.name] = value
    return changes


def convert_to_dict_recursively(params: IsDataclass) -> Dict[str, Any]:
    """
    Converts dataclass to dict recursively

    :param params: A dataclass instance
    :return: A dataclass as dict
    """
    if params is None:
        return {}

    result = {}
    for f in fields(params):
        value = getattr(params, f.name)
        if is_dataclass(value):
            result[f.name] = convert_to_dict_recursively(value)
        if isinstance(value, Enum):
            result[f.name] = value.value
        result[f.name] = value

    return result


def convert_quantization_parameters_to_dict(params: QuantizationParameters) -> Dict[str, Any]:
    """
    Converts quantization parameters to the dict in the legacy format

    :param params: Quantization parameters
    :return: Quantization parameters as dict in the legacy format
    """
    result = {}
    if params.num_bits is not None:
        result["bits"] = params.num_bits
    if params.mode is not None:
        result["mode"] = params.mode
    if params.signedness_to_force is not None:
        result["signed"] = params.signedness_to_force
    if params.per_channel is not None:
        result["per_channel"] = params.per_channel
    if params.narrow_range is not None:
        raise RuntimeError("narrow_range parameter is not supported in the legacy format")
    return result


def convert_range_estimator_parameters_to_dict(params: RangeEstimatorParameters) -> Dict[str, Any]:
    """
    Converts range estimator parameters to the dict in the legacy format

    :param params: Range estimator parameters
    :return: range estimator parameters as dict in the legacy format
    """
    if params.min.clipping_value is not None or params.max.clipping_value is not None:
        raise RuntimeError("clipping_value parameter is not supported in the legacy format")

    result = {}
    if (
        params.min.statistics_type == StatisticsType.MIN
        and params.min.aggregator_type == AggregatorType.MIN
        and params.max.statistics_type == StatisticsType.MAX
        and params.max.aggregator_type == AggregatorType.MAX
    ):
        result["type"] = "mixed_min_max"
    elif (
        params.min.statistics_type == StatisticsType.MIN
        and params.min.aggregator_type == AggregatorType.MEAN
        and params.max.statistics_type == StatisticsType.MAX
        and params.max.aggregator_type == AggregatorType.MEAN
    ):
        result["type"] = "mean_min_max"
    elif (
        params.min.statistics_type == StatisticsType.QUANTILE
        and params.min.aggregator_type == AggregatorType.MEAN
        and params.max.statistics_type == StatisticsType.QUANTILE
        and params.max.aggregator_type == AggregatorType.MEAN
    ):
        result["type"] = "mean_percentile"
        result["params"] = {
            "min_percentile": 1 - params.min.quantile_outlier_prob,
            "max_percentile": 1 - params.max.quantile_outlier_prob,
        }
    else:
        raise RuntimeError("The following range estimator parameters are not supported: " f"{str(params)}")

    return result


def convert_advanced_parameters_to_dict(params: AdvancedQuantizationParameters) -> Dict[str, Any]:
    """
    Converts advanced parameters to the dict in the legacy format

    :param params: Advanced quantization parameters
    :return: advanced quantization parameters as dict in the legacy format
    """
    result = {
        "overflow_fix": params.overflow_fix.value,
        "quantize_outputs": params.quantize_outputs,
    }

    if params.disable_bias_correction:
        result["batchnorm_adaptation"] = {"num_bn_adaptation_samples": 0}

    activations_config = convert_quantization_parameters_to_dict(params.activations_quantization_params)
    if activations_config:
        result["activations"] = activations_config

    weights_config = convert_quantization_parameters_to_dict(params.weights_quantization_params)
    if weights_config:
        result["weights"] = weights_config

    activations_init_range_config = convert_range_estimator_parameters_to_dict(
        params.activations_range_estimator_params
    )
    weights_init_range_config = convert_range_estimator_parameters_to_dict(params.weigths_range_estimator_params)
    if activations_init_range_config or weights_init_range_config:
        activations_init_range_config["target_quantizer_group"] = "activations"
        activations_init_range_config["target_scopes"] = "{re}.*"
        weights_init_range_config["target_quantizer_group"] = "weights"
        weights_init_range_config["target_scopes"] = "{re}.*"

        result["initializer"]["range"] = [activations_init_range_config, weights_init_range_config]

    if params.bias_correction_params.apply_for_all_nodes:
        raise RuntimeError(
            "apply_for_all_nodes parameter of the BiasCorrection algorithm is not supported in the legacy format"
        )

    if params.bias_correction_params.threshold is not None:
        raise RuntimeError("threshold parameter of the BiasCorrection algorithm is not supported in the legacy format")

    return result

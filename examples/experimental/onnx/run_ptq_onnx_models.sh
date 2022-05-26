#!/usr/bin/env bash

SCRIPT_DIR=$(dirname "$0")

if [ $# -ne 4 ]; then
    echo "illegal number of parameters"
    echo "E.g. ./run_ptq_onnx_models.sh classification <MODEL_DIR> <OUTPUT_DIR> <NUMBER_OF_SAMPLES>"
    exit 2
fi

case $1 in
    classification|det_and_seg)
        CONFIGS_DIR=${SCRIPT_DIR}/$1/onnx_models_configs;
        echo "CONFIGS_DIR=$CONFIGS_DIR"
        ;;
    *)
        echo "You should choose classification or det_and_seg. E.g. ./run_ptq_onnx_models.sh classification ..."
        exit 2
        ;;
esac

MODEL_DIR=$2
OUTPUT_DIR=$3
NUMBER_OF_SAMPLES=$4

echo "MODEL_DIR=$MODEL_DIR"
echo "OUTPUT_DIR=$OUTPUT_DIR"
echo "NUMBER_OF_SAMPLES=$NUMBER_OF_SAMPLES"

for config in `ls $CONFIGS_DIR`; do
    model_name=${config%.*}
    echo $model_name

    # Post-training quantization
    python $SCRIPT_DIR/run_ptq.py       \
        -c $CONFIGS_DIR/$config         \
        -m $MODEL_DIR/$model_name.onnx  \
        -o $OUTPUT_DIR                  \
        -ss $NUMBER_OF_SAMPLES

    # Accuracy check for the original model
    accuracy_check  \
        -c $CONFIGS_DIR/$config                     \
        -ss $NUMBER_OF_SAMPLES                      \
        -m $MODEL_DIR/$model_name.onnx              \
        --csv_result $OUTPUT_DIR/original_accuracy.csv

    # Accuracy check for the quantized model
    accuracy_check  \
        -c $CONFIGS_DIR/$config                     \
        -ss $NUMBER_OF_SAMPLES                      \
        -m $OUTPUT_DIR/$model_name-quantized.onnx   \
        --csv_result $OUTPUT_DIR/quantize_accuracy.csv

    # Benchmark the original model
    mkdir -p $OUTPUT_DIR/$model_name/original

    benchmark_app -m $MODEL_DIR/$model_name.onnx        \
        --batch_size 1 --time 10                        \
        -report_type no_counters                        \
        -report_folder $OUTPUT_DIR/$model_name/original

    # Benchmark the quantized model
    mkdir -p $OUTPUT_DIR/$model_name/quantized

    benchmark_app -m $OUTPUT_DIR/$model_name-quantized.onnx \
        --batch_size 1 --time 10                            \
        -report_type no_counters                            \
        -report_folder $OUTPUT_DIR/$model_name/quantized
done

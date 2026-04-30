MODEL_LIST=(yolov11s yolo26n yolo26s)
INPUT_PATH="/home/drone1/Desktop/Rpi5Tests/visible.mp4"
STREAMS_COUNT=(1 2 4 6)
RUNS=3

for model in "${MODEL_LIST[@]}"; do
    MODEL_PATH="/home/drone1/Desktop/Rpi5Tests/YOLO_test/models/$model.hef"
    LATENCY_RESULTS_FILE="results_latency_${model}.csv"
    for stream in "${STREAMS_COUNT[@]}"; do
        INPUT=$(printf "%s " $(yes "$INPUT_PATH" | head -n "$stream"))
        echo "Start test for $model with $stream streams"
        for (( run = 1; run <= $RUNS; run++ )); do
            echo "RUN #$run"
            python3 new_measure_latency.py -i $INPUT -m $MODEL_PATH > "temp_log${run}.txt"
            sleep 10
        done
        echo "Test finish. Parsing"
        python3 parse.py -s $stream -o $LATENCY_RESULTS_FILE
    done
done
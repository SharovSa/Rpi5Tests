MODEL_LIST=(yolov10n yolov10s yolov11n yolov11s yolo26n yolo26s)

for model in "${MODEL_LIST[@]}"; do
    ./run_benchmark.sh $model
    echo "FINISH $model TEST"
done
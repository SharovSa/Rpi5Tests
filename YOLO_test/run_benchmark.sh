#!/bin/bash

# Настройки
MODEL=$1

VIDEO_FILE="../long_visible.mp4" # Ваш склеенный длинный файл
HEF_PATH=~/Desktop/Rpi5Tests/YOLO_test/models/$MODEL.hef
SO_PATH="/usr/lib/aarch64-linux-gnu/hailo/tappas/post_processes/libyolo_hailortpp_post.so"
JSON_PATH="./yolov8s.json"
CSV_FILE="fps_results_$MODEL.csv"

# Массивы для тестирования
STREAMS=(1)
RUNS=1

# echo "Streams;Per_Stream_FPS;Total_FPS;Estimated_Latency_ms" > "$CSV_FILE"
echo "Бенчмарк начат. Результаты будут записаны в $CSV_FILE"
echo "--------------------------------------------------------"

for stream_count in "${STREAMS[@]}"; do
    echo "Запуск: $stream_count потока(ов) | Прогон: $run из $RUNS"
    rm -f ./log*.txt
    "./run_streams$stream_count.sh" $HEF_PATH
    wait
    total_avg_fps=0
    result_line=$(grep "Average-fps:" "./log$stream_count.txt" | tail -n 1)
    if [[ -n "$result_line" ]]; then
        total_avg_fps=$(echo "$result_line" | grep -o -E 'Average-fps: [0-9,]+' | cut -d' ' -f2 | tr ',' '.')
    fi
	echo "AVG FPS: $total_avg_fps"
    # Расчет FPS на один поток (среднее арифметическое среди запущенных потоков)
    per_stream_avg=$(awk "BEGIN {print $total_avg_fps / $stream_count}")
    # Расчет задержки (Latency в миллисекундах)
    # Формула: 1000 мс / FPS_одного_потока
    latency_ms=$(awk "BEGIN {printf \"%.2f\", 1000 / $per_stream_avg}")
    # Форматируем для красоты в консоль
    formatted_per_stream=$(awk "BEGIN {printf \"%.2f\", $per_stream_avg}")
    formatted_total=$(awk "BEGIN {printf \"%.2f\", $total_avg_fps}")

    echo "$stream_count;$formatted_per_stream;$formatted_total;$latency_ms" >> "$CSV_FILE"
    echo "Результат: 1 поток = $formatted_per_stream FPS | Задержка = $latency_ms мс"
    echo "Охлаждение 30 секунд..."
    sleep 30
    echo "--------------------------------------------------------"
done

echo "Бенчмарк успешно завершен! Откройте файл $CSV_FILE"

import sys
import time
import gi
import psutil
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

Gst.init(None)

TEST_COUNT = 3
VIDEO_FILE = "../long_visible.mp4"
MODEL_PATH = "/home/drone/Desktop/YOLO_test/models/yolov10s.hef"
TEST_DURATION_SEC = 45

frame_start_times = {}
latencies = []
cpu_measurements = []

psutil.cpu_percent(interval=None)

# Перехватываем кадр в самом начале Ветки 0
def start_probe(pad, info):
    buf = info.get_buffer()
    if buf and buf.pts != Gst.CLOCK_TIME_NONE:
        frame_start_times[buf.pts] = time.perf_counter()
    return Gst.PadProbeReturn.OK

# Перехватываем кадр на выходе (Hailo сохраняет оригинальный PTS после де-батчинга)
def end_probe(pad, info):
    buf = info.get_buffer()
    if buf and buf.pts != Gst.CLOCK_TIME_NONE and buf.pts in frame_start_times:
        latency_ms = (time.perf_counter() - frame_start_times[buf.pts]) * 1000
        latencies.append(latency_ms)
        if len(latencies) % 10 == 0:
            print(f"[Поток 0] Обработан кадр | Задержка: {latency_ms:.2f} мс")
        del frame_start_times[buf.pts]
    return Gst.PadProbeReturn.OK

def monitor_cpu():
    cpu_usage = psutil.cpu_percent(interval=None)
    cpu_measurements.append(cpu_usage)
    return True

def stop_pipeline():
    print(f"\n[ТАЙМЕР] Время ({TEST_DURATION_SEC} сек) вышло. Принудительный сброс пайплайна (Flush)...")
    
    # 1. Отправляем сигнал FLUSH_START. Он мгновенно разблокирует все ожидающие потоки, очереди и мультиплексоры.
    pipeline.send_event(Gst.Event.new_flush_start())
    
    # 2. Завершаем главный цикл GObject
    loop.quit()
    return False

# --- ОБРАБОТЧИК ОШИБОК (ВЕРНУЛИ КАК БЫЛО) ---
def on_bus_message(bus, message, loop):
    t = message.type
    if t == Gst.MessageType.EOS:
        print("\n[ИНФО] Конец видеопотока.")
        loop.quit()
    elif t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        print(f"\n[КРИТИЧЕСКАЯ ОШИБКА] {err}\n[ДЕТАЛИ] {debug}")
        loop.quit()
    return True

# Ваш единый пайплайн, оптимизированный для замера задержки (без очередей и с имитацией камер)


models = ["yolov8n", "yolov9t", "yolov10n", "yolov11n", "yolo26n",
          "yolov8s", "yolov9s", "yolov10s", "yolov11s", "yolo26s"]
results = {}

for model in models[4:5]:
    MODEL_PATH = "/home/drone/Desktop/YOLO_test/models/" + model + ".hef"
    print("Тест модели ", model)
    pipeline_str = f"""
      filesrc location={VIDEO_FILE} name=source_0 ! decodebin ! identity sync=true ! 
      queue name=start_queue_0 max-size-buffers=1 leaky=downstream ! 
      videoscale n-threads=2 ! videoconvert n-threads=2 qos=false ! 
      video/x-raw, pixel-aspect-ratio=1/1, format=RGB, width=640, height=640 ! 
      hailofilter name=set_src_0 so-path=/usr/lib/aarch64-linux-gnu/hailo/tappas/post_processes/libstream_id_tool.so config-path=src_0 ! 
      queue leaky=no max-size-buffers=1 ! robin.sink_0 
      
      filesrc location={VIDEO_FILE} name=source_1 ! decodebin ! identity sync=true ! 
      queue name=start_queue_1 max-size-buffers=1 leaky=downstream ! 
      videoscale n-threads=2 ! videoconvert n-threads=2 qos=false ! 
      video/x-raw, pixel-aspect-ratio=1/1, format=RGB, width=640, height=640 ! 
      hailofilter name=set_src_1 so-path=/usr/lib/aarch64-linux-gnu/hailo/tappas/post_processes/libstream_id_tool.so config-path=src_1 ! 
      queue leaky=no max-size-buffers=1 ! robin.sink_1 
      
      filesrc location={VIDEO_FILE} name=source_2 ! decodebin ! identity sync=true ! 
      queue name=start_queue_2 max-size-buffers=1 leaky=downstream ! 
      videoscale n-threads=2 ! videoconvert n-threads=2 qos=false ! 
      video/x-raw, pixel-aspect-ratio=1/1, format=RGB, width=640, height=640 ! 
      hailofilter name=set_src_2 so-path=/usr/lib/aarch64-linux-gnu/hailo/tappas/post_processes/libstream_id_tool.so config-path=src_2 ! 
      queue leaky=no max-size-buffers=1 ! robin.sink_2 
      
      filesrc location={VIDEO_FILE} name=source_3 ! decodebin ! identity sync=true ! 
      queue name=start_queue_3 max-size-buffers=1 leaky=downstream ! 
      videoscale n-threads=2 ! videoconvert n-threads=2 qos=false ! 
      video/x-raw, pixel-aspect-ratio=1/1, format=RGB, width=640, height=640 ! 
      hailofilter name=set_src_3 so-path=/usr/lib/aarch64-linux-gnu/hailo/tappas/post_processes/libstream_id_tool.so config-path=src_3 ! 
      queue leaky=no max-size-buffers=1 ! robin.sink_3 
      
      hailoroundrobin mode=1 name=robin ! 
      queue max-size-buffers=1 leaky=downstream ! 
      hailonet hef-path={MODEL_PATH} batch-size=4 vdevice-group-id=SHARED ! 
      queue max-size-buffers=1 leaky=downstream ! 
      hailofilter so-path=/usr/local/hailo/resources/so/libyolo_hailortpp_postprocess.so function-name=filter_letterbox qos=false ! 
      queue name=end_queue max-size-buffers=1 ! 
      fakesink sync=false async=false qos=false
    """

    t_lat = 0
    for k in range(TEST_COUNT):
        print(f"Сборка монолитного пайплайна (2 поток, Batch=2, тест={k+1})...")
        pipeline = Gst.parse_launch(pipeline_str)

        start_element = pipeline.get_by_name("start_queue_0")
        end_element = pipeline.get_by_name("end_queue")

        if not start_element or not end_element:
            print("Ошибка: не удалось найти элементы зондирования!")
            sys.exit(-1)

        start_element.get_static_pad("src").add_probe(Gst.PadProbeType.BUFFER, start_probe)
        end_element.get_static_pad("src").add_probe(Gst.PadProbeType.BUFFER, end_probe)

        loop = GLib.MainLoop()
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", on_bus_message, loop)

        GLib.timeout_add(1000, monitor_cpu)
        GLib.timeout_add_seconds(TEST_DURATION_SEC, stop_pipeline) # Авто-стоп через 30 сек

        print("Запуск... (Подождите 15-20 секунд и нажмите Ctrl+C)")
        ret = pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("Не удалось запустить пайплайн.")
            sys.exit(-1)

        try:
            loop.run()
        except KeyboardInterrupt:
            print("\nОстановка...")
        finally:
            print("\n==================================================")
            print(f"ОТЧЕТ: ЗАПУСК {k + 1}:")
            print("==================================================")
            if latencies:
                valid_latencies = latencies[5:] if len(latencies) > 5 else latencies
                avg_latency = sum(valid_latencies) / len(valid_latencies)
                t_lat += avg_latency
                print(f"-> Сквозная задержка (Latency):     {avg_latency:.2f} мс")
                print(f"Количество замеров: {len(latencies)}")
            
            if cpu_measurements:
                valid_cpu = cpu_measurements[1:-1] if len(cpu_measurements) > 2 else cpu_measurements
                if valid_cpu:
                    avg_cpu = sum(valid_cpu) / len(valid_cpu)
                    print(f"-> Средняя загрузка CPU:            {avg_cpu:.1f} %")
                    print(f"-> Остаточный ресурс (Headroom):    {100.0 - avg_cpu:.1f} %")
            print("==================================================")
            pipeline.set_state(Gst.State.NULL)
        time.sleep(5)
        
    print(f"Средняя задержка за {TEST_COUNT} запусков: {t_lat / 3:.2f} Модель: {model}")
    results[model] = round(t_lat / 3, 2)

print(results)
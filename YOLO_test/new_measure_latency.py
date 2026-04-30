#!/usr/bin/env python3

from gi.repository import GLib, Gst
import sys
import os
import time
import argparse
from collections import OrderedDict

import gi
gi.require_version('Gst', '1.0')

# ==============================================================================
# Класс для замера задержки и отслеживания конца файлов (EOS)
# ==============================================================================


class LatencyTracker:
    def __init__(self, num_sources, main_loop):
        self.start_times = {i: OrderedDict() for i in range(num_sources)}
        self.MAX_STORED = 1000

        # Переменные для отслеживания конца видео
        self.num_sources = num_sources
        self.main_loop = main_loop
        self.finished_sources = set()

    def on_enter(self, identity, buffer, source_id):
        pts = buffer.pts
        if len(self.start_times[source_id]) > self.MAX_STORED:
            self.start_times[source_id].popitem(last=False)
        self.start_times[source_id][pts] = time.perf_counter()

    def on_exit(self, identity, buffer, source_id):
        pts = buffer.pts
        start_time = self.start_times[source_id].pop(pts, None)
        if start_time is not None:
            latency_ms = (time.perf_counter() - start_time) * 1000
            sys.stdout.write(
                f"[Source {source_id}] Frame PTS: {pts} | Latency: {latency_ms:.2f} ms\n")
            sys.stdout.flush()

    def mark_eos(self, source_id):
        """Вызывается, когда конкретный источник достиг конца файла"""
        if source_id not in self.finished_sources:
            self.finished_sources.add(source_id)
            sys.stdout.write(
                f"\n[INFO] Source {source_id} reached End-Of-Stream.\n")
            sys.stdout.write(
                "[INFO] Shutting down pipeline to prevent batching deadlock...\n")
            sys.stdout.flush()

            # Завершаем работу по ПЕРВОМУ закончившемуся файлу
            # GLib.idle_add(self.main_loop.quit)
            os._exit(0)

# ==============================================================================
# Перехват событий EOS на выходе из источника
# ==============================================================================


def eos_probe(pad, info, data):
    event = info.get_event()
    if event.type == Gst.EventType.EOS:
        tracker, source_id = data
        sys.stdout.write(f"[INFO] Source {source_id} finished playing.\n")
        tracker.mark_eos(source_id)
    return Gst.PadProbeReturn.OK

# ==============================================================================
# Обработчик шины сообщений
# ==============================================================================


def bus_call(bus, message, loop):
    t = message.type
    if t == Gst.MessageType.EOS:
        sys.stdout.write("Pipeline End-of-stream\n")
        loop.quit()
    elif t == Gst.MessageType.WARNING:
        err, debug = message.parse_warning()
        sys.stderr.write(f"Warning: {err}: {debug}\n")
    elif t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        sys.stderr.write(f"Error: {err}: {debug}\n")
        loop.quit()
    return True

# ==============================================================================
# Утилита для создания элементов с проверкой
# ==============================================================================


def make_element(factory_name, element_name):
    elm = Gst.ElementFactory.make(factory_name, element_name)
    if not elm:
        sys.stderr.write(f"Unable to create element {factory_name} \n")
        sys.exit(1)
    return elm

# ==============================================================================
# Создание Source Bin
# ==============================================================================


def create_source_bin(index, uri, tracker):
    print(f"Creating source bin for stream {index} (URI: {uri})")
    bin_name = f"source-bin-{index}"
    nbin = Gst.Bin.new(bin_name)

    uri_decode_bin = make_element("uridecodebin", f"uri-decode-{index}")
    uri_decode_bin.set_property("uri", uri)

    scale_q = make_element("queue", f"scale_q_{index}")
    videoscale = make_element("videoscale", f"scale_{index}")
    convert = make_element("videoconvert", f"conv_{index}")
    capsfilter = make_element("capsfilter", f"caps_{index}")

    caps = Gst.Caps.from_string(
        "video/x-raw, pixel-aspect-ratio=1/1, format=RGB, width=640, height=640")
    capsfilter.set_property("caps", caps)

    identity_enter = make_element("identity", f"enter_{index}")
    identity_enter.set_property("signal-handoffs", True)
    identity_enter.connect("handoff", tracker.on_enter, index)

    stream_id = make_element("hailofilter", f"stream_id_{index}")
    stream_id.set_property(
        "so-path", "/usr/lib/aarch64-linux-gnu/hailo/tappas/post_processes/libstream_id_tool.so")
    stream_id.set_property("config-path", f"src_{index}")

    src_q = make_element("queue", f"src_q_{index}")

    scale_q.set_property("max-size-buffers", 3)
    scale_q.set_property("leaky", 2)

    src_q.set_property("max-size-buffers", 3)
    src_q.set_property("leaky", 2)

    for elem in [uri_decode_bin, scale_q, videoscale, convert, capsfilter, identity_enter, stream_id, src_q]:
        nbin.add(elem)

    scale_q.link(videoscale)
    videoscale.link(convert)
    convert.link(capsfilter)
    capsfilter.link(identity_enter)
    identity_enter.link(stream_id)
    stream_id.link(src_q)

    # Вешаем Probe на выходную очередь источника для отслеживания EOS
    srcpad = src_q.get_static_pad("src")
    srcpad.add_probe(Gst.PadProbeType.EVENT_DOWNSTREAM,
                     eos_probe, (tracker, index))

    def cb_newpad(decodebin, decoder_src_pad, data):
        try:
            caps = decoder_src_pad.query_caps(None)
            gstname = caps.get_structure(0).get_name()
            if gstname.startswith("video"):
                sink_pad = scale_q.get_static_pad("sink")
                if not sink_pad.is_linked():
                    decoder_src_pad.link(sink_pad)
        except Exception as e:
            print(f"[{bin_name}] Error in cb_newpad: {e}")

    uri_decode_bin.connect("pad-added", cb_newpad, None)

    bin_pad = Gst.GhostPad.new("src", srcpad)
    nbin.add_pad(bin_pad)

    return nbin

# ==============================================================================
# Основная логика
# ==============================================================================


def main(args):
    stream_paths = args.input
    model_path = args.model
    number_sources = len(stream_paths)

    Gst.init(None)

    # Инициализируем главный цикл ДО трекера, чтобы передать его внутрь
    loop = GLib.MainLoop()
    tracker = LatencyTracker(number_sources, loop)
    pipeline = Gst.Pipeline()

    # 1. Мультиплексор
    streammux = make_element("hailoroundrobin", "Stream-muxer")
    streammux.set_property("mode", 1)
    pipeline.add(streammux)

    # 2. Подключение источников
    for i in range(number_sources):
        path = stream_paths[i]
        uri = path if path.startswith(
            ("rtsp://", "http://", "file://")) else f"file://{os.path.abspath(path)}"

        source_bin = create_source_bin(i, uri, tracker)
        pipeline.add(source_bin)

        sinkpad = streammux.request_pad_simple(f"sink_{i}")
        srcpad = source_bin.get_static_pad("src")
        srcpad.link(sinkpad)

    # 3. Инференс
    infer_q = make_element("queue", "infer_q")
    infer_q.set_property("max-size-buffers", 3)
    infer_q.set_property("leaky", 2)

    hailonet = make_element("hailonet", "primary-inference")
    hailonet.set_property("hef-path", model_path)
    hailonet.set_property("batch-size", number_sources)
    hailonet.set_property("vdevice-group-id", "SHARED")
    hailonet.set_property("output-format-type", "HAILO_FORMAT_TYPE_FLOAT32")
    hailonet.set_property("force-writable", True)

    hailofilter = make_element("hailofilter", "post-process")
    hailofilter.set_property(
        "so-path", "/usr/local/hailo/resources/so/libyolo_hailortpp_postprocess.so")
    hailofilter.set_property("function-name", "filter_letterbox")
    hailofilter.set_property("qos", False)

    # 4. Роутер
    demux_q = make_element("queue", "demux_q")
    demux_q.set_property("max-size-buffers", 3)
    demux_q.set_property("leaky", 2)

    streamrouter = make_element("hailostreamrouter", "Stream-demuxer")

    for elem in [infer_q, hailonet, hailofilter, demux_q, streamrouter]:
        pipeline.add(elem)

    streammux.link(infer_q)
    infer_q.link(hailonet)
    hailonet.link(hailofilter)
    hailofilter.link(demux_q)
    demux_q.link(streamrouter)

    # 5. Выходы
    for i in range(number_sources):
        sink_q = make_element("queue", f"sink_q_{i}")
        sink_q.set_property("max-size-buffers", 3)
        sink_q.set_property("leaky", 2)

        identity_exit = make_element("identity", f"exit_{i}")
        identity_exit.set_property("signal-handoffs", True)
        identity_exit.connect("handoff", tracker.on_exit, i)

        fpssink = make_element("fpsdisplaysink", f"fpssink_{i}")
        fakesink = make_element("fakesink", f"fakesink_{i}")

        fakesink.set_property("sync", False)
        fakesink.set_property("async", False)

        fpssink.set_property("video-sink", fakesink)
        fpssink.set_property("text-overlay", False)
        fpssink.set_property("sync", False)

        pipeline.add(sink_q)
        pipeline.add(identity_exit)
        pipeline.add(fpssink)

        srcpad = streamrouter.request_pad_simple(f"src_{i}")
        Gst.util_set_object_arg(srcpad, "input-streams", f"<sink_{i}>")

        sinkpad = sink_q.get_static_pad("sink")
        srcpad.link(sinkpad)

        sink_q.link(identity_exit)
        identity_exit.link(fpssink)

    # 6. Запуск
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)

    print("Starting pipeline...")
    pipeline.set_state(Gst.State.PLAYING)

    try:
        loop.run()
    except KeyboardInterrupt:
        print("\nCtrl-C pressed, exiting...")
    finally:
        print("Cleaning up pipeline...")
        # Переводим в NULL, чтобы освободить чип и память
        pipeline.set_state(Gst.State.NULL)
        bus.remove_signal_watch()
        # Небольшая пауза, чтобы GStreamer успел закрыть файлы
        time.sleep(0.5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i", "--input", help="Path to input files/URIs", nargs="+", required=True)
    parser.add_argument(
        "-m", "--model", help="Path to Hailo HEF model", required=True)
    args = parser.parse_args()

    sys.exit(main(args))

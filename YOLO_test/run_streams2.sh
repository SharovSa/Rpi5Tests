MODEL_PATH=$1

# GST_DEBUG="fpsdisplaysink:5" gst-launch-1.0 \
#  filesrc location="../long_visible.mp4" name=source_0 ! \
#  decodebin name=source_0_decodebin ! \
#  queue leaky=no max-size-buffers=3 ! \
#  videoscale n-threads=2 ! \
#  videoconvert n-threads=3 qos=false ! \
#  video/x-raw, pixel-aspect-ratio=1/1, format=RGB, width=640, height=640 ! \
#  hailofilter so-path=/usr/lib/aarch64-linux-gnu/hailo/tappas/post_processes/libstream_id_tool.so config-path=src_0 ! \
#  queue leaky=no max-size-buffers=30 ! \
#  robin.sink_0 \
#  filesrc location="../long_visible.mp4" name=source_1 ! \
#  decodebin name=source_1_decodebin ! \
#  queue leaky=no max-size-buffers=3 ! \
#  videoscale n-threads=2 ! \
#  videoconvert n-threads=3 qos=false ! \
#  video/x-raw, pixel-aspect-ratio=1/1, format=RGB, width=640, height=640 ! \
#  hailofilter so-path=/usr/lib/aarch64-linux-gnu/hailo/tappas/post_processes/libstream_id_tool.so config-path=src_1 ! \
#  queue leaky=no max-size-buffers=30 ! \
#  robin.sink_1 \
#  hailoroundrobin mode=1 name=robin ! \
#  queue leaky=no max-size-buffers=3 ! \
#  hailonet hef-path="$MODEL_PATH" batch-size=2 vdevice-group-id=SHARED nms-score-threshold=0.3 nms-iou-threshold=0.45 output-format-type=HAILO_FORMAT_TYPE_FLOAT32 force-writable=true ! \
#  queue leaky=no max-size-buffers=3 ! \
#  hailofilter so-path=/usr/local/hailo/resources/so/libyolo_hailortpp_postprocess.so function-name=filter_letterbox qos=false ! \
#  queue leaky=no max-size-buffers=3 ! \
#  fpsdisplaysink video-sink="fakesink sync=false" text-overlay=false silent=false sync=false 2> log2.txt

GST_DEBUG="fpsdisplaysink:5" gst-launch-1.0 \
 filesrc location=long_hevc3.h265 name=source_0 ! \
 h265parse ! v4l2slh265dec name=source_0_decodebin ! \
 queue max-size-buffers=3 name=source_0_convert_q leaky=no  ! \
 glupload ! \
 glcolorconvert ! \
 "video/x-raw(memory:GLMemory),format=NV12" ! \
 gldownload ! \
 video/x-raw,format=NV12 ! \
 videoconvert n-threads=3 name=source_0_convert qos=false ! \
 video/x-raw, format=RGB ! \
 hailofilter name=set_src_0 so-path=/usr/lib/aarch64-linux-gnu/hailo/tappas/post_processes/libstream_id_tool.so config-path=src_0 ! \
 queue name=src_q_0 leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0  ! \
 robin.sink_0 \
 filesrc location=long_hevc3.h265 name=source_1 ! \
 h265parse ! v4l2slh265dec name=source_1_decodebin ! \
 queue max-size-buffers=3 name=source_1_scale_q leaky=no  ! \
 glupload ! \
 glcolorconvert ! \
 "video/x-raw(memory:GLMemory),format=NV12" ! \
 gldownload ! \
 video/x-raw,format=NV12 ! \
 videoconvert n-threads=3 name=source_1_convert qos=false ! \
 video/x-raw, format=RGB ! \
 hailofilter name=set_src_1 so-path=/usr/lib/aarch64-linux-gnu/hailo/tappas/post_processes/libstream_id_tool.so config-path=src_1 ! \
 queue name=src_q_1 leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0  ! \
 robin.sink_1 hailoroundrobin mode=1 name=robin ! \
 queue name=inference_hailonet_q leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0  ! \
 hailonet name=inference_hailonet hef-path="$MODEL_PATH" batch-size=2  vdevice-group-id=SHARED  ! \
 queue name=inference_hailofilter_q leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0  ! \
 hailofilter name=inference_hailofilter so-path=/usr/local/hailo/resources/so/libyolo_hailortpp_postprocess.so   function-name=filter_letterbox  qos=false ! \
 queue name=call_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0  ! \
 fpsdisplaysink video-sink="fakesink sync=false" text-overlay=false silent=false sync=false
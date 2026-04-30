# =============================================
# ПАЙПЛАЙН ДЛЯ 1 ВИДЕОПОТОКА (batch-size=1)
# =============================================

MODEL_PATH=$1

# GST_DEBUG="fpsdisplaysink:5" gst-launch-1.0 \
#  filesrc location=../long_visible.mp4 ! \
#  decodebin ! \
#  queue max-size-buffers=3 leaky=no ! \
#  glupload ! \
#  glcolorconvert ! \
#  "video/x-raw(memory:GLMemory),format=NV12" ! \
#  gldownload ! \
#  video/x-raw,format=NV12 ! \
#  videoconvert n-threads=3 qos=false ! \
#  video/x-raw,format=RGB ! \
#  hailofilter name=set_src_0 so-path=/usr/lib/aarch64-linux-gnu/hailo/tappas/post_processes/libstream_id_tool.so config-path=src_0 ! \
#  queue max-size-buffers=30 leaky=no ! \
#  hailonet name=inference_hailonet hef-path="$MODEL_PATH" batch-size=1 vdevice-group-id=SHARED ! \
#  queue max-size-buffers=3 leaky=no ! \
#  hailofilter name=inference_hailofilter so-path=/usr/local/hailo/resources/so/libyolo_hailortpp_postprocess.so function-name=filter_letterbox qos=false ! \
#  fpsdisplaysink video-sink="fakesink sync=false" text-overlay=false silent=false sync=false 

GST_DEBUG="fpsdisplaysink:5" gst-launch-1.0 \
 filesrc location="../long_visible.mp4" ! \
 decodebin ! \
 queue max-size-buffers=3 leaky=no ! \
 videoscale n-threads=2 ! \
 videoconvert n-threads=3 qos=false ! \
 video/x-raw,format=RGB,width=640,height=640,pixel-aspect-ratio=1/1 ! \
 hailofilter name=set_src_0 so-path=/usr/lib/aarch64-linux-gnu/hailo/tappas/post_processes/libstream_id_tool.so config-path=src_0 ! \
 queue max-size-buffers=3 leaky=no ! \
 hailonet name=inference_hailonet hef-path="$MODEL_PATH" batch-size=1 vdevice-group-id=SHARED ! \
 queue max-size-buffers=3 leaky=no ! \
 hailofilter name=inference_hailofilter so-path=/usr/local/hailo/resources/so/libyolo_hailortpp_postprocess.so function-name=filter_letterbox qos=false ! \
 fpsdisplaysink video-sink="fakesink sync=false" text-overlay=false silent=false sync=false 2> log1.txt
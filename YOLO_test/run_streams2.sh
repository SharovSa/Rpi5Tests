MODEL_PATH=$1

# GST_DEBUG="fpsdisplaysink:5" gst-launch-1.0 \
#  filesrc location="../long_visible.mp4" name=source_0 ! \
#  decodebin name=source_0_decodebin ! \
#  videoscale n-threads=2 ! \
#  queue leaky=no max-size-buffers=8 ! \
#  videoconvert n-threads=3 qos=false ! \
#  video/x-raw, pixel-aspect-ratio=1/1, format=RGB, width=640, height=640 ! \
#  hailofilter so-path=/usr/lib/aarch64-linux-gnu/hailo/tappas/post_processes/libstream_id_tool.so config-path=src_0 ! \
#  robin.sink_0 \
#  filesrc location="../long_visible.mp4" name=source_1 ! \
#  decodebin name=source_1_decodebin ! \
#  videoscale n-threads=2 ! \
#  queue leaky=no max-size-buffers=3 ! \
#  videoconvert n-threads=3 qos=false ! \
#  video/x-raw, pixel-aspect-ratio=1/1, format=RGB, width=640, height=640 ! \
#  hailofilter so-path=/usr/lib/aarch64-linux-gnu/hailo/tappas/post_processes/libstream_id_tool.so config-path=src_1 ! \
#  robin.sink_1 \
#  hailoroundrobin mode=1 name=robin ! \
#  queue leaky=no max-size-buffers=3 ! \
#  hailonet hef-path="$MODEL_PATH" batch-size=2 vdevice-group-id=SHARED nms-score-threshold=0.3 nms-iou-threshold=0.45 output-format-type=HAILO_FORMAT_TYPE_FLOAT32 force-writable=true ! \
#  queue leaky=no max-size-buffers=3 ! \
#  hailofilter so-path=/usr/local/hailo/resources/so/libyolo_hailortpp_postprocess.so function-name=filter_letterbox qos=false ! \
#  queue leaky=no max-size-buffers=3 ! \
#  fpsdisplaysink video-sink="fakesink sync=false" text-overlay=false silent=false sync=false 2> log2.txt

GST_DEBUG="fpsdisplaysink:5" gst-launch-1.0 \
 filesrc location="../long_visible.mp4" name=source_0 ! \
 queue name=source_0_queue_decode leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0  ! \
  decodebin name=source_0_decodebin !  queue name=source_0_scale_q leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0 ! \
  videoscale name=source_0_videoscale n-threads=2 ! \
  queue name=source_0_convert_q leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0  ! \
  videoconvert n-threads=3 name=source_0_convert qos=false ! \
  video/x-raw, pixel-aspect-ratio=1/1, format=RGB, width=640, height=640 ! \
   hailofilter name=set_src_0 so-path=/usr/lib/aarch64-linux-gnu/hailo/tappas/post_processes/libstream_id_tool.so config-path=src_0 ! \
   queue name=src_q_0 leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0  ! \
   robin.sink_0 filesrc location="../long_visible.mp4" name=source_1 ! \
   queue name=source_1_queue_decode leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0  !\
   decodebin name=source_1_decodebin ! \
   queue name=source_1_scale_q leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0  ! \
   videoscale name=source_1_videoscale n-threads=2 ! \
   queue name=source_1_convert_q leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0  ! \
   videoconvert n-threads=3 name=source_1_convert qos=false ! \
   video/x-raw, pixel-aspect-ratio=1/1, format=RGB, width=640, height=640 ! \
   hailofilter name=set_src_1 so-path=/usr/lib/aarch64-linux-gnu/hailo/tappas/post_processes/libstream_id_tool.so config-path=src_1 ! \
   queue name=src_q_1 leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0  ! \
   robin.sink_1 hailoroundrobin mode=1 name=robin ! \
   queue name=inference_scale_q leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0  ! \
   videoscale name=inference_videoscale n-threads=2 qos=false ! \
   queue name=inference_convert_q leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0  ! \
   video/x-raw, pixel-aspect-ratio=1/1 ! videoconvert name=inference_videoconvert n-threads=2 ! \
   queue name=inference_hailonet_q leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0  ! \
   hailonet name=inference_hailonet hef-path="$MODEL_PATH" batch-size=2  vdevice-group-id=SHARED output-format-type=HAILO_FORMAT_TYPE_FLOAT32 force-writable=true  ! \
   queue name=inference_hailofilter_q leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0  ! \
   hailofilter name=inference_hailofilter so-path=/usr/local/hailo/resources/so/libyolo_hailortpp_postprocess.so   function-name=filter_letterbox  qos=false ! \
   queue name=inference_output_q leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0   ! \
   queue name=identity_callback_q leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0  ! \
   identity name=identity_callback  ! \
   queue name=call_q leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0  ! \
   fpsdisplaysink video-sink="fakesink sync=false" text-overlay=false silent=false sync=false 2> log2.txt
import gi
gi.require_version("Gst", "1.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository import GObject
import gtk

Gst.debug_set_active(True)
Gst.debug_set_default_threshold(4)
Gst.init("")

import signal
import os
import sys
import argparse
import numpy as np
import cv2
import time

def parse_args():
    parseargs = argparse.ArgumentParser(prog="2_.py")
    parseargs.add_argument("-p", "--recv_port", default=5000, help="Specify Receive Port")
    parseargs.add_argument("-a", "--set_algo", default=3, help="Select Algo do decode")
    parseargs.add_argument("-v", "--video_player", default="OpenCV", help="Select app to play/OpenCV/videosink")
    args = parseargs.parse_args()
    return args

class VideoReceiver():
    def __init__(self, args):
        self.args = args
        self.pipeline = self.create_pipeline()
        message_bus = self.pipeline.get_bus()
        self.bus = message_bus
        message_bus.add_signal_watch()
        message_bus.connect('message', self.message_handler)

    def message_handler(self, bus, message):
        struct = message.get_structure()
        print("Message type")
        print(message.type)
        if message.type == Gst.MessageType.EOS:
            print('Found End Of Stream!.')
            Gtk.main_quit()
        elif message.type == Gst.MessageType.TAG and message.parse_tag() and struct.has_field('taglist'):
            print('MetaTags:')
            taglist = struct.get_value('taglist')
            for x in range(taglist.n_tags()):
                name = taglist.nth_tag_name(x)
                #print(' name %s: val %s' % (name, taglist.get_string(name)[1]))
        else:
            pass



    def create_pipeline(self):
        print("Create Pipeline")
        new_pipe = Gst.Pipeline()
        print(new_pipe)
        udpread = Gst.ElementFactory.make('udpsrc', 'udpr1')
        udpread.set_property('port', int(args.recv_port))
        udpcaps = Gst.caps_from_string("application/x-rtp, payload=127")
        udpread.set_property('caps', udpcaps)
        rtpstreamdepay = Gst.ElementFactory.make('rtph264depay', 'udp2rtph')
        #rtpstreamdepay.set_property('caps', udpcaps)
        
        # may be changed to the decodebin, more universal than avdec_h264
        avdecode = Gst.ElementFactory.make('avdec_h264', 'vi1dec')
        videoplay = Gst.ElementFactory.make('autovideosink', 'vi1play')

        appsink = Gst.ElementFactory.make('appsink', 'appsnk1')

        q1_udp_to_dec = Gst.ElementFactory.make('queue', 'q1udpout')
        if (self.args.video_player == "OpenCV"):
            [ new_pipe.add(k) for k in [udpread, q1_udp_to_dec, rtpstreamdepay, avdecode, appsink]] 
            avdecode.link(appsink)
            appsink.set_property("emit-signals", True)
            appsink.connect('new-sample', self.sample_process, None)
        elif (self.args.video_player == "videosink"):
            [ new_pipe.add(k) for k in [udpread, q1_udp_to_dec, rtpstreamdepay, avdecode, videoplay]]
            avdecode.link(videoplay)
        else:
            raise Exception("Only OPENCV, videosink allowed")

        udpread.link(q1_udp_to_dec)
        q1_udp_to_dec.link(rtpstreamdepay)
        rtpstreamdepay.link(avdecode)

        self.video_sink = videoplay
        self.appsink = appsink

        return new_pipe


    def YV12_h_stream2RGB_frame(self, data):
        w=640
        h=360
        size=w*h

        stream=np.fromstring(data,np.uint8) #convert data form string to numpy array

        #Y bytes  will start form 0 and end in size-1
        y=stream[0:size].reshape(h,w) # create the y channel same size as the image

        #U bytes will start from size and end at size+size/4 as its size = framesize/4
        u=stream[size:(size+int(size/4))].reshape(int(h/2),int(w/2))# create the u channel its size=framesize/4

        #up-sample the u channel to be the same size as the y channel and frame using pyrUp func in opencv2
        u_upsize=cv2.pyrUp(u)

        #do the same for v channel
        v=stream[int(size+int(size/4)):].reshape(int(h/2),int(w/2))
        v_upsize=cv2.pyrUp(v)

        #create the 3-channel frame using cv2.merge func watch for the order
        yuv=cv2.merge((y,u_upsize,v_upsize))

        #Convert TO RGB format
        rgb=cv2.cvtColor(yuv,cv2.COLOR_YCrCb2RGB)

        #print("imshow")

        #show frame
        cv2.imshow("show",rgb)
        #print("imshow->ok")
        cv2.waitKey(1)

    def YV12_stream2RGB_frame(self, data):
        w,h = 640,360
        px=w*h
        stream=np.fromstring(data,np.uint8)
        # Take first h x w samples and reshape as Y channel
        Y = stream[0:w*h].reshape(h,w)
        # Take next px/4 samples as U
        U = stream[px:(px*5)//4].reshape(h//2,w//2)

        # Take next px/4 samples as V
        V = stream[(px*5)//4:(px*6)//4].reshape(h//2,w//2)
        # Undo subsampling of U and V by doubling height and width
        #Ufull = U.copy().resize((w,h))
        Ufull=cv2.pyrUp(U)
        Vfull=cv2.pyrUp(V)
        yuv=cv2.merge((Y, Vfull, Ufull))
        #print(yuv)
        rgb=cv2.cvtColor(yuv,cv2.COLOR_YUV2RGB)

        cv2.imshow("show",rgb)
        #print("imshow->ok")
        cv2.waitKey(1)

    def YUV420P_2_rgb(self, sample):
        buf = sample.get_buffer()
        caps = sample.get_caps()
        height = caps.get_structure(0).get_value('height')
        width = caps.get_structure(0).get_value('width')
        b1=buf.extract_dup(0, buf.get_size())
        frame = np.frombuffer(b1, np.uint8).reshape((height+height//2, width))
        #print(np.frombuffer(b1, np.uint8))
        #print("---")
        rgb=cv2.cvtColor(frame, cv2.COLOR_YUV420p2RGB)
        cv2.imshow("show", rgb)
        cv2.waitKey(1)

    def gst_to_opencv(self, sample):
        buf = sample.get_buffer()
        caps = sample.get_caps()
        b1=buf.extract_dup(0, buf.get_size())
        #print(caps.get_structure(0).get_value('format'))
        #print(caps.get_structure(0).get_value('height'))
        #print(caps.get_structure(0).get_value('width'))
        if int(self.args.set_algo) == 1:
            self.YV12_h_stream2RGB_frame(b1)
        elif int(self.args.set_algo) == 2:
            self.YV12_stream2RGB_frame(b1)
        elif int(self.args.set_algo) == 3:
            self.YUV420P_2_rgb(sample)
        else:
            raise Exception("unknown decode algo")

        return False

    def sample_process(self, sink, user_data):
        sample = sink.emit('pull-sample')
        buf = sample.get_buffer()
        #print("Timestamp: ")
        #print(buf.pts)
        arr = self.gst_to_opencv(sample)
        return Gst.FlowReturn.OK


    def run_srv(self):
        print(self.pipeline)
        self.pipeline.set_state(Gst.State.PLAYING)


    def print_args(self):
        print(args)

if __name__ == "__main__":
    print("GST ATK2.0 APP")
    args = parse_args()
    VideoRecv = VideoReceiver(args)
    print("args=")
    VideoRecv.print_args()
    VideoRecv.run_srv()
    #Gtk.main()
    #GObject.MainLoop.run()
    while True:
        time.sleep(1)
        #message = VideoRecv.bus.timed_pop_filtered(1000000, Gst.MessageType.ANY)



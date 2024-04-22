import gi
gi.require_version("Gst", "1.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository import GObject

import os
import signal
import argparse
import ipaddress


Gst.debug_set_active(True)
Gst.debug_set_default_threshold(4)
Gst.init("")
signal.signal(signal.SIGINT, signal.SIG_DFL)
# If PY is 3.11+ threads is not needed 
GObject.threads_init()


def parse_args():
    argparser = argparse.ArgumentParser(prog="1_.py")
    argparser.add_argument("-l", "--location")
    argparser.add_argument("-d", "--dest-port", default=5000, help="DestStreamPort")
    argparser.add_argument("-i", "--dest-ip", default="127.0.0.1", help="DestStreamIP")
    argparser.add_argument("-ll", "--stream-l", default=1, help="IsPlayLocal")

    arguments = argparser.parse_args()
    return arguments



class VideoStreamer():
    def __init__(self, args):
        self.args = args
        self.pipeline = self.create_pipeline()

        message_bus = self.pipeline.get_bus()
        message_bus.add_signal_watch()
        message_bus.connect('message', self.message_handler)

    def message_handler(self, bus, message):
        struct = message.get_structure()
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



    def create_source(self):
        if not self.args.location.startswith('http') and not os.path.exists(self.args.location):
            raise IOError("File %s doesn't exists" % self.args.location)

        if (self.args.location.startswith('http')):
            source = Gst.ElementFactory.make('souphttpsrc', 'source_i')
        else:
            source = Gst.ElementFactory.make('filesrc', 'source_i')
        source.set_property('location', self.args.location)

        print("Self source location")
        print(source)
        print(self.args.location)

        return source

    def create_udpstream(self, args):
        print("Create UDP packet stream")
        x264_enc = Gst.ElementFactory.make('x264enc', '264_to_rtph')
        rtph_udp = Gst.ElementFactory.make('rtph264pay',  'udp264helper')
        udp_sink  = Gst.ElementFactory.make('udpsink', 'udp264tx')
        udp_sink.set_property('host', self.args.dest_ip)
        udp_sink.set_property('port', int(self.args.dest_port))
        print(rtph_udp)
        print(udp_sink)
        print(self.args)
        return x264_enc, rtph_udp, udp_sink


    def create_pipeline(self):
        new_pipe = Gst.Pipeline()
        source = self.create_source()

        decodebin = Gst.ElementFactory.make('decodebin', 'decode_bin')
        videoconvert = Gst.ElementFactory.make('videoconvert', 'video_c')
        videosink = Gst.ElementFactory.make('autovideosink', 'video_sink') 


        def dynamic_decodebin_link2vi(decodebin, pad):
            pad.link(videoconvert.get_static_pad('sink'))

        def dynamic_decodebin_link2ip(decodebin, pad):
            pad.link(x264_enc.get_static_pad('sink'))


        # Pipelines should be added before linking because link are null after adding
        if int(self.args.stream_l) != 1:
            x264_enc, udp_serv_rtph, udp_serv_sink = self.create_udpstream(self.args)
            decodebin.connect('pad-added', dynamic_decodebin_link2ip)
            [new_pipe.add(k) for k in [source, decodebin, x264_enc, udp_serv_rtph, udp_serv_sink]]
        else:
            decodebin.connect('pad-added', dynamic_decodebin_link2vi)
            [new_pipe.add(k) for k in [source, decodebin, videoconvert, videosink]]

        source.link(decodebin)
        videoconvert.link(videosink)

        if int(self.args.stream_l) != 1:
            x264_enc.link(udp_serv_rtph)
            udp_serv_rtph.link(udp_serv_sink)

        print(source)
        print(decodebin)
        print("VideoSink=")
        print(videosink)


        return new_pipe

    def print_args(self):
        print("Arguments created for : ")
        print(self.args)

    def run(self):
        self.pipeline.set_state(Gst.State.PLAYING)


if __name__ == "__main__":
    print ("GTestApp 1.0 ATK")
    input_args = parse_args()
    print (input_args)
    
    Vi1 = VideoStreamer(input_args)
    Vi1.print_args()
    Vi1.run()

    Gtk.main()



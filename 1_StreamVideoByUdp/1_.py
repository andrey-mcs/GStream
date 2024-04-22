import gi
gi.require_version("Gst", "1.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository import GObject

import os
import signal
import argparse


Gst.debug_set_active(True)
Gst.debug_set_default_threshold(1)
Gst.init("")
signal.signal(signal.SIGINT, signal.SIG_DFL)
# If PY is 3.11+ threads is not needed 
GObject.threads_init()


def parse_args():
    argparser = argparse.ArgumentParser(prog="1_.py")
    argparser.add_argument("-l", "--location")
    argparser.add_argument("-v", "--voice", help="VoiceDecodedLocation")
    argparser.add_argument("-vv", "--video", help="VideoDecodedLocation")

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
                print('  %s: %s' % (name, taglist.get_string(name)[1]))
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


    def create_pipeline(self):
        new_pipe = Gst.Pipeline()
        source = self.create_source()

        decodebin = Gst.ElementFactory.make('decodebin', 'decode_bin')
        videoconvert = Gst.ElementFactory.make('videoconvert', 'video_c')
        videosink = Gst.ElementFactory.make('autovideosink', 'video_sink') 

        def dynamic_decodebin_link(decodebin, pad):
            pad.link(videoconvert.get_static_pad('sink'))

        decodebin.connect('pad-added', dynamic_decodebin_link)

        [new_pipe.add(k) for k in [source, decodebin, videoconvert, videosink]]

        source.link(decodebin)
        videoconvert.link(videosink)

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



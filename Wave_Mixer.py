#!/usr/bin/env python

import pygtk
import gtk,os,signal
import pyaudio
import wave
import sys
import struct
from array import array
import copy
from sys import byteorder
from array import array
from struct import pack


THRESHOLD = 500
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
RATE = 44100


def is_silent(snd_data):
    	return max(snd_data) < THRESHOLD


def normalize(snd_data):
	MAXIMUM = 16384
	times = float(MAXIMUM)/max(abs(i) for i in snd_data)
	r = array('h')
	for i in snd_data:
		r.append(int(i*times))
	return r

def trim(snd_data):
	def _trim(snd_data):
	       	snd_started = False
	        r = array('h')

	        for i in snd_data:
	        	if not snd_started and abs(i)>THRESHOLD:
	                	snd_started = True
	                	r.append(i)

	            	elif snd_started:
	                	r.append(i)
	        return r

	    # Trim to the left
	snd_data = _trim(snd_data)

	    # Trim to the right
	snd_data.reverse()
	snd_data = _trim(snd_data)
	snd_data.reverse()
	return snd_data

def add_silence(snd_data, seconds):
	r = array('h', [0 for i in xrange(int(seconds*RATE))])
	r.extend(snd_data)
	r.extend([0 for i in xrange(int(seconds*RATE))])
	return r

def record():
	p = pyaudio.PyAudio()
	stream = p.open(format=FORMAT, channels=1, rate=RATE,input=True, output=True,frames_per_buffer=CHUNK_SIZE)

	num_silent = 0
	snd_started = False
	r = array('h')

	while 1:
	        # little endian, signed short
		snd_data = array('h', stream.read(CHUNK_SIZE))
		if byteorder == 'big':
	            snd_data.byteswap()
	        r.extend(snd_data)

	        silent = is_silent(snd_data)

	        if silent and snd_started:
	            num_silent += 1
	        elif not silent and not snd_started:
	            snd_started = True

	        if snd_started and num_silent > 30:
	            break

	sample_width = p.get_sample_size(FORMAT)
	stream.stop_stream()
	stream.close()
	p.terminate()
	r = normalize(r)
	r = trim(r)
	r = add_silence(r, 0.5)
	return sample_width, r

def record_to_file(path):
	sample_width, data = record()
    	data = pack('<' + ('h'*len(data)), *data)
    	wf = wave.open(path, 'wb')
    	wf.setnchannels(1)
    	wf.setsampwidth(sample_width)
    	wf.setframerate(RATE)
    	wf.writeframes(data)
    	wf.close()
    	return

class Wave:
	def __init__(self,file_name):
		self.file_name=file_name
		self.file_ptr=wave.open(self.file_name,'r')
		self.num_frame=self.file_ptr.getnframes()
		self.sample_width=self.file_ptr.getsampwidth()
		self.num_channel=self.file_ptr.getnchannels()
		self.frame_rate=self.file_ptr.getframerate()
		self.raw_data=self.file_ptr.readframes(self.num_frame)
		self.file_ptr.close()
		self.total_length=self.num_frame*self.num_channel
		if self.sample_width==1:
			fmt="%iB"%self.total_length
		else : 
			fmt="%ih"%self.total_length
		self.samples=list(struct.unpack(fmt,self.raw_data))

	def amplitude(self,value):
		self.value=value
		self.min_value=-32768
		self.max_value=32767
		for i in xrange(0,len(self.samples)):
			if(self.samples[i]*self.value<=self.max_value and self.samples[i]*self.value>=self.min_value):
				self.samples[i]=self.samples[i]*self.value
			elif (self.samples[i]*self.value>self.max_value and self.samples[i]*self.value>=self.min_value):
				self.samples[i]=self.max_value
			elif (self.samples[i]*self.value<=self.max_value and self.samples[i]*self.value<self.min_value):
				self.samples[i]=self.min_value

	def time_reversal(self,k):
		if k==True:
			if self.num_channel==2:
				self.samples=self.samples[::-1]
				for i in xrange(0,len(self.samples)-1,2):
					swap=self.samples[i]
					self.samples[i]=self.samples[i+1]
					self.samples[i+1]=swap
			elif self.num_channel==1:
				self.samples=self.samples[::-1]
		else:
			pass

	def time_shift(self,value):
		self.value=value
		self.skip_frames=int(abs(self.value)*self.frame_rate)
		if self.num_channel==2:
			if self.value>=0:
				self.samples.reverse()
				for i in xrange(0,2*self.skip_frames,1):
					self.samples.append(0)
				self.samples.reverse()
			elif self.value<0:
				self.samples=self.samples[2*self.skip_frames::1]
			self.num_frame=len(self.samples)/2
		elif self.num_channel==1:
			if self.value>=0:
				self.samples.reverse()
				for i in xrange(0,self.skip_frames,1):
					self.samples.append(0)
				self.samples.reverse()
			elif self.value<0:
				self.samples=self.samples[2*self.skip_frames::1]
			self.num_frame=len(self.samples)

	def quit(self,outputfile):
		self.new_file=outputfile
		if self.sample_width==1: 
			fmt="%iB" % self.num_frame*self.num_channel 
		else: 
			fmt="%ih" % self.num_frame*self.num_channel
		self.data=struct.pack(fmt,*(self.samples))
		self.new_file_ptr=wave.open(self.new_file,'w')
		self.new_file_ptr.setframerate(self.frame_rate) 
		self.new_file_ptr.setnframes(self.num_frame) 
		self.new_file_ptr.setsampwidth(self.sample_width) 
		self.new_file_ptr.setnchannels(self.num_channel) 
		self.new_file_ptr.writeframes(self.data) 
		self.new_file_ptr.close()
	
	
	def time_scaling(self,l):
		self.value=l
		if self.value!=0:
	 		if self.num_channel==1:
	 			final_ans=[]
	 			length=len(self.samples)
	 			num_frame=0
	 			for i in xrange(int(length/self.value)):
					final_ans.append(self.samples[int(self.value*i)])
	 				num_frame+=1
			else :
				odd=[]
				even=[]
				num_frame=0
				length=len(self.samples)
				for i in xrange(0,length,1):
					if i%2==0:
						even.append(self.samples[i])
					else:
						odd.append(self.samples[i])

				final_ans=[]
				lens=min(len(even),len(odd))
				for i in xrange(0,int(lens/self.value)):
						final_ans.append(odd[int(self.value*i)])
						final_ans.append(even[int(self.value*i)])
				
			self.num_samples=self.num_frame*self.num_channel
			self.num_frame=len(final_ans)/self.num_channel
			self.samples=final_ans


file_list=['','','']
output_list=['output.wav','output1.wav','output2.wav','output3.wav','output4.wav']

class mixer:
	def destroy(self,widget,data=None):
		gtk.main_quit()

	def __init__(self):
		self.background = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.background.set_position(gtk.WIN_POS_CENTER)
		self.background.set_size_request(1000,800)
		self.background.set_title("WAVE MIXER")
		fixed=gtk.Fixed()
		file_extention=gtk.FileFilter()
		file_extention.add_pattern("*.wav")

		self.label1=gtk.Label("Wave 1: ")

		self.file_chooser_button=gtk.FileChooserButton("Select .wav file",None)
		self.file_chooser_button.add_filter(file_extention)
		self.file_chooser_button.connect("file-set",self.file_selected,0)
		self.file_chooser_button.set_tooltip_text("Select File")
		self.file_chooser_button.set_size_request(160,40)

		self.label2=gtk.Label("Amplitude: ")
		self.scale1=gtk.HScale()
		self.scale1.set_range(0,5)
		self.scale1.set_increments(0.1,1)
		self.scale1.set_value(1)
		self.scale1.set_digits(1)
		self.scale1.set_size_request(150,40)


		self.label3=gtk.Label("Time Shift: ")
		self.scale3=gtk.HScale()
		self.scale3.set_range(-1,1)
		self.scale3.set_increments(0.125,1)
		self.scale3.set_digits(1)
		self.scale3.set_size_request(150,40)


		self.label4=gtk.Label("Time Scaling: ")
		self.scale4=gtk.HScale()
		self.scale4.set_range(0,8)
		self.scale4.set_increments(0.1,1)
		self.scale4.set_digits(2)
		self.scale4.set_size_request(150,40)


		self.button1 = gtk.CheckButton("Time Reversal")
		self.button1.set_active(False)
		self.button1.unset_flags(gtk.CAN_FOCUS)


		self.button2 = gtk.CheckButton("Select for Modulation ")
		self.button2.set_active(False)
		self.button2.unset_flags(gtk.CAN_FOCUS)

		self.button3 = gtk.CheckButton("Select for Mixing ")
		self.button3.set_active(False)
		self.button3.unset_flags(gtk.CAN_FOCUS)
		
		self.button_play1=gtk.Button("PLAY")
		self.button_play1.set_size_request(50,30)
		self.button_play1.connect("clicked",self.on_clicked,0)


		self.pause_button1=gtk.Button("PAUSE")
		self.pause_button1.set_size_request(60,30)
		self.pause_button1.connect("clicked",self.pause,0)
		
		self.pause_flag1=0
		self.pid1=0

		self.stop1=gtk.Button("STOP")
		self.stop1.set_size_request(50,30)
		self.stop1.connect("clicked",self.stop,0)
		fixed.put(self.stop1,180,500)


		fixed.put(self.label1,25,50)
		fixed.put(self.label2,50,160)
		fixed.put(self.scale1,50,180)
		fixed.put(self.label3,50,250)
		fixed.put(self.scale3,50,270)
		fixed.put(self.label4,50,320)
		fixed.put(self.scale4,50,350)
		fixed.put(self.button1,50,400)
		fixed.put(self.button2,50,425)
		fixed.put(self.button3,50,450)
		fixed.put(self.button_play1,50,500)
		fixed.put(self.pause_button1,120,500)
		fixed.put(self.file_chooser_button,50,100)
		

		self.label2=gtk.Label("Wave 2 :")

		self.file_chooser_button2=gtk.FileChooserButton("Select .wav file",None)
		self.file_chooser_button2.add_filter(file_extention)
		self.file_chooser_button2.connect("file-set",self.file_selected,1)
		self.file_chooser_button2.set_tooltip_text("Select File")
		self.file_chooser_button2.set_size_request(160,40)

		self.label2_1=gtk.Label("Amplitude: ")
		self.scale2_1=gtk.HScale()
		self.scale2_1.set_range(0,5)
		self.scale2_1.set_increments(0.1,1)
		self.scale2_1.set_value(1)
		self.scale2_1.set_digits(1)
		self.scale2_1.set_size_request(150,40)


		self.label2_3=gtk.Label("Time Shift: ")
		self.scale2_3=gtk.HScale()
		self.scale2_3.set_range(-1,1)
		self.scale2_3.set_increments(0.125,1)
		self.scale2_3.set_digits(1)
		self.scale2_3.set_size_request(150,40)


		self.label2_4=gtk.Label("Time Scaling: ")
		self.scale2_4=gtk.HScale()
		self.scale2_4.set_range(0,8)
		self.scale2_4.set_increments(0.1,1)
		self.scale2_4.set_digits(2)
		self.scale2_4.set_size_request(150,40)


		self.button2_1 = gtk.CheckButton("Time Reversal")
		self.button2_1.set_active(False)
		self.button2_1.unset_flags(gtk.CAN_FOCUS)


		self.button2_2 = gtk.CheckButton("Select for Modulation ")
		self.button2_2.set_active(False)
		self.button2_2.unset_flags(gtk.CAN_FOCUS)

		self.button2_3 = gtk.CheckButton("Select for Mixing ")
		self.button2_3.set_active(False)
		self.button2_3.unset_flags(gtk.CAN_FOCUS)
	
		
		self.button_play2_1=gtk.Button("PLAY")
		self.button_play2_1.set_size_request(50,30)
		self.button_play2_1.connect("clicked",self.on_clicked,1)


		self.pause_button2=gtk.Button("PAUSE")
		self.pause_button2.set_size_request(60,30)
		self.pause_button2.connect("clicked",self.pause,1)
		
		self.pause_flag2=0
		self.pid2=0


		self.stop2=gtk.Button("STOP")
		self.stop2.set_size_request(50,30)
		self.stop2.connect("clicked",self.stop,1)
		fixed.put(self.stop2,480,500)


		fixed.put(self.label2,350,50)
		fixed.put(self.label2_1,350,160)
		fixed.put(self.scale2_1,350,180)
		fixed.put(self.label2_3,350,250)
		fixed.put(self.scale2_3,350,270)
		fixed.put(self.label2_4,350,320)
		fixed.put(self.scale2_4,350,350)
		fixed.put(self.button2_1,350,400)
		fixed.put(self.button2_2,350,425)
		fixed.put(self.button2_3,350,450)
		fixed.put(self.button_play2_1,350,500)
		fixed.put(self.pause_button2,420,500)
		fixed.put(self.file_chooser_button2,350,100)


		self.label3=gtk.Label("Wave 3 :")

		self.file_chooser_button3=gtk.FileChooserButton("Select .wav file",None)
		self.file_chooser_button3.add_filter(file_extention)
		self.file_chooser_button3.connect("file-set",self.file_selected,2)
		self.file_chooser_button3.set_tooltip_text("Select File")
		self.file_chooser_button3.set_size_request(160,40)

		self.label3_1=gtk.Label("Amplitude: ")
		self.scale3_1=gtk.HScale()
		self.scale3_1.set_range(0,5)
		self.scale3_1.set_increments(0.1,1)
		self.scale3_1.set_value(1)
		self.scale3_1.set_digits(1)
		self.scale3_1.set_size_request(150,40)


		self.label3_3=gtk.Label("Time Shift: ")
		self.scale3_3=gtk.HScale()
		self.scale3_3.set_range(-1,1)
		self.scale3_3.set_increments(0.125,1)
		self.scale3_3.set_digits(1)
		self.scale3_3.set_size_request(150,40)


		self.label3_4=gtk.Label("Time Scaling: ")
		self.scale3_4=gtk.HScale()
		self.scale3_4.set_range(0,8)
		self.scale3_4.set_increments(0.1,1)
		self.scale3_4.set_digits(2)
		self.scale3_4.set_size_request(150,40)


		self.button3_1 = gtk.CheckButton("Time Reversal")
		self.button3_1.set_active(False)
		self.button3_1.unset_flags(gtk.CAN_FOCUS)


		self.button3_2 = gtk.CheckButton("Select for Modulation ")
		self.button3_2.set_active(False)
		self.button3_2.unset_flags(gtk.CAN_FOCUS)

		self.button3_3 = gtk.CheckButton("Select for Mixing ")
		self.button3_3.set_active(False)
		self.button3_3.unset_flags(gtk.CAN_FOCUS)
		
		
		self.button_play3_1=gtk.Button("PLAY")
		self.button_play3_1.set_size_request(50,30)
		self.button_play3_1.connect("clicked",self.on_clicked,2)


		self.pause_button3=gtk.Button("PAUSE")
		self.pause_button3.set_size_request(60,30)
		self.pause_button3.connect("clicked",self.pause,2)
		
		self.pause_flag3=0
		self.pid3=0


		self.stop3=gtk.Button("STOP")
		self.stop3.set_size_request(50,30)
		self.stop3.connect("clicked",self.stop,2)
		fixed.put(self.stop3,780,500)


		fixed.put(self.label3,650,50)
		fixed.put(self.label3_1,650,160)
		fixed.put(self.scale3_1,650,180)
		fixed.put(self.label3_3,650,250)
		fixed.put(self.scale3_3,650,270)
		fixed.put(self.label3_4,650,320)
		fixed.put(self.scale3_4,650,350)
		fixed.put(self.button3_1,650,400)
		fixed.put(self.button3_2,650,425)
		fixed.put(self.button3_3,650,450)
		fixed.put(self.button_play3_1,650,500)
		fixed.put(self.pause_button3,720,500)
		fixed.put(self.file_chooser_button3,650,100)
		

		self.button_play4=gtk.Button("MODULATE AND PLAY")
		self.button_play4.set_size_request(160,40)
		self.button_play4.connect("clicked",self.on_clicked,4)
		fixed.put(self.button_play4,200,550)
		
		
		self.button_play5=gtk.Button("MIX AND PLAY")
		self.button_play5.set_size_request(160,40)
		self.button_play5.connect("clicked",self.on_clicked,3)
		fixed.put(self.button_play5,600,550)
		
		self.record=gtk.Label("Recording File Name")
		
		fixed.put(self.record,100,620)

		self.input = gtk.Entry(12)
		fixed.put(self.input,100,650)

		self.start_record=gtk.Button("START RECORDING")
		self.start_record.set_size_request(160,40)
		self.start_record.connect("clicked",self.on_clicked,5)
		fixed.put(self.start_record,300,640)

		self.background.add(fixed)
		self.background.show_all()
		self.background.connect("destroy",self.destroy)


	def file_selected(self, widget,value):
		file_list[value]=widget.get_filename()


	
	def on_clicked(self,widget,value):
		if value<=2:
			w=Wave(file_list[value])
			if value==0:
				magnitude_of_amp=self.scale1.get_value()
				magnitude_of_timeshift=self.scale3.get_value()
				magnitude_of_timescale=self.scale4.get_value()
				wave_reversal=self.button1.get_active()
				w.amplitude(magnitude_of_amp)
				w.time_reversal(wave_reversal)
				w.time_shift(magnitude_of_timeshift)
				w.time_scaling(magnitude_of_timescale)
				w.quit(output_list[value])
			elif value==1:
				magnitude_of_amp=self.scale2_1.get_value()
				magnitude_of_timeshift=self.scale2_3.get_value()
				magnitude_of_timescale=self.scale2_4.get_value()
				wave_reversal=self.button2_1.get_active()
				w.amplitude(magnitude_of_amp)
				w.time_reversal(wave_reversal)
				w.time_shift(magnitude_of_timeshift)
				w.time_scaling(magnitude_of_timescale)
				w.quit(output_list[value])
			else:
				magnitude_of_amp=self.scale3_1.get_value()
				magnitude_of_timeshift=self.scale3_3.get_value()
				magnitude_of_timescale=self.scale3_4.get_value()
				wave_reversal=self.button3_1.get_active()
				w.amplitude(magnitude_of_amp)
				w.time_reversal(wave_reversal)
				w.time_shift(magnitude_of_timeshift)
				w.time_scaling(magnitude_of_timescale)
				w.quit(output_list[value])

		else:
			if value==3:
				ans_list=[]	
				p=None
				q=None
				r=None
				sample_width=None
				if file_list[0]!='' and self.button3.get_active():
					p=Wave(file_list[0])
					magnitude_of_amp=self.scale1.get_value()
					magnitude_of_timeshift=self.scale3.get_value()
					magnitude_of_timescale=self.scale4.get_value()
					wave_reversal=self.button1.get_active()
					p.amplitude(magnitude_of_amp)
					p.time_reversal(wave_reversal)
					p.time_shift(magnitude_of_timeshift)
					p.time_scaling(magnitude_of_timescale)
				if file_list[1]!='' and self.button2_3.get_active():
					q=Wave(file_list[1])
					magnitude_of_amp=self.scale2_1.get_value()
					magnitude_of_timeshift=self.scale2_3.get_value()
					magnitude_of_timescale=self.scale2_4.get_value()
					wave_reversal=self.button2_1.get_active()
					q.amplitude(magnitude_of_amp)
					q.time_reversal(wave_reversal)
					q.time_shift(magnitude_of_timeshift)
					q.time_scaling(magnitude_of_timescale)
				if file_list[2]!='' and self.button3_3.get_active():
					r=Wave(file_list[2])
					magnitude_of_amp=self.scale3_1.get_value()
					magnitude_of_timeshift=self.scale3_3.get_value()
					magnitude_of_timescale=self.scale3_4.get_value()
					wave_reversal=self.button3_1.get_active()
					r.amplitude(magnitude_of_amp)
					r.time_reversal(wave_reversal)
					r.time_shift(magnitude_of_timeshift)
					r.time_scaling(magnitude_of_timescale)
				min_value=-32768
				max_value=32767
				length_list=0
				if p:
					sample_width=p.sample_width
					frame_rate=p.frame_rate
					num_channel=p.num_channel
					for i in xrange (0,len(p.samples)):
						ans_list.append(p.samples[i])
					length_list=len(ans_list)
				if q:
					if sample_width:
						m=max(len(q.samples),len(ans_list))
						for i in xrange(0,m):
							if i>=len(ans_list):
								ans_list.append(q.samples[i])
							elif i<len(q.samples):
								ans_list[i]+=q.samples[i]
							elif i>=len(q.samples):
								break
						length_list=len(ans_list)
					else:
						sample_width=q.sample_width
						frame_rate=q.frame_rate
						num_channel=q.num_channel
						for i in xrange (0,len(q.samples)):
							ans_list.append(q.samples[i])
						length_list=len(ans_list)
				if r:
					if sample_width:
						for i in xrange(0,max(len(ans_list),len(r.samples))):
							if i>=len(ans_list):
								ans_list.append(r.samples[i])
							elif i<len(r.samples):
								ans_list[i]+=r.samples[i]
							elif i>=len(r.samples):
								break
						length_list=len(ans_list)
					else:
						sample_width=r.sample_width
						frame_rate=r.frame_rate
						num_channel=r.num_channel
						for i in xrange (0,len(r.samples)):
							ans_list.append(r.samples[i])
						length_list=len(ans_list)

				for i in xrange(0,length_list):
					if ans_list[i]>max_value:
						ans_list[i]=max_value
					if ans_list[i]<min_value:
						ans_list[i]=min_value

				num_frame=length_list/num_channel 
				new_file=output_list[value]
				if sample_width==1: 
					fmt="%iB" % num_frame*num_channel 
				else: 
					fmt="%ih" % num_frame*num_channel
				data=struct.pack(fmt,*(ans_list))
				new_file_ptr=wave.open(new_file,'w')
				new_file_ptr.setframerate(frame_rate) 
				new_file_ptr.setnframes(num_frame) 
				new_file_ptr.setsampwidth(sample_width) 
				new_file_ptr.setnchannels(num_channel) 
				new_file_ptr.writeframes(data) 
				new_file_ptr.close()

			elif value==4:
				ans_list=[]	
				p=None
				q=None
				r=None
				sample_width=None
				if file_list[0]!='' and self.button2.get_active():
					p=Wave(file_list[0])
					magnitude_of_amp=self.scale1.get_value()
					magnitude_of_timeshift=self.scale3.get_value()
					magnitude_of_timescale=self.scale4.get_value()
					wave_reversal=self.button1.get_active()
					p.amplitude(magnitude_of_amp)
					p.time_reversal(wave_reversal)
					p.time_shift(magnitude_of_timeshift)
					p.time_scaling(magnitude_of_timescale)
				if file_list[1]!='' and self.button2_2.get_active():
					q=Wave(file_list[1])
					magnitude_of_amp=self.scale2_1.get_value()
					magnitude_of_timeshift=self.scale2_3.get_value()
					magnitude_of_timescale=self.scale2_4.get_value()
					wave_reversal=self.button2_1.get_active()
					q.amplitude(magnitude_of_amp)
					q.time_reversal(wave_reversal)
					q.time_shift(magnitude_of_timeshift)
					q.time_scaling(magnitude_of_timescale)
				if file_list[2]!='' and self.button3_2.get_active():
					r=Wave(file_list[2])
					magnitude_of_amp=self.scale3_1.get_value()
					magnitude_of_timeshift=self.scale3_3.get_value()
					magnitude_of_timescale=self.scale3_4.get_value()
					wave_reversal=self.button3_1.get_active()
					r.amplitude(magnitude_of_amp)
					r.time_reversal(wave_reversal)
					r.time_shift(magnitude_of_timeshift)
					r.time_scaling(magnitude_of_timescale)
				min_value=-32768
				max_value=32767
				length_list=0
				if p:
					sample_width=p.sample_width
					frame_rate=p.frame_rate
					num_channel=p.num_channel
					for i in xrange (0,len(p.samples)):
						ans_list.append(p.samples[i])
					length_list=len(ans_list)
				if q:
					if sample_width:
						min1=min(len(q.samples),len(ans_list))
						ans_list=ans_list[0:min1:1]
						for i in xrange(0,min1):
								ans_list[i]*=q.samples[i]
						length_list=len(ans_list)
					else:
						sample_width=q.sample_width
						frame_rate=q.frame_rate
						num_channel=q.num_channel
						for i in xrange (0,len(q.samples)):
							ans_list.append(q.samples[i])
						length_list=len(ans_list)
				if r:
					if sample_width:
						min1=min(len(r.samples),len(ans_list))
						ans_list=ans_list[0:min1:1]
						for i in xrange(0,min1):
								ans_list[i]*=r.samples[i]
						length_list=len(ans_list)
					else:
						sample_width=r.sample_width
						frame_rate=r.frame_rate
						num_channel=r.num_channel
						for i in xrange (0,len(r.samples)):
							ans_list.append(r.samples[i])
						length_list=len(ans_list)

				for i in xrange(0,length_list):
					if ans_list[i]>max_value:
						ans_list[i]=max_value
					if ans_list[i]<min_value:
						ans_list[i]=min_value

				num_frame=length_list/num_channel 
				new_file=output_list[value]
				if sample_width==1: 
					fmt="%iB" % num_frame*num_channel 
				else: 
					fmt="%ih" % num_frame*num_channel
				data=struct.pack(fmt,*(ans_list))
				new_file_ptr=wave.open(new_file,'w')
				new_file_ptr.setframerate(frame_rate) 
				new_file_ptr.setnframes(num_frame) 
				new_file_ptr.setsampwidth(sample_width) 
				new_file_ptr.setnchannels(num_channel) 
				new_file_ptr.writeframes(data) 
				new_file_ptr.close()

			elif value==5:
				filename=self.input.get_text()
				record_to_file(filename+".wav")
				print "Done"			
 
			
		if value<=4:
			if value==3 or value==4:
				v=os.fork()
				if v==0:
					CHUNK = 1024
					wf = wave.open(output_list[value], 'rb')
					p = pyaudio.PyAudio()
					stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
								                channels=wf.getnchannels(),
										                rate=wf.getframerate(),
											                output=True)

					data = wf.readframes(CHUNK)
					while data != '':
					  	stream.write(data)
						data = wf.readframes(CHUNK)
					stream.stop_stream()
					stream.close()
					p.terminate()
					exit(0)
				
			if value==2:
				if self.pause_flag3==2:
					os.kill(self.pid3,signal.SIGCONT)
					self.pause_flag3=1
				else:
					self.pid3=os.fork()
					if(self.pid3==0):
						CHUNK = 1024
						wf = wave.open(output_list[value], 'rb')
						p = pyaudio.PyAudio()
						stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
							                channels=wf.getnchannels(),
									                rate=wf.getframerate(),
										                output=True)

						data = wf.readframes(CHUNK)
						while data != '':
				  		    stream.write(data)
						    data = wf.readframes(CHUNK)
						stream.stop_stream()
						stream.close()
						p.terminate()
						exit(0)

			elif value==1:
				if self.pause_flag2==2:
					os.kill(self.pid2,signal.SIGCONT)
					self.pause_flag2=1
				else:
					self.pid2=os.fork()
					if(self.pid2==0):
						CHUNK = 1024
						wf = wave.open(output_list[value], 'rb')
						p = pyaudio.PyAudio()
						stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
							                channels=wf.getnchannels(),
									                rate=wf.getframerate(),
										                output=True)

						data = wf.readframes(CHUNK)
						while data != '':
				  		    stream.write(data)
						    data = wf.readframes(CHUNK)
						stream.stop_stream()
						stream.close()
						p.terminate()
						exit(0)

			elif value==0:
				if self.pause_flag1==2:
					os.kill(self.pid1,signal.SIGCONT)
					self.pause_flag1=1
				else:
					self.pid1=os.fork()
					if(self.pid1==0):
						CHUNK = 1024
						wf = wave.open(output_list[value], 'rb')
						p = pyaudio.PyAudio()
						stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
							                channels=wf.getnchannels(),
									                rate=wf.getframerate(),
										                output=True)

						data = wf.readframes(CHUNK)
						while data != '':
				  		    stream.write(data)
						    data = wf.readframes(CHUNK)
						stream.stop_stream()
						stream.close()
						p.terminate()
						exit(0)


	def pause(self,widget,value):
		if value==2:
			os.kill(self.pid3,signal.SIGSTOP)
			self.pause_flag3=2
		elif value==1:
			os.kill(self.pid2,signal.SIGSTOP)
			self.pause_flag2=2
		elif value==0:
			os.kill(self.pid1,signal.SIGSTOP)
			self.pause_flag1=2

	def stop(self,widget,value):
		if value==2:
			os.kill(self.pid3,9)
		elif value==1:
			os.kill(self.pid2,9)
		elif value==0:
			os.kill(self.pid1,9)


	def main(self):
	 	gtk.main()          

if __name__ =="__main__":
	background=mixer()
	background.main()

from pyftdi.pyftdi.ftdi import *
from FlashDevice import NandIO

class NandIOFtdi(NandIO):

	def __init__(self, do_slow=False):
                self.Ftdi = None
                super(NandIOFTdi, self).__init__(do_slow)

        def _setupDevice(self):
		self.Ftdi = Ftdi()
		self.Ftdi.open(0x0403,0x6010,interface=1)
		self.Ftdi.set_bitmode(0, self.Ftdi.BITMODE_MCU)

		if (self.Slow==True):
			# Clock FTDI chip at 12MHz instead of 60MHz
			self.Ftdi.write_data(Array('B', [Ftdi.ENABLE_CLK_DIV5]))
		else:
			self.Ftdi.write_data(Array('B', [Ftdi.DISABLE_CLK_DIV5]))

		self.Ftdi.set_latency_timer(1)
		self.Ftdi.purge_buffers()
		self.Ftdi.write_data(Array('B', [Ftdi.SET_BITS_HIGH,0x0,0x1]))
                
        def waitReady(self):
		while 1:
			self.Ftdi.write_data(Array('B', [Ftdi.GET_BITS_HIGH]))
			data = self.Ftdi.read_data_bytes(1)
			if data[0]&2==0x2:
				return
			else:
				if self.Debug>0:
					print 'Not Ready', data
		return

	def nandRead(self,cl,al,count):
		cmds=[]
		cmd_type=0
		if cl==1:
			cmd_type|=self.ADR_CL
		if al==1:
			cmd_type|=self.ADR_AL

		cmds+=[Ftdi.READ_EXTENDED, cmd_type, 0]

		for i in range(1,count,1):
			cmds+=[Ftdi.READ_SHORT, 0]

		cmds.append(Ftdi.SEND_IMMEDIATE)
		self.Ftdi.write_data(Array('B', cmds))
		if (self.getSlow()):
			data = self.Ftdi.read_data_bytes(count*2)
			data = data[0:-1:2]
		else:
			data = self.Ftdi.read_data_bytes(count)
		return data.tolist()

	def nandWrite(self,cl,al,data):
		cmds=[]
		cmd_type=0
		if cl==1:
			cmd_type|=self.ADR_CL
		if al==1:
			cmd_type|=self.ADR_AL                        
		if not self.WriteProtect:
			cmd_type|=self.ADR_WP

		cmds+=[Ftdi.WRITE_EXTENDED, cmd_type, 0, ord(data[0])]
		for i in range(1,len(data),1):
			#if i == 256:
			#	cmds+=[Ftdi.WRITE_SHORT, 0, ord(data[i])]
			cmds+=[Ftdi.WRITE_SHORT, 0, ord(data[i])]
		self.Ftdi.write_data(Array('B', cmds))


	def readSeq(self,pageno,remove_oob=False,raw_mode=False):
		page=[]
		self.sendCmd(self.NAND_CMD_READ0)
		self.waitReady()
		self.sendAddr(pageno<<8,self.AddrCycles)
		self.waitReady()

		bad_block=False

		for i in range(0,self.PagePerBlock,1):
			page_data = self.readFlashData(self.RawPageSize)

			if i==0 or i==1:
				if page_data[self.PageSize+5]!=0xff:
					bad_block = True

			if remove_oob:
				page += page_data[0:self.PageSize]
			else:
				page += page_data

			self.waitReady()

		self.Ftdi.write_data(Array('B', [Ftdi.SET_BITS_HIGH,0x1,0x1]))
		self.Ftdi.write_data(Array('B', [Ftdi.SET_BITS_HIGH,0x0,0x1]))

		data=''

		if bad_block and not raw_mode:
			print '\nSkipping bad block at %d' % (pageno/self.PagePerBlock)
		else:
			for ch in page:
				data+=chr(ch)

		return data

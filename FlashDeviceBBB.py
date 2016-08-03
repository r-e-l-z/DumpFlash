import Adafruit_BBIO.GPIO as GPIO
from FlashDevice import NandIO

class Ports:
        d0  = "P8_7"
        d1  = "P8_8"
        d2  = "P8_9"
        d3  = "P8_10"
        d4  = "P8_11"
        d5  = "P8_12"
        d6  = "P8_13"
        d7  = "P8_14"
        _ce = "P8_15"
        _we = "P8_16"
        _re = "P8_17"
        cle = "P8_18"
        ale = "P8_19"
        ry  = "P8_26"
        io = [d0, d1, d2, d3, d4, d5, d6, d7]

class NandIOBBB(NandIO):
                
        def _setupDevice(self):
                print "_setupDevice"

                #setup ports
                for d in Ports.io:
                        GPIO.setup(d,  GPIO.IN)
                GPIO.setup(Ports._ce, GPIO.OUT)
                GPIO.setup(Ports._we, GPIO.OUT)
                GPIO.setup(Ports._re, GPIO.OUT)
                GPIO.setup(Ports.cle, GPIO.OUT)
                GPIO.setup(Ports.ale, GPIO.OUT)
                GPIO.setup(Ports.ry, GPIO.IN)
                
                #set initial port values
                GPIO.output(Ports._ce, GPIO.HIGH)
                GPIO.output(Ports.cle, GPIO.LOW)
                GPIO.output(Ports.ale, GPIO.LOW)
                GPIO.output(Ports._re, GPIO.HIGH)
                GPIO.output(Ports._we, GPIO.HIGH)

                #send reset device cmd
                self.sendCmd(self.NAND_CMD_RESET)

        def chipEnable(self):
                GPIO.output(Ports._ce, GPIO.LOW)

        def chipDisable(self):
                GPIO.output(Ports._ce, GPIO.HIGH)
                
        def waitReady(self):
                while not GPIO.input(Ports.ry):
                        if self.Debug>0:
                                print 'ry Not Ready'     

        def writeDataByte(self, data):
                # latch all data pins
                for p in Ports.io:
                        GPIO.output(p, data & 1)
                        data >>= 1
                
                # jiggle the write enable line
                GPIO.output(Ports._we, GPIO.LOW)
                # do we need a sleep here?
                GPIO.output(Ports._we, GPIO.HIGH)
                
        def readDataByte(self):
                # jiggle the read enable line
                GPIO.output(Ports._re, GPIO.LOW)
                #sleep(0.001)
                data = 0
                for p in reversed(Ports.io):
                        data <<= 1
                        b = GPIO.input(p)
                        #print "port %s, bit %d" % (p, b) 
                        data |= b
                        #print "data is 0x%x" % data
                # do we need a sleep here?
                GPIO.output(Ports._re, GPIO.HIGH)


                return data

        def configIOread(self):
                for d in Ports.io:
                        GPIO.setup(d, GPIO.IN)

        def configIOwrite(self):
                for d in Ports.io:
                        GPIO.setup(d, GPIO.OUT)

# note: data is received as a string???
	def nandWrite(self, cl, al, data):
                #print "nandWrite: data %s" % [hex(ord(d)) for d in  data]
                assert cl == 0 or al == 0
                cmd_port = -1
                self.configIOwrite()

		if cl == 1:
                        cmd_port = Ports.cle
		if al == 1:
                        cmd_port = Ports.ale
                
                # raise command/address latch lien
                if cmd_port != -1:
                        GPIO.output(cmd_port, GPIO.HIGH)
                
                # write data bytes
                for d in data:
                        self.writeDataByte(ord(d))
                        
                # lower command/address latch line
                if cmd_port != -1:
                        GPIO.output(cmd_port, GPIO.LOW)

	def nandRead(self, cl, al, numbytes):
                #print "nandRead: numbytes %d" % numbytes
                data = []
                self.configIOread()

                for i in range(numbytes):
                        d = self.readDataByte()
                        # print "nandRead: read byte 0x%x" % d
                        data.append(d)

                #print "nandRead: data %s" % map(hex, data)
                return data

	def __readSeq(self,pageno,remove_oob=False,raw_mode=False):
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

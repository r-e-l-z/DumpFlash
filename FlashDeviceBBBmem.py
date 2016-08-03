from FlashDevice import NandIO
from collections import namedtuple
from mmap import mmap
import struct


# GPIO bases
GPIO0             = 0x44E07000
GPIO1             = 0x4804C000
GPIO2             = 0x481AC000
GPIO3             = 0x481AE000

# memory range
GPIO_START = GPIO0
GPIO_SIZE  = GPIO3 + 0x2000 - GPIO_START


# control register offsets
GPIO_OE           = 0x134
GPIO_DATAIN       = 0x138
GPIO_SETDATAOUT   = 0x194
GPIO_CLEARDATAOUT = 0x190

# directions
IN   = 0
OUT  = 1
# value
HIGH = 1
LOW  = 0


Port = namedtuple('port', ['gpio', 'mask', 'addr', 'repr'])

# maping of ports to gpio and offset
class Ports:
        d0  = Port(GPIO2, 1<<2,  0x44e10890, "P8_7") 
        d1  = Port(GPIO2, 1<<3,  0x44e10894, "P8_8") 
        d2  = Port(GPIO2, 1<<5,  0x44e1089c, "P8_9")
        d3  = Port(GPIO2, 1<<4,  0x44e10898, "P8_10")
        d4  = Port(GPIO1, 1<<13, 0x44e10834, "P8_11")
        d5  = Port(GPIO1, 1<<12, 0x44e10830, "P8_12")
        d6  = Port(GPIO0, 1<<23, 0x44e10824, "P8_13")
        d7  = Port(GPIO0, 1<<26, 0x44e10828, "P8_14")
        _ce = Port(GPIO1, 1<<15, 0x44e1083c, "P8_15")
        _we = Port(GPIO1, 1<<14, 0x44e10838, "P8_16")
        _re = Port(GPIO0, 1<<27, 0x44e1082c, "P8_17")
        cle = Port(GPIO2, 1<<1,  0x44e1088c, "P8_18")
        ale = Port(GPIO0, 1<<22, 0x44e10820, "P8_19")
        ry  = Port(GPIO1, 1<<29, 0x44e1087c, "P8_26")
        io  = [d0, d1, d2, d3, d4, d5, d6, d7]


class NandIOBBBmem(NandIO):

        def __init__(self, do_slow=False):
                # define memory map
                self.f   = open("/dev/mem", "r+b")
                self.mem = mmap(self.f.fileno(), GPIO_SIZE, offset=GPIO_START)
#                super(NandIOBBBmem, self).__init__(do_slow)


        def _setupDevice(self):
                print "_setupDevice"
                
                #setup ports
                for d in Ports.io:
                        self.setPortDirection(d,  IN)
                self.setPortDirection(Ports._ce, OUT)
                self.setPortDirection(Ports._we, OUT)
                self.setPortDirection(Ports._re, OUT)
                self.setPortDirection(Ports.cle, OUT)
                self.setPortDirection(Ports.ale, OUT)
                self.setPortDirection(Ports.ry, IN)
                
                #set initial port values
                self.setPortValue(Ports._ce, HIGH)
                self.setPortValue(Ports.cle, LOW)
                self.setPortValue(Ports.ale, LOW)
                self.setPortValue(Ports._re, HIGH)
                self.setPortValue(Ports._we, HIGH)

                #send reset device cmd
                self.sendCmd(self.NAND_CMD_RESET)

        # get 32bit register, and unpack the string
        def getReg(self, addr):
                offset = addr - GPIO_START
                return struct.unpack("<L", self.mem[offset:offset+4])[0]

        # pack string, and set 32bit register
        def setReg(self, addr, value):
                offset = addr - GPIO_START
                self.mem[offset:offset+4] = struct.pack("<L", value)

        def setPortDirection(self, port, direction):
                oe_reg_addr = port.gpio + GPIO_OE
                oe_reg_val  = self.getReg(oe_reg_addr)
                
                print "oe_reg_addr 0x%08x, oe_reg_val 0x%08x" % (oe_reg_addr, oe_reg_val)
                if direction == OUT:
                        oe_reg_val |= port.mask
                elif direction == IN:
                        oe_reg_val &= port.mask

                self.setReg(oe_reg_addr, oe_reg_val)
                
        def setPortValue(self, port, value):
                reg_addr = (port.gpio + GPIO_SETDATAOUT) if value == HIGH else (port.gpio + GPIO_CLEARDATAOUT)
                self.setReg(reg_addr, port.mask)

        def getPortValue(self, port):
                datain = self.getReg(port.gpio + GPIO_DATAIN)
                value  = datain & port.mask == port.mask
                print "getPortValue 0x%08x" % value

                assert value == HIGH or value == LOW
                return value
                
        def chipEnable(self):
                self.setPortValue(Ports._ce, LOW)

        def chipDisable(self):
                self.setPortValue(Ports._ce, HIGH)
                
        def waitReady(self):
                while not self.getReg(Ports.ry.addr):
                        if self.Debug>0:
                                print 'ry Not Ready'     

        def writeDataByte(self, data):
                # latch all data pins
                for p in Ports.io:
                        self.setPortValue(p, data & 1)
                        data >>= 1
                
                # jiggle the write enable line
                self.setPortValue(Ports._we, LOW)
                # do we need a sleep here?
                self.setPortValue(Ports._we, HIGH)
                
        def readDataByte(self):
                # jiggle the read enable line
                self.setPortValue(Ports._re, LOW)

                data = 0
                for p in reversed(Ports.io):
                        data <<= 1
                        b = self.getPortValue(p)
                        print "port %s, bit %d" % (p.repr, b) 
                        data |= b
                        #rint "data is 0x%x" % data
                # do we need a sleep here?
                self.setPortValue(Ports._re, HIGH)


                return data

        def configIOread(self):
                for d in Ports.io:
                        self.setPortDirection(d, IN)

        def configIOwrite(self):
                for d in Ports.io:
                        self.setPortDirection(d, OUT)

# note: data is received as a string???
	def nandWrite(self, cl, al, data):
                print "nandWrite: data %s" % [hex(ord(d)) for d in  data]
                assert cl == 0 or al == 0
                cmd_port = -1
                self.configIOwrite()

		if cl == 1:
                        cmd_port = Ports.cle
		if al == 1:
                        cmd_port = Ports.ale
                
                # raise command/address latch lien
                if cmd_port != -1:
                        self.setPortValue(cmd_port, HIGH)
                
                # write data bytes
                for d in data:
                        self.writeDataByte(ord(d))
                        
                # lower command/address latch line
                if cmd_port != -1:
                        self.setPortValue(cmd_port, LOW)

	def nandRead(self, cl, al, numbytes):
                print "nandRead: numbytes %d" % numbytes
                data = []
                self.configIOread()

                for i in range(numbytes):
                        d = self.readDataByte()
                        print "nandRead: read byte 0x%x" % d
                        data.append(d)

                print "nandRead: data %s" % map(hex, data)
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

import serial
from serial.tools import list_ports
from serial import SerialException
import time
import sys

class CoboltLaser():
    '''Creates a laser object using either COM-port or serial number to connect to laser. \n Will automatically return proper subclass, if applicable'''
    
    def __init__(self, port=None, serialNumber=None, baudrate=115200):
        self.serialNumber=serialNumber
        self.port=port
        self.modelNumber = None
        self.baudrate=baudrate
        self.adress=None
        self.connect()
    
    def __str__(self):
        try:
            return f'Serial number: {self.serialNumber}, Model number: {self.modelNumber}, Wavelength: {"{:.0f}".format(float(self.modelNumber[0:4]))} nm, Type: {self.__class__.__name__}'
        except:
            return f'Serial number: {self.serialNumber}, Model number: {self.modelNumber}'
    
    def connect(self): 
        '''Connects the laser on using a specified COM-port (preferred) or serial number. \n Will throw exception if it cannot connect to specified port or find laser with given serial number'''
        
        if self.port!= None:
            try:
                self.adress=serial.Serial(self.port,self.baudrate, timeout=1)
            except Exception as error:
                self.adress=None
                raise SerialException (f'{self.port} not accesible. Error: {error}')
        

        elif self.serialNumber!= None : 
            ports=list_ports.comports()
            for port in ports:
                try:
                    self.adress=serial.Serial(port.device,baudrate=self.baudrate, timeout=1)
                    sn=self.sendCmd('sn?')
                    self.adress.close()
                    if sn == self.serialNumber:
                        self.port=port.device
                        self.adress=serial.Serial(self.port,baudrate=self.baudrate)
                        break    
                except:
                    pass             
            if self.port==None:
                raise Exception('No laser found')
        if self.adress!=None:
            self._identify_()
        if self.__class__==CoboltLaser:
            self._classify_()



    def _identify_(self): 
        """Fetch Serial number and model number of laser. \n
        Will raise exception and close connection if not connected to a cobolt laser"""
        try:
            firmware = self.sendCmd('gfv?')
            if 'ERROR' in firmware:
                self.disconnect()
                raise Exception('Not a Cobolt laser')
            self.serialNumber = self.sendCmd('sn?') 
            if not '.' in firmware: 
                if '0' in self.serialNumber: 
                    self.modelNumber=f'0{self.serialNumber.partition(string(0))[0]}-04-XX-XXXX-XXX'
                    self.serialNumber=self.serialNumber.partition('0')[2] 
                    while self.serialNumber[0]=='0':
                        self.serialNumber=self.serialNumber[1:]                   
            else:
                self.modelNumber=self.sendCmd('glm?')
        except:
            self.disconnect()
            raise Exception('Not a Cobolt laser')

    def _classify_(self):
        '''Classifies the laser into probler subclass depending on laser type'''
        try:
            if '-06-' in self.modelNumber:
                if '532' in self.modelNumber[0:4] or '561' in self.modelNumber[0:4] or '553' in self.modelNumber[0:4]:
                    self.__class__=CoboltModDPL
                else:
                    self.__class__=CoboltMLD
        except:
            pass
    
    def isConnected(self): 
        """Ask if laser is connected"""
        if self.adress.is_open:
            try:
                test=self.sendCmd('?')
                if test=='OK':
                    return True
                else:
                    return False
            except:
                return False
        else:
            return False
    
    def disconnect(self): 
        '''Disconnect the laser'''
        if self.adress!=None:
            self.adress.close()
            self.serialNumber=None
            self.modelNumber=None
            #clear sn & mn on disconnect?
         
    def turnOn(self):
        '''turn on the laser with the autostart sequence.The laser will await the TEC setpoints and pass a warm-up state'''
        return self.sendCmd(f'@cob1') 


    def turnOff(self):
        '''turn off the laser '''
        return self.sendCmd(f'l0') 
        
    def isOn(self):
        '''Check if laser is turned on '''
        answer=self.sendCmd(f'l?') 
        if answer == '1':
            return True
        else:
            return False

    def interlock(self):
        '''Returns: 0 if closed, 1 if open '''
        return self.sendCmd(f'ilk?')

    def getFault(self):
        '''Get laser fault'''
        faults={'0': '0 - No errors',
        '1':'1 – Temperature error',
        '3':'3 - Interlock error',
        '4':'4 – Constant power time out'}
        fault=self.sendCmd(f'f?')
        try:
            fault=faults.get(fault)
            return fault
        except:
            return fault


    def clearFault(self):
        '''Clear laser fault'''
        return self.sendCmd(f'cf')
    
    def getMode(self):
        '''get operating mode'''
        modes={'0': '0 - Constant Current',
        '1': '1 - Constant Power',
        '2':'2 - Modulation Mode'}
        mode=self.sendCmd(f'gam?')
        try: 
            mode=modes.get(mode)
            return modes.get(mode)
        except:
            return mode

    def getState(self): 
        '''get autostart state'''
        states={'0':'0–Off',
        '1':'1 – Waiting for key',
        '2':'2 – Continuous',
        '3':'3 – On/Off Modulation',
        '4':'4 – Modulation',
        '5':'5 – Fault',
        '6':'6 – Aborted'}
        state=self.sendCmd(f'gom?')
        try:
            state=states.get(state)
            return state
        except:
            return state

        



    def constCurrent(self,current=None):
        '''Enter constant current mode, current in mA ''' 
        if current!=None:
            self.sendCmd(f'slc {current}')
        return self.sendCmd(f'ci')

    def setCurrent(self, current):
        '''Set laser current in mA'''
        return self.sendCmd(f'slc {current}')

    
    def getCurrent(self):
        '''Get laser current in mA '''
        return float(self.sendCmd(f'i?')) #returns mA


    def getCurrentSetpoint(self):
        '''Get laser current in mA '''
        return float(self.sendCmd(f'glc?')) #returns mA



    def constPower(self,power=None):
        '''Enter constant power mode, power in mW''' 
        if power!=None:
            self.sendCmd(f'p {float(power)/1000}')
        return self.sendCmd(f'cp')
    
    def setPower(self, power):
        '''Set laser power in mW '''
        return self.sendCmd(f'p {float(power)/1000}')

    def getPower(self):
        ''' Get laser power in mW'''
        return float(self.sendCmd(f'pa?'))*1000    

    def getPowerSetpoint(self):
        ''' Get laser power setpoint in mW'''
        return float(self.sendCmd(f'p?'))*1000    


    def getOpHours(self):
        ''' Get laser operational hours'''
        return self.sendCmd(f'hrs?')

    def _timeDiff_( self, time_start ):
        '''time in ms'''
        time_diff = 1000 * ( time.perf_counter() - time_start )
        return time_diff


    def sendCmd( self, message, timeout = 1000 ):
        """ Sends a message to the laset and awaits response until timeout (ms).

            :returns:
                The string recieved from the laser
                "SYNTAX ERROR: No response" on a failed attempt.
        """
        time_start = time.perf_counter()
        message += "\r"
        try:
            self.adress.write(message.encode() )
        except: #handle error correctly
            #raise Exception('Write Failed') #returnera sträng eller fel?
            return 'Error: write failed'


        time_stamp = 0
        while ( time_stamp < timeout ):

            try:
                received_string = self.adress.readline().decode()
                time_stamp = self._timeDiff_( time_start )
            except:
                time_stamp = self._timeDiff_( time_start )
                continue


            if ( len( received_string ) > 1 ):
                while ( ( received_string[ -1 ] == '\n' ) or ( received_string[ -1 ] == '\r' ) ):
                    received_string = received_string[ 0 : -1 ]
                    if ( len( received_string ) < 1 ):
                        break
                
                return  received_string

        return "Syntax Error: No response"


class CoboltMLD(CoboltLaser):
    '''For lasers of type MLD'''
    def __init__(self,port=None,serialNumber=None):
        super().__init__(port,serialNumber)

    def modulationMode(self,power=None):
        '''enter modulation mode with the possibility  to set modulation power in mW'''
        if power!=None:
            self.sendCmd(f'slmp {power}')
        return self.sendCmd(f'em')

    def digitalModulation(self,enable):
        '''Enable digital modulation mode by enable=1, turn off by enable=0'''
        return self.sendCmd(f'sdmes {enable}')

    def analogModulation(self,enable):
        '''Enable analog modulation mode by enable=1, turn off by enable=0''' 
        return self.sendCmd(f'sames {enable}')

    def getModulationState(self,type):
        '''get the laser modulation settings as [analog, digital]'''
        dm=self.sendCmd(f'gdmes?')
        am=self.sendCmd(f'games?')
        return [am,dm]

    def setModulationPower(self,power):
        '''set the modulation power in mW'''
        return self.sendCmd(f'slmp {power}')
    
    def getModulationPower(self):
        '''get the modulation power setpoint in mW'''
        return float(self.sendCmd(f'glmp?'))

    def setAnalogImpedance(self,arg):
        '''Set the impedance of the analog modulation by \n
        arg=0 for HighZ and \n
        arg=1 for 50 Ohm '''
        return self.sendCmd(f'salis {arg}')
        
    def getAnalogImpedance(self,arg):
        '''Get the impedance of the analog modulation \n
        return: 0 for HighZ and 1 for 50 Ohm '''
        return self.sendCmd(f'salis {arg}')
        


class CoboltModDPL(CoboltLaser):
    '''For lasers of type ModDPL'''
    def __init__(self,port=None,serialNumber=None):
        super().__init__(port,serialNumber)

    def modulationMode(self,highI=None):
        '''Enter Modulation mode, with possibiity to set the modulation high current level in mA (**kwarg)'''
        if highI!=None:
            self.sendCmd(f'smc {highI}')
        return self.sendCmd(f'em')

    def digitalModulation(self,enable):
        '''Enable digital modulation mode by enable=1, turn off by enable=0'''
        return self.sendCmd(f'sdmes {enable}')

    def analogModulation(self,enable):
        '''Enable analog modulation mode by enable=1, turn off by enable=0''' 
        return self.sendCmd(f'sames {enable}')

    def getModulationState(self):
        '''get the laser modulation settings as [analog, digital]'''
        dm=self.sendCmd(f'gdmes?')
        am=self.sendCmd(f'games?')
        return [am,dm]

    def setModCurrentHigh(self,highI):
        '''Set the modulation high current in mA '''
        return self.sendCmd(f'smc {highI}')
    
    def setModCurrentLow(self,lowI):
        '''Set the modulation low current in mA '''
        return self.sendCmd(f'slth {highI}')
    
    def getModCurrent(self):
        '''Return the modulation currrent setpoints in mA as [highCurrent,lowCurrent]'''
        highI=float(self.sendCmd(f'gmc?'))
        lowI=float(self.sendCmd(f'glth?'))
        return [highI,lowI] 

    def readModTec(self):
        '''Read the temperature of the modulation TEC in °C'''
        return float(self.sendCmd(f'rtec4t?'))

    def setModTec(self, temperature):
        '''Set the temperature of the modulation TEC in °C'''
        return self.sendCmd(f'stec4t {temperature}')

    def getModTecSetpoint(self):
        '''Get the setpoint of the modulation TEC in °C'''
        return float(self.sendCmd(f'gtec4t?'))




def listLasers():
    '''Return a list of laser objects for all cobolt lasers '''
    lasers=[]
    ports=list_ports.comports()
    for port in ports:
        try:
            laser=CoboltLaser(port=port.device)
            if laser.serialNumber==None or laser.serialNumber.startswith('Syntax'):
                del laser
            else:
                lasers.append(laser)
        except:
            pass
    return lasers
    


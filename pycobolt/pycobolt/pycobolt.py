import serial
from serial.tools import list_ports
from serial import SerialException
import logging

logger = logging.getLogger(__name__)


class CoboltLaser:
    """
    Creates a laser object using either COM-port or serial number to connect to laser. Will automatically return proper
    subclass, if applicable
    """

    def __init__(self, port=None, serialnumber=None, baudrate=115200):
        self.serialnumber = serialnumber
        self.port = port
        self.modelnumber = None
        self.baudrate = baudrate
        self.address = None
        self.connect()

    def __str__(self):
        try:
            return f'Serial number: {self.serialnumber}, ' \
                   f'Model number: {self.modelnumber}, ' \
                   f'Wavelength: {self.modelnumber[0:4]:.0f} nm, ' \
                   f'Type: {self.__class__.__name__}'
        except TypeError:
            return f"Serial number: {self.serialnumber}, Model number: {self.modelnumber}"

    def connect(self):
        """
        Connects the laser on using a specified COM-port (preferred) or serial number. Will throw exception if it
        cannot connect to specified port or find laser with given serial number.

        Raises:
            SerialException: serial port error
            RuntimeError: no laser found
        """

        if self.port is not None:
            try:
                self.address = serial.Serial(self.port, self.baudrate, timeout=1)
            except serial.SerialException as err:
                self.address = None
                raise SerialException(f"{self.port} not accessible.") from err

        elif self.serialnumber is not None:
            ports = list_ports.comports()
            for port in ports:
                try:
                    self.address = serial.Serial(port.device, baudrate=self.baudrate, timeout=1)
                    sn = self.send_cmd("sn?")
                    self.address.close()
                    if sn == self.serialnumber:
                        self.port = port.device
                        self.address = serial.Serial(self.port, baudrate=self.baudrate)
                        break
                except (serial.SerialException, RuntimeError):
                    pass
            if self.port is None:
                raise RuntimeError("No laser found")
        if self.address is not None:
            self._identify_()
        if self.__class__ == CoboltLaser:
            self._classify_()

    def _identify_(self):
        """
        Fetch Serial number and model number of laser. Will raise exception and close connection if not connected to
        a Cobolt laser.

        Raises:
            RuntimeError: error identifying the laser model
        """
        try:
            firmware = self.send_cmd("gfv?")
            if "ERROR" in firmware:
                self.disconnect()
                raise RuntimeError("Not a Cobolt laser")
            self.serialnumber = self.send_cmd("sn?")
            if "." not in firmware:
                if "0" in self.serialnumber:
                    self.modelnumber = f"0{self.serialnumber.partition('0')[0]}-04-XX-XXXX-XXX"
                    self.serialnumber = self.serialnumber.partition('0')[2].lstrip('0')
            else:
                self.modelnumber = self.send_cmd("glm?")
        except (RuntimeError, TypeError):
            self.disconnect()
            raise RuntimeError("Not a Cobolt laser")

    def _classify_(self):
        """Classifies the laser into proper subclass depending on laser type"""
        try:
            if "-71-" not in self.modelnumber and "-06-" in self.modelnumber and \
                    ("-91-" in self.modelnumber[0:4] or "-93-" in self.modelnumber[0:4]):
                self.__class__ = Cobolt06DPL
            else:
                self.__class__ = Cobolt06MLD
        except TypeError:
            pass

    def is_connected(self):
        """Ask if laser is connected"""
        try:
            if self.address.is_open:
                return self.send_cmd("?") == "OK"
        except (serial.SerialException, RuntimeError):
            return False
        return False

    def disconnect(self):
        """Disconnect the laser"""
        if self.address is not None:
            self.address.close()
            self.serialnumber = None
            self.modelnumber = None

    def turn_on(self):
        """
        Turn on the laser with the autostart sequence.The laser will await the TEC setpoints and pass a warm-up state
        """
        logger.info("Turning on laser")
        return self.send_cmd("@cob1")

    def turn_off(self):
        """Turn off the laser"""
        logger.info("Turning off laser")
        return self.send_cmd("l0")

    def is_on(self):
        """Ask if laser is turned on"""
        return self.send_cmd("l?") == "1"

    def interlock(self):
        """Returns: 0 if closed, 1 if open"""
        return self.send_cmd("ilk?")

    def get_fault(self):
        """Get laser fault"""
        faults = {
            "0": "0 - No errors",
            "1": "1 - Temperature error",
            "3": "3 - Interlock error",
            "4": "4 - Constant power time out",
        }
        fault = self.send_cmd("f?")
        return faults.get(fault)

    def clear_fault(self):
        """Clear laser fault"""
        return self.send_cmd("cf")

    def get_mode(self):
        """Get operating mode"""
        modes = {
            "0": "0 - Constant Current",
            "1": "1 - Constant Power",
            "2": "2 - Modulation Mode",
        }
        mode = self.send_cmd("gam?")
        return modes.get(mode)

    def get_state(self):
        """Get autostart state"""
        states = {
            "0": "0 - Off",
            "1": "1 - Waiting for key",
            "2": "2 - Continuous",
            "3": "3 - On/Off Modulation",
            "4": "4 - Modulation",
            "5": "5 - Fault",
            "6": "6 - Aborted",
        }
        state = self.send_cmd("gom?")
        return states.get(state)

    def constant_current(self, current=None):
        """Enter constant current mode, current in mA"""
        if current is not None:
            if "-08-" not in self.modelnumber or "-06-" not in self.modelnumber:
                self.send_cmd(f"slc {current / 1000}")
            else:
                self.send_cmd(f"slc {current}")
            logger.info(f"Entering constant current mode with I = {current} mA")
        else:
            logger.info("Entering constant current mode")
        return self.send_cmd("ci")

    def set_current(self, current):
        """Set laser current in mA"""
        logger.info(f"Setting I = {current} mA")
        if "-08-" not in self.modelnumber or "-06-" not in self.modelnumber:
            current = current / 1000
        return self.send_cmd(f"slc {current}")

    def get_current(self):
        """Get laser current in mA"""
        return float(self.send_cmd("i?"))

    def get_current_setpoint(self):
        """Get laser current setpoint in mA"""
        return float(self.send_cmd("glc?"))

    def constant_power(self, power=None):
        """Enter constant power mode, power in mW"""
        if power is not None:
            self.send_cmd(f"p {float(power) / 1000}")
            logger.info(f"Entering constant power mode with P = {power} mW")
        else:
            logger.info("Entering constant power mode")
        return self.send_cmd("cp")

    def set_power(self, power):
        """Set laser power in mW"""
        logger.info(f"Setting P = {power} mW")
        return self.send_cmd(f"p {float(power) / 1000}")

    def get_power(self):
        """Get laser power in mW"""
        return float(self.send_cmd("pa?")) * 1000

    def get_power_setpoint(self):
        """Get laser power setpoint in mW"""
        return float(self.send_cmd("p?")) * 1000

    def get_ophours(self):
        """Get laser operational hours"""
        return self.send_cmd("hrs?")

    def send_cmd(self, message, timeout=1):
        """Sends a message to the laser and awaits response until timeout (in s).

        Returns:
            The response received from the laser as string

        Raises:
            RuntimeError: sending the message failed
        """
        message += "\r"
        utf8_msg = message.encode()
        try:
            self.address.write(utf8_msg)
        except serial.SerialException as e:
            raise RuntimeError("Error: write failed") from e
        else:
            logger.debug(f"sent laser [{self}] message [{utf8_msg}]")

        try:
            self.address.timeout = timeout
            received_string = self.address.readline().decode().rstrip()
        except serial.SerialException:
            raise RuntimeError("Syntax Error: No response")
        else:
            logger.debug(f"received from laser [{self}] message [{received_string}]")

        return received_string

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.turn_off()
        self.disconnect()


class Cobolt06MLD(CoboltLaser):
    """For lasers of type 06-MLD"""

    def __init__(self, port=None, serialnumber=None):
        super().__init__(port, serialnumber)

    def modulation_mode(self, power=None):
        """Enter modulation mode.

        Args:
            power: modulation power (mW)
        """
        logger.info("Entering modulation mode")
        if power is not None:
            self.send_cmd(f"slmp {power}")
        return self.send_cmd("em")

    def digital_modulation(self, enable):
        """Enable digital modulation mode by enable=1, turn off by enable=0"""
        return self.send_cmd(f"sdmes {enable}")

    def analog_modulation(self, enable):
        """Enable analog modulation mode by enable=1, turn off by enable=0"""
        return self.send_cmd(f"sames {enable}")

    def on_off_modulation(self, enable):
        """Enable On/Off modulation mode by enable=1, turn off by enable=0"""
        return self.send_cmd('eoom' if enable else 'xoom')

    def get_modulation_state(self):
        """Get the laser modulation settings as [analog, digital]"""
        dm = self.send_cmd("gdmes?")
        am = self.send_cmd("games?")
        return [am, dm]

    def set_modulation_power(self, power):
        """Set the modulation power in mW"""
        logger.info(f"Setting modulation power = {power} mW")
        return self.send_cmd(f"slmp {power}")

    def get_modulation_power(self):
        """Get the modulation power setpoint in mW"""
        return float(self.send_cmd("glmp?"))

    def set_analog_impedance(self, arg):
        """Set the impedance of the analog modulation.

        Args:
            arg: 0 for HighZ, 1 for 50 Ohm.
        """
        return self.send_cmd(f"salis {arg}")

    def get_analog_impedance(self):
        """Get the impedance of the analog modulation \n
        return: 0 for HighZ and 1 for 50 Ohm"""
        return self.send_cmd("galis?")


class Cobolt06DPL(CoboltLaser):
    """For lasers of type 06-DPL"""

    def __init__(self, port=None, serialnumber=None):
        super().__init__(port, serialnumber)

    def modulation_mode(self, highI=None):
        """Enter Modulation mode, with possibility to set the modulation high current level in mA (**kwarg)"""
        if highI is not None:
            self.send_cmd(f"smc {highI}")
        return self.send_cmd("em")

    def digital_modulation(self, enable):
        """Enable digital modulation mode by enable=1, turn off by enable=0"""
        return self.send_cmd(f"sdmes {enable}")

    def analog_modulation(self, enable):
        """Enable analog modulation mode by enable=1, turn off by enable=0"""
        return self.send_cmd(f"sames {enable}")

    def get_modulation_state(self):
        """Get the laser modulation settings as [analog, digital]"""
        dm = self.send_cmd("gdmes?")
        am = self.send_cmd("games?")
        return [am, dm]

    def set_modulation_current_high(self, highI):
        """Set the modulation high current in mA"""
        return self.send_cmd(f"smc {highI}")

    def set_modulation_current_low(self, lowI):
        """Set the modulation low current in mA"""
        return self.send_cmd(f"slth {lowI}")

    def get_modulation_current(self):
        """Return the modulation current setpoints in mA as [highCurrent,lowCurrent]"""
        highI = float(self.send_cmd("gmc?"))
        lowI = float(self.send_cmd("glth?"))
        return [highI, lowI]

    def get_modulation_tec(self):
        """Read the temperature of the modulation TEC in °C"""
        return float(self.send_cmd("rtec4t?"))

    def set_modulation_tec(self, temperature):
        """Set the temperature of the modulation TEC in °C"""
        return self.send_cmd(f"stec4t {temperature}")

    def get_modulation_tec_setpoint(self):
        """Get the setpoint of the modulation TEC in °C"""
        return float(self.send_cmd("gtec4t?"))


def list_lasers():
    """Return a list of laser objects for all cobolt lasers connected to the computer"""
    lasers = []
    ports = list_ports.comports()
    for port in ports:
        try:
            laser = CoboltLaser(port=port.device)
            if laser.serialnumber is None or laser.serialnumber.startswith("Syntax"):
                del laser
            else:
                lasers.append(laser)
        except (serial.SerialException, RuntimeError):
            pass
    return lasers

from serial import Serial, SerialException
import time
import sys
import glob

class SyncBox:

    
    def __init__(self, num_volumes=16, num_slices=1, trigger_slice=1, trigger_volume=1, pulse_length=100, 
    TR_time=3000, optional_trigger_slice=0, optional_trigger_volume=0, simulation = True):
        """
        This class finds and establishes serial connection with the SyncBox in serial mode.

        Parameters
        -------
        num_volumes
            Number of volumes
        num_slices
            Number of slices in each volume
        trigger_slice
            Slice number to trigger on
        trigger_volume
            How often to trigger on a volume. 
        pulse_length
            Pulse length in ms. Only needed in simulation mode.
        TR_time
            TR time in ms. Only needed in simulation mode.
        optional_trigger_slice
            0 for triggering on the slice typed above. 1 for triggering on each slice. 2 for triggering on random slice. (1 and 2 override above settings)
        optional_trigger_volume
            0 for triggering on each volume typed above. 1 for triggering on each volume. 2 for triggering on random volume. (1 and 2 override above settings)
        simulation
            False for synchronization mode. True for simulation mode.
        """
        
        self.num_volumes = num_volumes
        self.num_slices = num_slices
        self.trigger_slice = trigger_slice
        self.trigger_volume = trigger_volume
        self.pulse_length = pulse_length
        self.TR_time = TR_time
        self.optional_trigger_slice = optional_trigger_slice
        self.optional_trigger_volume = optional_trigger_volume
        self.simulation = simulation

        self.port = self._findSyncBox()
        self._configure()
    

    def readCurrentInputBuffer(self) -> str:
        """
        This function will read the current input buffer from the SyncBox 
        even if it is empty. Useful for use within loops.
        
        Return
        ------
        trigger : str
            "s" for synchronization
            "a" for left thumb on ResponseGrips
            "b" for left index on ResponseGrips
            "c" for right index on ResponseGrips
            "d" for right thumb on ResponseGrips
        
        """
        out = self.port.read(self.port.in_waiting)
        return out.decode("utf-8")
        


    def getTrigger(self, timeout = 0) -> str:
        """
        This function returns the trigger sent from the SyncBox to the computer.
        
        Parameters
        ----------
        timeout : float
            Number of seconds to wait for the trigger to be returned from SyncBox
            if set to None, it will wait an unlimited number of seconds for input.

        Return
        ------
        trigger : str
            "s" for synchronization
            "a" for left thumb on ResponseGrips
            "b" for left index on ResponseGrips
            "c" for right index on ResponseGrips
            "d" for right thumb on ResponseGrips
        
        """
        self.port.timeout = timeout
        out = self.port.read(1)
        self.port.timeout = None
        return out.decode("utf-8")
    
    def start(self) -> None:
        """
        This function starts a SyncBox synchronization or simulation session

        Raises
        ----------
        SyncBoxException
            if unable to start session

        """
        self.port.write(b"S")
        time.sleep(0.1)
        confirmation = self.port.read(1)
        time.sleep(0.1)
        if confirmation != b"S":
            raise SyncBoxException(f"Unable to start session {confirmation}")

    def stop(self) -> None:
        """
        This function stops an ongoing SyncBox synchronization or simulation session

        Raises
        ----------
        SyncBoxException
            if unable to stop session

        """
        self.port.write(b"A")
        time.sleep(0.1)
        confirmation = self.port.read(1)
        time.sleep(0.1)
        if confirmation != b"A":
            raise SyncBoxException("Unable to stop session")


    def _findSyncBox(self) -> Serial:
        """
        This function loops thorugh all available serialports and finds the SyncBox
        
        Return
        -------
        serialport : Serial
            the serial port connected to the SyncBox

        Raises
        ----------
        SyncBoxException
            if unable to find the SyncBox
        
        """
        availablePorts = self._getAvailableSerialPorts()
        for port in availablePorts:
            try:
                com = Serial(port=port, baudrate=57600)
                com.timeout = 0.2
                com.write(b"C")   #Trying to enter computer mode
                time.sleep(0.1)
                confirmation = com.read(1)
                time.sleep(0.1)
                if confirmation == b"C":
                    return com
                    breakt

            except SerialException:
                continue
     

        raise SyncBoxException("Unable to find SyncBox")
            
    


    def _configure(self) -> None:
        """
        This function configures the SyncBox to the parameters provided to the constructor

        Raises
        ----------
        SyncBoxException
            if incorrect confirmation is recieved from SyncBox

        """
        self.port.write(b"R")   #Entering SyncBox configuration mode
        time.sleep(0.1)
        confirmation = self.port.read(1)
        time.sleep(0.1)
        if confirmation != b"R":
            raise SyncBoxException(f"Unable to configure SyncBox. Please restart the SyncBox")
        self.port.write(b"0000") #Dummy "0000"
        self.port.write(self._stringVar(self.num_volumes)) #Number of volumes "xxxx"
        self.port.write(self._stringVar(self.num_slices)) #Number of slices in each volume "xxxx"
        self.port.write(self._stringVar(self.pulse_length)) #Pulse length in ms (Only needed in simulation mode) "xxxx"
        self.port.write(self._stringVar(self.TR_time)) #TR time in ms (Only needed in simulation mode) "xxxx"
        self.port.write(self._stringVar(self.trigger_slice)) #Slice number you like to trigger on "xxxx"
        self.port.write(self._stringVar(self.trigger_volume)) #Enter how often you will trigger on volume "xxxx"
        self.port.write(b"0000") #Dummy "0000"
        self.port.write(b"0000") #Dummy "0000"
        self.port.write(self._stringVar(self.optional_trigger_slice)) #0 for triggering on each slice typed above, 1 for triggering on each slice, 2 for triggering on random slice "000x"
        self.port.write(self._stringVar(self.optional_trigger_volume)) #0 for triggering on each volume typed above, 1 for triggering on each volume, 2 for triggering on random volume "000x"
        if self.simulation:
            self.port.write(b"0000") #0001 for synchronization 0000 for simualtion
        else:
            self.port.write(b"0001")
        time.sleep(0.2)
        confirmation = self.port.read(12*4)
        time.sleep(0.1)
        if len(confirmation) != 12*4:
            raise SyncBoxException(f"Unable to configure SyncBox. Please restart the SyncBox")
        

    def _stringVar(self, var) -> bytes:
        """
        This function makes sure the provided parameters are maximum 4 digits 
        and converts it to bytes in the correct format

        Return
        --------
        bytes : bytes
            bytes of correct string input for the SyncBox

        Raises
        ----------
        SyncBoxException
            if a provided parameter is of incorrect length

        """
        num = str(var)
        if len(num) == 1:
            zero = "000"
        elif len(num) == 2:
            zero = "00"
        elif len(num) == 3:
            zero = "0"
        elif len(num) == 4:
            zero = ""
        else:
            raise SyncBoxException(f"The parameter '{var}' is unsupported. Please check that your parameters is maximum 4 digits")
        
        string = zero + num
        return bytes(string, 'ascii')
    


    def _getAvailableSerialPorts(self) -> list:
        """
        This function finds every available serial port on the currently used OS.

        Return
        -------
        list
            A list of available serial ports
        
        Raises
        -------

        EnvirornmentError
            If operative system is not available
        SerialExcpetion 
            If serial is not available
        """
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        result = []

        for port in ports:
            try:
                s = Serial(port)

                s.close()
                result.append(port)
            except (OSError, SerialException):
                pass
        return result
    

    def close(self):
        """
        This function closes the serial port connection and switches Computer mode off on the SyncBox.

        Raises
        ----------
        SyncBoxException
            if unable to turn off computer mode.

        """
        self.port.write(b"D")  
        time.sleep(0.1)
        confirmation = self.port.read(1)
        time.sleep(0.1)
        if confirmation != b"D":
            raise SyncBoxException("Unable to disconnect from SyncBox. Please turn it off manually")
        self.port.close()
        print("SyncBox disconnected")


class SyncBoxException(Exception):
    pass
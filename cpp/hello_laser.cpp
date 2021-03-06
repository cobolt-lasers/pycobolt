/*
*  hello_laser.cpp
*
*   THE PRESENT SAMPLE CODE WHICH IS FOR GUIDANCE ONLY AIMS AT PROVIDING CUSTOMERS
*       * WITH CODING INFORMATION REGARDING THEIR PRODUCTS IN ORDER FOR THEM TO SAVE
*         TIME.
*
* The following code is released under the MIT license.
*
* Please refer to the included license document for further information.
*/

#include <iostream>

#include <string>
#include <iostream>
#include <cstdio>

// OS Specific sleep
#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#endif

#include "serial/serial.h"

using std::string;
using std::exception;
using std::cout;
using std::endl;
using std::vector;

void enumerate_ports( vector<serial::PortInfo> &devices_found )
{
    devices_found = serial::list_ports();
    for ( int i = 0; i < devices_found.size(); i++ )
    {
        printf( "%i : (%s, %s, %s)\n", i, devices_found[i].port.c_str(), devices_found[i].description.c_str(),
     devices_found[i].hardware_id.c_str() );
    }
}

class InvalidPortException: public std::exception
{
  virtual const char* what() const throw()
  {
    return "Port ID out of range";
  }
} invalidPortException;

int main(int, char**) {
    vector<serial::PortInfo> devices_found;
    const int baud = 112500;
    unsigned int port_id;

    std::cout << "Please select serial port!\n";
    

    try {
        // Enumerate the system COM ports and present options to user
        enumerate_ports( devices_found );

        std::cin >> port_id;
        // Check that the user selected a valid port
        if (port_id >=  devices_found.size())
        {
            throw invalidPortException;
        }
    }
    catch(const std::exception& e) {
        std::cerr << e.what() << '\n';
    }
    
    // Connect to the slected port port, baudrate, timeout in milliseconds
    serial::Serial my_serial(devices_found[port_id].port, baud, serial::Timeout::simpleTimeout(1000));

    try {
        // Check if we managed to open the port (optional)
        cout << "Is the serial port open?";
        if(my_serial.isOpen()) 
        {
            cout << " Yes." << endl;
        }
        else
        {
            cout << " No." << endl;
        }

        // Ask the laser for its serial number, ( note the required ending \r\n )
        // Look in manual for the commands and response formatting of your laser!
        const std::string command = "gsn?"; // gsn? --> get serial number
        const std::string termination = "\r\n"; // This document is encoded in ascii compatible UTF-8. \r\n in UTF-8 and ASCII are the same.
        my_serial.write( command + termination );

        // Fetch results    
        string result = my_serial.readline();
        cout << "Serial number was: " << result << endl;

        my_serial.close();
    }

    catch(const std::exception& e)
    {
        std::cerr << e.what() << '\n';
        if ( my_serial.isOpen() ) 
        {
            my_serial.close();
        }
    }

}


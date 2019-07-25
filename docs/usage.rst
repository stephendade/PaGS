=====
Usage
=====

PaGS can be used in two ways: either as a standalone GCS or as part of a larger application.

Standalone
----------

To run standalone::

    pags.py
   
The following commandline arguments can be used:

* ``--source=tcpclient:127.0.0.1:5760:1:0`` Connection in format connectiontype:connectionstr:sys:comp
* ``--mav=2`` Mavlink Version (1 or 2)
* ``--dialect=ardupilotmega`` MAVLink dialect
* ``--source-system=255`` MAVLink source system for this GCS
* ``--source-component=0`` MAVLink source component for this GCS
* ``--multi``
* ``--nogui`` Disable usage of a GUI
* ``--sitl=n`` Connect to Ardupilot SITL instance, where ``n`` is the instance ID (ID is required).

(Default values of each argument are shown above).

For the connection sources (``--source``), the connection types can be:

* ``tcpclient`` with the connectionstr being ``remoteip:port``
* ``tcpserver`` with the connectionstr being ``localip:port``
* ``udpserver`` with the connectionstr being ``localip:port``
* ``udpclient`` with the connectionstr being ``remoteip:port``
* ``serial`` with the connectionstr being ``serialport:baud``, ie ``source=serial:COM17:115200:1:0``

The ``sys`` is the System ID of the remote vehicle and the ``comp`` is the component ID of the vehicle.
These are typically 1 and 0 respectively for Ardupilot with the default parameters.

Multiple ``--source`` can be used. Each system ID is assumed to be a different vehicle. Thus multiple connections
to a single vehicle can be used.

In the alternate case, where multiple vehicles (each with a different System ID) are on a single connection, 
simply repeat the ``--source`` with the same connectionstr and the relevent (differerent) source ID's.

If using the ``--sitl`` options, multiple connections to different APM SITL instances can be used. For example, to connect to 3 SITL instances: ``--sitl=0 --sitl=1 --sitl=2``

If neither the ``--source`` and ``--sitl`` arguments are used, PaGS will first look for any USB-connected flight controllers and attempt to connect at a buad rate of 115200, otherwise it will connect to a UDP server on localhost, port 14550.

As an example:

* Vehicle 1 (System ID 1) and Vehicle 3 (System ID) are both on serial port COM17, baud 57600
* Vehicle 2 (System ID 22) is on tcpserver 192.168.0.1:14500 and a secondary link on udpclient 192.168.0.10:14600

Gives::

    pags.py --source=serial:COM17:57600:1:0 --source=serial:COM17:57600:3:0 --source=tcpserver:192.168.0.1:14500:22:0 -source=udpclient:192.168.0.10:14600:22:0

   

As a Library
------------

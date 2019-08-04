Modules
=======

Modules are plugins for PaGS that can read and write packets to vehicles.

For example, a module might read the system status onto a GUI, or command
the vehicle to change mode.

Modules can be loaded by ``module load xxx``, where xx is the module library path.

The current set of loaded modules can be listed via ``module list``.

.. toctree::
    :glob:

    terminal
    mode
    parameter
    status
